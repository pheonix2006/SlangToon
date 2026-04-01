# Tests

本项目所有测试集中在此目录下，按层级和类型组织。

## 目录结构

```
tests/
├── backend/
│   ├── unit/            # 后端单元测试 (pytest)
│   └── integration/     # 后端集成测试 (需要真实 API)
├── frontend/
│   ├── unit/            # 前端单元测试 (Vitest)
│   └── e2e/             # 前端 E2E 测试 (Playwright)
└── e2e/                 # 全链路 E2E 测试
```

## 运行命令

### 后端单元测试

```bash
uv run pytest tests/backend/unit/ -v
```

### 后端集成测试（需要运行中的后端 + API Key）

```bash
uv run pytest tests/backend/integration/test_real_api.py -v -s --tb=short
```

或独立运行：

```bash
uv run python tests/backend/integration/test_real_api.py
```

### 前端单元测试

```bash
cd frontend && npx vitest run
```

### 前端 E2E 测试（Playwright）

```bash
cd frontend && npx playwright test
```

### 全链路 E2E 测试

```bash
uv run python tests/e2e/e2e_test.py
```

前置条件：后端已启动 (`uv run python backend/run.py`)，`.env` 已配置有效 API Key。
