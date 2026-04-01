# FlowTrace — 全流程调用链追踪系统

> 日期：2026-03-31
> 状态：Approved

## 1. 目标

为后端全流程（analyze / generate）提供完整的调用链 trace 记录，用于**模型调试和性能分析**。前端在关键节点增加 console.log，通过 `X-Trace-Id` 响应头与后端 trace 关联。

### 核心价值

- 每次完整调用生成一条 trace，包含各阶段耗时、状态、关键参数
- trace 通过 contextvars 跨层传递，自动关联 request_id
- 按天分割 JSONL 文件存储，自动清理过期数据
- 调试接口 `GET /api/traces` 查看历史记录
- 前端 DevTools 通过 trace_id 与后端日志对应

## 2. 数据模型

### FlowTrace

```python
class FlowTrace(BaseModel):
    trace_id: str                           # UUID
    request_id: str                         # 中间件生成的 req-xxxxxxxx（从 request_id_ctx 获取）
    flow_type: Literal["analyze", "generate"]
    status: Literal["success", "failed"]
    created_at: str                         # ISO 8601, 毫秒精度
    total_duration_ms: float                # 总耗时
    steps: list[FlowStep]                   # 各阶段记录
    error: str | None = None                # 失败时的最终错误信息
```

### FlowStep

```python
class FlowStep(BaseModel):
    name: str                               # 阶段标识符
    status: Literal["running", "success", "failed", "skipped"]
    started_at: str                         # ISO 8601
    duration_ms: float | None = None
    detail: dict = {}                       # 阶段特有信息（dict 类型，KISS 原则，不使用 TypedDict）
    error: str | None = None                # 失败时的错误信息
```

### 阶段标识符（name）

| flow_type | step name | 位置 | detail 字段 |
|-----------|-----------|------|-------------|
| analyze | `llm_analyze` | analyze_service.py | `model`, `image_size`, `temperature`, `options_count`, `topic_names` |
| analyze | `parse_response` | analyze_service.py | `options_count` |
| generate | `save_photo` | generate_service.py | `path`, `file_size` |
| generate | `compose_prompt` | generate_service.py | `model`, `style_name`, `temperature`, `prompt_length` |
| generate | `image_generate` | generate_service.py | `model`, `retries`, `response_size` |
| generate | `download_image` | image_gen_client.py (_download_as_base64) | `file_size` |
| generate | `save_poster` | generate_service.py | `history_id`, `poster_size` |

> 注：`compose_prompt` step 包裹整个 `_compose_prompt` 调用（含内部 LLM 调用和 JSON 解析），不拆分子步骤。`download_image` 对应 `ImageGenClient._download_as_base64()`，Qwen API 返回图片 URL 后需下载转为 base64。

## 3. 架构设计

### 文件结构

```
backend/app/
├── flow_log/
│   ├── __init__.py          # 导出 FlowSession, get_current_trace, NoOpSession
│   ├── trace.py             # FlowTrace / FlowStep 模型 + FlowSession + NoOpSession
│   └── trace_store.py       # JSONL 文件存储 + 自动清理
├── routers/
│   └── traces.py            # GET /api/traces 查询端点
```

### FlowSession 核心

```python
class FlowSession:
    """一次完整 API 调用的 trace 会话。"""

    def __init__(self, flow_type: str, request_id: str = ""):
        self.trace = FlowTrace(
            trace_id=str(uuid4()),
            request_id=request_id,
            flow_type=flow_type,
            created_at=iso_now(),
            status="running",
            steps=[],
            total_duration_ms=0,
        )
        self._start = time.perf_counter()

    @asynccontextmanager
    async def step(self, name: str, detail: dict | None = None):
        """阶段上下文管理器：自动计时、记录状态、捕获异常。"""
        step = FlowStep(name=name, started_at=iso_now(), status="running", detail=detail or {})
        self.trace.steps.append(step)
        t0 = time.perf_counter()
        try:
            yield step
            step.status = "success"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            raise  # 不吞异常
        finally:
            step.duration_ms = (time.perf_counter() - t0) * 1000

    def finish(self, status: Literal["success", "failed"], error: str | None = None):
        """标记 trace 完成，计算总耗时。"""
        self.trace.status = status
        self.trace.total_duration_ms = (time.perf_counter() - self._start) * 1000
        self.trace.error = error
```

### NoOpSession（Null Object 模式）

当 `trace_enabled=False` 时，`get_current_trace()` 返回 `NoOpSession` 而非 `None`，确保服务层代码无需条件判断：

