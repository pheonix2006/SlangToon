"""L3-L6 集成验收：节点真实连通 + LangSmith trace 完整性。

运行前提：
    1. .env 中配置了 ZHIPU_API_KEY / DASHSCOPE_API_KEY / LANGSMITH_API_KEY
    2. 设置 LANGSMITH_TRACING=true

运行方式：
    cd "E:/Project/1505v2/1505creative_art"
    uv run pytest tests/backend/integration/test_node_langsmith_connectivity.py -v -s
"""

import os
import time

import httpx
import pytest

from app.config import Settings
from app.graphs.script_graph import build_script_graph
from app.graphs.comic_graph import build_comic_graph
from app.graphs.trace_collector import invoke_with_trace
from app.graphs.trace_store import TraceStore


# ── LangSmith API helper ──────────────────────────────────────────────

LANGSMITH_API_BASE = "https://api.smith.langchain.com"


def _fetch_langsmith_runs(project: str, api_key: str, limit: int = 10):
    """查询 LangSmith 项目最近的 runs。"""
    resp = httpx.get(
        f"{LANGSMITH_API_BASE}/api/v1/runs",
        params={"project_name": project, "limit": limit},
        headers={"x-api-key": api_key},
        timeout=30,
    )
    assert resp.status_code == 200, f"LangSmith API error: {resp.status_code} {resp.text}"
    return resp.json()


def _find_graph_run(runs: list) -> dict | None:
    """从 runs 列表中找到顶层 Graph run（无 parent_run_id）。"""
    for r in runs:
        if r.get("parent_run_id") is None:
            return r
    return None


def _find_child_runs(runs: list, parent_id: str) -> list:
    """找到某 parent 下的所有子 run。"""
    return [r for r in runs if r.get("parent_run_id") == parent_id]


# ── L3: 节点真实 API 连通 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_L3_script_node_real_llm():
    """L3: script_node 真实调用 GLM-4.6V，返回有效脚本数据。"""
    settings = Settings()
    graph = build_script_graph()

    result = await graph.ainvoke(
        {"trigger": "ok_gesture"},
        config={"configurable": {"settings": settings}},
    )

    # 验证脚本数据完整性
    assert "slang" in result and len(result["slang"]) > 0, f"Invalid slang: {result.get('slang')}"
    assert "origin" in result and len(result["origin"]) > 0, f"Invalid origin: {result.get('origin')}"
    assert "explanation" in result and len(result["explanation"]) > 0, "Invalid explanation"
    assert 8 <= result["panel_count"] <= 12, f"Invalid panel_count: {result.get('panel_count')}"
    assert len(result["panels"]) == result["panel_count"], (
        f"panels length {len(result['panels'])} != panel_count {result['panel_count']}"
    )

    # 验证每个 panel 结构
    for i, panel in enumerate(result["panels"]):
        assert "scene" in panel, f"Panel {i} missing 'scene' field"

    print(f"  [L3 PASS] script_node: slang='{result['slang']}', panels={result['panel_count']}")


@pytest.mark.asyncio
async def test_L3_comic_graph_real_pipeline():
    """L3: ComicGraph 真实调用 Qwen Image 2.0，生成漫画图片。

    用固定脚本数据作为输入，测试 prompt_node → comic_node → save_node 全链路。
    """
    settings = Settings()
    graph = build_comic_graph()

    inputs = {
        "slang": "Break a leg",
        "origin": "Western theater tradition",
        "explanation": "A way to wish good luck to performers before a show",
        "panel_count": 8,
        "panels": [
            {"scene": f"A simple manga panel scene {i+1} with a character performing daily activities",
             "dialogue": f"Dialogue {i+1}" if i % 2 == 0 else "",
             "narration": f"Narration {i+1}" if i % 3 == 0 else ""}
            for i in range(8)
        ],
    }

    result = await graph.ainvoke(
        inputs,
        config={"configurable": {"settings": settings}},
    )

    # 验证漫画生成结果
    assert "comic_url" in result, "Missing comic_url"
    assert "thumbnail_url" in result, "Missing thumbnail_url"
    assert "history_id" in result, "Missing history_id"
    assert result["comic_url"].startswith("/data/comics/"), f"Invalid comic_url: {result.get('comic_url')}"
    assert len(result["history_id"]) > 0, "Empty history_id"

    print(f"  [L3 PASS] comic_graph: comic_url={result['comic_url']}, history_id={result['history_id']}")