```python
class NoOpSession:
    """trace_enabled=False 时的空操作会话，零开销。"""

    @asynccontextmanager
    async def step(self, name: str, detail: dict | None = None):
        yield _NoOpStep()  # step 仍执行包裹的代码，但不记录

    def finish(self, status, error=None):
        pass
```

### contextvars 传递

```python
_current_trace: ContextVar[FlowSession | NoOpSession] = ContextVar("flow_trace", default=NoOpSession())

def get_current_trace() -> FlowSession | NoOpSession:
    return _current_trace.get()
```

- 路由层入口根据 `settings.trace_enabled` 创建 `FlowSession` 或 `NoOpSession`，设置到 contextvars
- `request_id` 从现有的 `request_id_ctx` contextvars（定义在 `logging_config.py`）中读取
- service 层通过 `get_current_trace()` 获取当前 trace，直接调用 `.step()`，无需判空

### 集成方式

**路由层 — 使用 FastAPI `Response` 参数注入 X-Trace-Id header：**

```python
from fastapi import Response
from app.flow_log import FlowSession, NoOpSession
from app.logging_config import request_id_ctx

@router.post("/analyze")
async def analyze_endpoint(
    request: AnalyzeRequest,
    settings: Settings = Depends(get_settings),
    response: Response = Response(),
):
    # 创建 trace session
    if settings.trace_enabled:
        trace = FlowSession("analyze", request_id=request_id_ctx.get(""))
        _current_trace.set(trace)
    else:
        trace = NoOpSession()
        _current_trace.set(trace)

    # 注入 X-Trace-Id header（对 NoOpSession 无影响）
    if isinstance(trace, FlowSession):
        response.headers["X-Trace-Id"] = trace.trace.trace_id

    try:
        options = await analyze_photo(request.image_base64, request.image_format, settings)
        if isinstance(trace, FlowSession):
            trace.finish("success")
        return ApiResponse(code=0, message="success", data=AnalyzeResponse(options=options).model_dump())
    except AnalyzeError as e:
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=e.message)
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=str(e))
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
    finally:
        if isinstance(trace, FlowSession):
            trace_store.save(trace.trace)
```

> **设计决策**：使用 `isinstance` 检查区分 FlowSession 和 NoOpSession。这比在 NoOpSession 中维护空数据结构更清晰，性能开销可忽略（仅在请求边界执行一次）。

**服务层（analyze_service.py, generate_service.py）：**

```python
from app.flow_log import get_current_trace

async def analyze_photo(image_base64, image_format, settings):
    trace = get_current_trace()
    llm = LLMClient(settings)
    async with trace.step("llm_analyze", detail={"model": settings.openai_model, "image_size": len(image_base64)}):
        content = await llm.chat_with_vision(...)

    async with trace.step("parse_response"):
        data = LLMClient.extract_json_from_content(content)
    # ...
```

服务层代码完全不需要知道 trace 是否启用，`NoOpSession.step()` 是空操作上下文管理器。

### 存储 — JSONL 追加模式（并发安全）

使用 **JSONL 格式**（每行一条 JSON）+ **追加写入**替代"读取-修改-写回"模式，解决并发写入竞态条件：

```python
class TraceStore:
    def __init__(self, trace_dir: str, retention_days: int = 7):
        self.trace_dir = Path(trace_dir)
        self.retention_days = retention_days

    def save(self, trace: FlowTrace):
        """追加写入当天 trace 文件（JSONL 格式，并发安全）。"""
        date_str = trace.created_at[:10]  # "2026-03-31"
        file_path = self.trace_dir / f"{date_str}.jsonl"
        # 追加模式写入，无需读取已有内容
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(trace.model_dump_json() + "\n")

    def query(self, date: str | None = None, limit: int = 20) -> list[FlowTrace]:
        """查询指定日期的 trace 记录。"""
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        file_path = self.trace_dir / f"{date_str}.jsonl"
        if not file_path.exists():
            return []
        traces = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    traces.append(FlowTrace.model_validate_json(line))
        # 返回最新的 N 条（倒序）
        return list(reversed(traces))[:limit]

    def cleanup(self):
        """删除超过 retention_days 的文件。启动时调用一次。"""
        ...
```

文件格式：

```jsonl
{"trace_id":"abc-123","request_id":"req-abcdef","flow_type":"analyze","status":"success","created_at":"2026-03-31T10:23:45.123","total_duration_ms":3456.78,"steps":[...],"error":null}
{"trace_id":"def-456","request_id":"req-ghijkl","flow_type":"generate","status":"success","created_at":"2026-03-31T10:24:30.456","total_duration_ms":45678.90,"steps":[...],"error":null}
```

### 配置

```python
# config.py 新增
trace_enabled: bool = True              # 是否启用 trace（开发环境 True，生产可选关闭）
trace_dir: str = "data/traces"          # trace 文件目录
trace_retention_days: int = 7           # 保留天数
```

### 查询 API

```
GET /api/traces?date=2026-03-31&limit=20
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| date | string | 今天 | 日期字符串 YYYY-MM-DD |
| limit | int | 20 | 返回条数（最多 100） |

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "traces": [FlowTrace, ...],
    "date": "2026-03-31"
  }
}
```

### 前端改动

**api.ts — 在 `response.json()` 之前提取 header：**

```typescript
async function request<T>(
  endpoint: string,
  options: RequestInit,
  timeoutMs: number,
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const t0 = performance.now();

  try {
    const response = await fetch(url, {
      ...options,
      signal: AbortSignal.timeout(timeoutMs),
    });

    // 在 json() 之前提取 trace header
    const traceId = response.headers.get('x-trace-id');
    console.log('[FlowTrace] API response:', endpoint, '| trace_id:', traceId, '| status:', response.status, '| duration_ms:', Math.round(performance.now() - t0));

    if (!response.ok) {
      throw new ApiError(...);
    }

    const data: T = await response.json();
    // ... code check ...
    return data;
  } catch (error) {
    throw new Error(parseApiError(error));
  }
}
```

**App.tsx — 状态转换节点 console.log：**

```typescript
// 格式统一: [FlowTrace] 节点 | 信息
// onCountdownComplete 中
console.log('[FlowTrace] state:', AppState.ANALYZING, '| action:', 'analyze_start');

// handleSelectStyle 中
console.log('[FlowTrace] state:', AppState.GENERATING, '| style:', style.name);

// analyze 完成后
console.log('[FlowTrace] state:', AppState.STYLE_SELECTION, '| options_count:', options.length);
```

**X-Trace-Id 关联：**

- 前端 `api.ts` 在 `response.json()` 之前从 `response.headers` 读取 `X-Trace-Id`
- console.log 中输出 trace_id
- 后端 trace 文件中通过 trace_id 定位完整记录

## 4. 错误处理

- `trace.step()` **不吞异常**：捕获后记录状态和错误信息，然后 `raise` 继续向上传播
- 现有 try/except 错误处理链**完全不变**
- trace 文件写入失败时（如磁盘满）不影响主流程，`trace_store.save()` 内部 try/except + logger.warning
- `trace_enabled=False` 时返回 `NoOpSession`，`.step()` 和 `.finish()` 均为空操作，零开销

## 5. 测试设计

### 5.1 单元测试

文件：`tests/backend/unit/test_flow_trace.py`

#### 模型测试

| 用例 | 说明 |
|------|------|
| `test_flow_trace_model_valid` | 验证 FlowTrace 模型正确创建 |
| `test_flow_step_model_valid` | 验证 FlowStep 模型正确创建 |
| `test_flow_step_default_values` | 验证 detail 默认空 dict，duration_ms/error 默认 None |
| `test_flow_trace_validation` | 验证 flow_type 和 status 的枚举约束 |

#### FlowSession 测试

| 用例 | 说明 |
|------|------|
| `test_session_step_success_records_timing` | 成功 step 记录 status=success + duration_ms > 0 |
| `test_session_step_failed_records_error` | 失败 step 记录 status=failed + error 信息 |
| `test_session_step_failed_reraises_exception` | 验证 step 不吞异常（raise 后可被外层 catch） |
| `test_session_step_with_detail` | 验证 detail 正确传递到 step |
| `test_session_finish_calculates_total_duration` | finish() 计算 total_duration_ms > 0 |
| `test_session_finish_with_error` | finish("failed", error="...") 记录错误信息到 trace.error |
| `test_session_multiple_steps_ordered` | 多个 step 按顺序记录 |
| `test_session_concurrent_isolation` | 多个并发 FlowSession 互不干扰（contextvars 隔离） |
| `test_session_init_with_request_id` | 构造时传入 request_id 正确记录 |

#### NoOpSession 测试

| 用例 | 说明 |
|------|------|
| `test_noop_step_executes_code_without_recording` | step 内部代码正常执行，但不产生任何记录 |
| `test_noop_step_does_not_raise_on_success` | 成功时无异常 |
| `test_noop_step_reraises_exception` | 异常仍向上传播 |
| `test_noop_finish_noop` | finish() 不做任何事，无异常 |

#### TraceStore 测试