# ── L4: 节点间 State 串联 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_L4_state_propagation_between_nodes():
    """L4: ComicGraph 逐节点 stream，验证 State 在节点间正确传递。"""
    settings = Settings()
    graph = build_comic_graph()

    inputs = {
        "slang": "Break a leg",
        "origin": "Western theater",
        "explanation": "Good luck wish",
        "panel_count": 8,
        "panels": [
            {"scene": f"Scene {i+1}", "dialogue": "", "narration": ""}
            for i in range(8)
        ],
    }

    node_outputs = {}
    async for chunk in graph.astream(
        inputs,
        config={"configurable": {"settings": settings}},
        stream_mode="updates",
    ):
        for node_name, output in chunk.items():
            node_outputs[node_name] = output
            print(f"  [L4] {node_name}: {list(output.keys()) if output else 'None'}")

    # 验证执行顺序和串联
    assert "prompt_node" in node_outputs, "prompt_node did not execute"
    assert "comic_prompt" in node_outputs["prompt_node"], "prompt_node did not output comic_prompt"

    # comic_node 应该接收到 comic_prompt 并输出 image_base64
    assert "comic_node" in node_outputs, "comic_node did not execute"
    assert "image_base64" in node_outputs["comic_node"], "comic_node did not output image_base64"

    # save_node 应该输出 URL
    assert "save_node" in node_outputs, "save_node did not execute"
    assert "comic_url" in node_outputs["save_node"], "save_node did not output comic_url"
    assert "thumbnail_url" in node_outputs["save_node"], "save_node did not output thumbnail_url"
    assert "history_id" in node_outputs["save_node"], "save_node did not output history_id"

    print(f"  [L4 PASS] Node chain: {' -> '.join(node_outputs.keys())}")


# ── L5: LangSmith 逐节点上报 ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_L5_langsmith_per_node_trace():
    """L5: ScriptGraph 执行后，LangSmith 收到 script_node 对应的 run。"""
    api_key = os.environ.get("LANGSMITH_API_KEY", "")
    project = os.environ.get("LANGSMITH_PROJECT", "slangtoon")
    assert api_key, "LANGSMITH_API_KEY not set"

    settings = Settings()
    graph = build_script_graph()

    # 执行 Graph
    await graph.ainvoke(
        {"trigger": "ok_gesture"},
        config={"configurable": {"settings": settings}},
    )

    # 等待 LangSmith 数据上报（通常 <2s）
    time.sleep(3)

    # 查询最近 runs
    runs = _fetch_langsmith_runs(project, api_key, limit=5)
    assert len(runs) > 0, "No runs found in LangSmith"

    # 找到 script_node 的 run
    node_runs = [r for r in runs if r.get("name") == "script_node"]
    assert len(node_runs) > 0, (
        f"script_node run not found in LangSmith. "
        f"Available: {[r.get('name') for r in runs]}"
    )

    script_run = node_runs[0]
    assert script_run.get("status") == "success", f"script_node status: {script_run.get('status')}"
    assert "inputs" in script_run, "script_node run missing inputs"
    assert "outputs" in script_run, "script_node run missing outputs"

    print(f"  [L5 PASS] script_node found in LangSmith: status={script_run['status']}")


# ── L6: LangSmith 全链路 trace 树 ─────────────────────────────────────