| 用例 | 说明 |
|------|------|
| `test_store_save_creates_jsonl_file` | 保存 trace 创建对应日期的 .jsonl 文件 |
| `test_store_save_appends_lines` | 同一天的 trace 追加到同一文件（每行一条） |
| `test_store_save_different_dates` | 不同日期的 trace 写入不同文件 |
| `test_store_query_returns_traces` | 查询返回指定日期的 trace 列表（最新优先） |
| `test_store_query_default_date` | 不指定 date 默认查今天 |
| `test_store_query_limit` | limit 参数限制返回条数 |
| `test_store_query_empty_date` | 查询不存在的日期返回空列表 |
| `test_store_query_returns_newest_first` | 返回结果按时间倒序 |
| `test_store_cleanup_removes_old_files` | 清理超过 retention_days 的文件 |
| `test_store_cleanup_keeps_recent_files` | 保留未过期的文件 |
| `test_store_save_valid_jsonl_structure` | 每行是合法的 FlowTrace JSON |

#### 路由测试

| 用例 | 说明 |
|------|------|
| `test_traces_endpoint_returns_list` | GET /api/traces 返回 traces 列表 |
| `test_traces_endpoint_with_date_param` | date 参数正确过滤 |
| `test_traces_endpoint_with_limit_param` | limit 参数正确限制条数 |
| `test_traces_endpoint_empty_date` | 空日期返回空列表 |
| `test_analyze_response_has_trace_header` | analyze 响应包含 X-Trace-Id header（trace_enabled=True 时） |
| `test_generate_response_has_trace_header` | generate 响应包含 X-Trace-Id header |
| `test_no_trace_header_when_disabled` | trace_enabled=False 时无 X-Trace-Id header |

#### Contextvars 传递测试

| 用例 | 说明 |
|------|------|
| `test_contextvar_set_in_router_accessible_in_service` | 路由层设置的 trace 在 service 层可获取 |
| `test_get_current_trace_returns_noop_when_unset` | 未设置时返回 NoOpSession |

### 5.2 集成测试

文件：`tests/backend/integration/test_real_api.py`（在现有文件中追加 trace 验证用例）

#### 全流程 trace 记录验证

| 用例 | 说明 |
|------|------|
| `test_trace_created_on_analyze` | 调用 analyze 后，trace 文件中生成一条 flow_type=analyze 的记录 |
| `test_trace_created_on_generate` | 调用 generate 后，trace 文件中生成一条 flow_type=generate 的记录 |
| `test_trace_has_correct_steps` | analyze trace 包含 llm_analyze + parse_response 两个 step |
| `test_trace_generate_has_all_steps` | generate trace 包含 save_photo + compose_prompt + image_generate + download_image + save_poster 五个 step |
| `test_trace_step_has_duration` | 每个 step 的 duration_ms > 0 |
| `test_trace_step_has_detail` | llm_analyze step 的 detail 包含 model 和 image_size |
| `test_trace_total_duration` | total_duration_ms >= 所有 step duration_ms 之和 |
| `test_trace_status_success` | 正常完成后 trace.status = "success" |

#### 失败场景 trace 记录验证

| 用例 | 说明 |
|------|------|
| `test_trace_records_llm_failure` | LLM 调用失败时 trace 包含 failed step + error 信息 |
| `test_trace_status_failed_on_error` | 异常时 trace.status = "failed" |

#### TraceStore 集成验证

| 用例 | 说明 |
|------|------|
| `test_trace_file_exists_after_request` | 发送请求后 trace 文件存在且非空 |
| `test_trace_file_valid_jsonl` | trace 文件内容是合法 JSONL（每行独立解析为 FlowTrace） |
| `test_traces_endpoint_returns_saved_data` | 通过 API 查询到之前保存的 trace |

#### 端到端 trace 关联验证

| 用例 | 说明 |
|------|------|
| `test_full_flow_trace_complete` | 完整流程 analyze → select → generate 后，两条 trace 都可查到 |
| `test_trace_request_id_matches` | trace 中的 request_id 与中间件日志一致 |
| `test_trace_id_in_response_header` | response header 中的 X-Trace-Id 与 trace 文件中的 trace_id 一致 |

### 5.3 真实 API 测试中的 trace 验证

在现有的 `test_real_api.py` 中，为关键用例追加 trace 验证。测试前需创建独立的 trace 目录并配置环境变量。

| 现有用例 | 追加验证 |
|----------|----------|
| `test_analyze_returns_5_topics` (T02) | 验证 trace 文件生成，包含 llm_analyze step，duration 记录合理 |
| `test_compose_generates_english_prompt` (T07) | 验证 compose_prompt step 的 detail 包含 prompt_length |
| `test_generate_end_to_end` (T09) | 验证完整 5 个 step 全部记录，total_duration 合理 |

辅助函数设计（通过 trace_id 精确匹配，避免 `limit=1` 的隐含假设）：

```python
def verify_trace(flow_type: str, trace_dir: str, trace_id: str | None = None) -> dict:
    """验证 trace 记录。可通过 trace_id 精确匹配，或匹配最新的指定类型 trace。"""
    from app.flow_log.trace_store import TraceStore
    store = TraceStore(trace_dir)
    traces = store.query(limit=50)
    # 按 trace_id 精确匹配，或按 flow_type 匹配最新一条
    if trace_id:
        matches = [t for t in traces if t.trace_id == trace_id]
        assert len(matches) == 1, f"Expected 1 trace with id={trace_id}, found {len(matches)}"
        trace = matches[0]
    else:
        matches = [t for t in traces if t.flow_type == flow_type]
        assert len(matches) > 0, f"No trace found for {flow_type}"
        trace = matches[0]
    assert trace.flow_type == flow_type
    return trace.model_dump()
```

### 5.4 前端日志验证

不写自动化测试。通过手动验证：

1. 打开浏览器 DevTools Console
2. 执行完整流程（拍照 → 分析 → 选择 → 生成）
3. 确认每个节点有 `[FlowTrace]` 前缀的 console.log
4. 确认 API 响应日志中包含 `trace_id`（来自 X-Trace-Id header）
5. 用该 trace_id 在 `GET /api/traces` 或 `data/traces/*.jsonl` 中找到对应记录
6. 确认 `duration_ms` 在合理范围内

### 5.5 conftest.py fixture 改动

在现有 `tmp_data_dir` fixture 中追加 trace 目录和环境变量：

```python
@pytest.fixture
def tmp_data_dir(tmp_path):
    """创建临时 data 目录结构并设置环境变量。"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "photos").mkdir()
    (data_dir / "posters").mkdir()
    (data_dir / "traces").mkdir()
    (data_dir / "history.json").write_text("[]", encoding="utf-8")
    os.environ["PHOTO_STORAGE_DIR"] = str(data_dir / "photos")
    os.environ["POSTER_STORAGE_DIR"] = str(data_dir / "posters")
    os.environ["HISTORY_FILE"] = str(data_dir / "history.json")
    os.environ["TRACE_DIR"] = str(data_dir / "traces")
    os.environ["TRACE_ENABLED"] = "true"
    yield data_dir

@pytest.fixture
def trace_store(tmp_data_dir):
    """创建临时 TraceStore 实例。"""
    from app.flow_log.trace_store import TraceStore
    return TraceStore(str(tmp_data_dir / "traces"), retention_days=7)
```

## 6. 现有代码改动清单

### 后端

| 文件 | 改动 |
|------|------|
| `backend/app/config.py` | 新增 `trace_enabled`, `trace_dir`, `trace_retention_days` 三个配置项 |
| `backend/app/main.py` | lifespan 中创建 `trace_dir` 目录，启动时执行 cleanup；注册 traces router |
| `backend/app/routers/analyze.py` | 创建 FlowSession/NoOpSession，finish 后保存 trace，通过 Response 注入 X-Trace-Id header |
| `backend/app/routers/generate.py` | 同上 |
| `backend/app/services/analyze_service.py` | llm 调用和 JSON 解析包裹 `trace.step()` |
| `backend/app/services/generate_service.py` | 5 个步骤分别包裹 `trace.step()` |
| `backend/app/flow_log/__init__.py` | 新建，导出 FlowSession, NoOpSession, get_current_trace |
| `backend/app/flow_log/trace.py` | 新建，FlowTrace/FlowStep 模型 + FlowSession + NoOpSession |
| `backend/app/flow_log/trace_store.py` | 新建，JSONL 文件存储（追加模式，并发安全） |
| `backend/app/routers/traces.py` | 新建，GET /api/traces |

### 前端

| 文件 | 改动 |
|------|------|
| `frontend/src/services/api.ts` | `request()` 函数在 `response.json()` 之前提取 X-Trace-Id header 并 console.log |
| `frontend/src/App.tsx` | 状态转换关键节点添加 console.log |

### 测试

| 文件 | 改动 |
|------|------|
| `tests/backend/unit/test_flow_trace.py` | 新建，约 30 个单元测试 |
| `tests/backend/conftest.py` | `tmp_data_dir` 增加 traces 目录 + 环境变量；新增 `trace_store` fixture |
| `tests/backend/integration/test_real_api.py` | 追加 trace 验证用例和 `verify_trace` 辅助函数 |