@pytest.mark.asyncio
async def test_L6_langsmith_full_trace_chain():
    """L6: 全流程在 LangSmith 展示为一条连贯 trace（父子关系完整）。

    验证：
    1. 存在一个顶层 Graph run（parent_run_id = None）
    2. 该 Graph run 下有子 run（每个执行的 node 一个）
    3. 子 run 的 parent_run_id 指向 Graph run
    4. 子 run 形成完整链路，不是散落的独立 run
    """
    api_key = os.environ.get("LANGSMITH_API_KEY", "")
    project = os.environ.get("LANGSMITH_PROJECT", "slangtoon")
    assert api_key, "LANGSMITH_API_KEY not set"

    settings = Settings()
    graph = build_comic_graph()

    inputs = {
        "slang": "Break a leg",
        "origin": "Western theater",
        "explanation": "Good luck wish",
        "panel_count": 8,
        "panels": [
            {"scene": f"Scene {i+1}", "dialogue": "", "narration": ""}
            for i in range(8)
        ],
    }

    # 执行 ComicGraph
    await graph.ainvoke(
        inputs,
        config={"configurable": {"settings": settings}},
    )

    # 等待 LangSmith 数据上报
    time.sleep(3)

    # 查询最近 runs
    runs = _fetch_langsmith_runs(project, api_key, limit=20)
    assert len(runs) > 0, "No runs found in LangSmith"

    # 找到顶层 Graph run
    graph_run = _find_graph_run(runs)
    assert graph_run is not None, (
        f"No top-level graph run found. "
        f"All runs: {[(r.get('name'), r.get('parent_run_id')) for r in runs]}"
    )

    # 找到 Graph 的子 run
    child_runs = _find_child_runs(runs, graph_run["id"])
    child_names = {r["name"] for r in child_runs}

    # 验证关键节点存在
    required_nodes = {"prompt_node", "comic_node", "save_node"}
    missing = required_nodes - child_names
    assert not missing, (
        f"Missing child runs: {missing}. "
        f"Found children: {child_names}"
    )

    # 验证是连贯链路，不是散落的独立 run
    parent_ids = {r["parent_run_id"] for r in child_runs}
    assert len(parent_ids) == 1, (
        f"Child runs have different parent_run_ids: {parent_ids}. "
        f"Should all be children of one graph run."
    )

    # 验证执行顺序（按 start_time 排序）
    sorted_children = sorted(child_runs, key=lambda r: r.get("start_time", ""))
    execution_order = [r["name"] for r in sorted_children]

    # prompt_node 应在 comic_node 之前
    if "prompt_node" in execution_order and "comic_node" in execution_order:
        assert execution_order.index("prompt_node") < execution_order.index("comic_node"), (
            f"prompt_node should execute before comic_node. Order: {execution_order}"
        )

    # comic_node 应在 save_node 之前
    if "comic_node" in execution_order and "save_node" in execution_order:
        assert execution_order.index("comic_node") < execution_order.index("save_node"), (
            f"comic_node should execute before save_node. Order: {execution_order}"
        )

    print(f"  [L6 PASS] Full trace chain:")
    print(f"    Graph run: {graph_run['id']}")
    print(f"    Children ({len(child_runs)}): {' -> '.join(execution_order)}")
    print(f"    All parent_run_ids point to graph run: {graph_run['id']}")


# ── L6 附加：本地 trace + LangSmith 双写验证 ──────────────────────────


@pytest.mark.asyncio
async def test_L6_local_trace_matches_langsmith():
    """L6 附加：invoke_with_trace 同时产生本地 trace 和 LangSmith trace。"""
    api_key = os.environ.get("LANGSMITH_API_KEY", "")
    project = os.environ.get("LANGSMITH_PROJECT", "slangtoon")
    assert api_key, "LANGSMITH_API_KEY not set"

    settings = Settings()
    graph = build_script_graph()

    result, trace_id = await invoke_with_trace(
        graph,
        {"trigger": "ok_gesture"},
        settings,
        flow_type="script",
    )

    # 验证本地 trace
    store = TraceStore(settings.trace_dir, settings.trace_retention_days)
    local_trace = store.get_by_trace_id(trace_id)
    assert local_trace is not None, f"Local trace {trace_id} not found"
    assert local_trace.flow_type == "script"
    assert local_trace.status == "success"
    assert len(local_trace.nodes) >= 1, "Local trace has no nodes"

    # 验证 LangSmith trace
    time.sleep(3)
    runs = _fetch_langsmith_runs(project, api_key, limit=10)
    graph_run = _find_graph_run(runs)
    assert graph_run is not None, "No graph run in LangSmith"

    # 两边都应该记录了执行
    print(f"  [L6 PASS] Dual trace:")
    print(f"    Local: trace_id={trace_id}, nodes={[n.name for n in local_trace.nodes]}")
    print(f"    LangSmith: graph_run_id={graph_run['id']}")
