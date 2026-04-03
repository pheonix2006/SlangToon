"""LangSmithClient 单元测试 — 覆盖 disabled / enabled / failure 降级三条路径。"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from app.tracing.langsmith_client import LangSmithClient, RunResult


# ---------------------------------------------------------------------------
# TestLangSmithClientDisabled — enabled=False
# ---------------------------------------------------------------------------

class TestLangSmithClientDisabled:
    """当 enabled=False 时，客户端应完全静默，不做任何 SDK 调用。"""

    def test_constructor_client_is_none(self):
        client = LangSmithClient(
            enabled=False, api_key="key", project="proj", endpoint="https://example.com"
        )
        assert client._client is None

    def test_start_run_returns_none(self):
        client = LangSmithClient(
            enabled=False, api_key="key", project="proj", endpoint="https://example.com"
        )
        result = client.start_run(name="test", run_type="llm", inputs={"q": "hi"})
        assert result is None

    def test_end_run_is_noop(self):
        client = LangSmithClient(
            enabled=False, api_key="key", project="proj", endpoint="https://example.com"
        )
        # 不应抛出任何异常
        client.end_run(run_id="abc-123")


# ---------------------------------------------------------------------------
# TestLangSmithClientEnabled — mock langsmith.Client
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ls_client():
    """Patch langsmith.Client so the real SDK is never called."""
    with patch("langsmith.Client") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        yield MockClient, mock_instance


class TestLangSmithClientEnabled:
    """当 enabled=True 且 SDK 正常时，start_run / end_run 应正确委托。"""

    def test_constructor_creates_sdk_client(self, mock_ls_client):
        MockClient, mock_instance = mock_ls_client
        client = LangSmithClient(
            enabled=True, api_key="sk-123", project="my-proj", endpoint="https://ls.test"
        )
        MockClient.assert_called_once_with(
            api_key="sk-123", api_url="https://ls.test"
        )
        assert client._client is mock_instance

    def test_start_run_returns_run_result(self, mock_ls_client):
        _, mock_instance = mock_ls_client
        client = LangSmithClient(
            enabled=True, api_key="k", project="p", endpoint="e"
        )
        result = client.start_run(
            name="gen-script",
            run_type="llm",
            inputs={"prompt": "hello"},
            parent_run_id="parent-001",
            extra={"tags": ["v2"]},
        )
        assert isinstance(result, RunResult)
        assert result.run_url.startswith("https://smith.langchain.com/o/default/runs/")
        assert len(result.run_id) > 0

        # 验证 create_run 被调用且参数正确
        create_call = mock_instance.create_run
        create_call.assert_called_once()
        call_kwargs = create_call.call_args[1]
        assert call_kwargs["name"] == "gen-script"
        assert call_kwargs["run_type"] == "llm"
        assert call_kwargs["inputs"] == {"prompt": "hello"}
        assert call_kwargs["parent_run_id"] == "parent-001"
        assert call_kwargs["extra"] == {"tags": ["v2"]}

    def test_end_run_calls_update_run(self, mock_ls_client):
        _, mock_instance = mock_ls_client
        client = LangSmithClient(
            enabled=True, api_key="k", project="p", endpoint="e"
        )
        client.end_run(
            run_id="run-abc",
            outputs={"answer": 42},
            error=None,
        )
        update_call = mock_instance.update_run
        update_call.assert_called_once()
        call_kwargs = update_call.call_args[1]
        assert call_kwargs["outputs"] == {"answer": 42}
        assert call_kwargs["error"] is None
        assert call_kwargs["end_time"] is not None

    def test_end_run_with_error(self, mock_ls_client):
        _, mock_instance = mock_ls_client
        client = LangSmithClient(
            enabled=True, api_key="k", project="p", endpoint="e"
        )
        client.end_run(run_id="run-err", error="timeout exceeded")
        call_kwargs = mock_instance.update_run.call_args[1]
        assert call_kwargs["error"] == "timeout exceeded"


# ---------------------------------------------------------------------------
# TestLangSmithClientFailureDegradation — SDK 抛异常时降级为 warning
# ---------------------------------------------------------------------------

class TestLangSmithClientFailureDegradation:
    """SDK 异常不应传播，应降级为 warning 日志。"""

    def test_constructor_init_failure_silenced(self):
        """Client() 构造抛异常 → _client 仍为 None，不传播。"""
        with patch("langsmith.Client", side_effect=RuntimeError("bad key")):
            client = LangSmithClient(
                enabled=True, api_key="bad", project="p", endpoint="e"
            )
            assert client._client is None

    def test_start_run_failure_returns_none(self):
        """create_run 抛异常 → 返回 None，不传播。"""
        with patch("langsmith.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.create_run.side_effect = ConnectionError("network down")
            MockClient.return_value = mock_instance

            client = LangSmithClient(
                enabled=True, api_key="k", project="p", endpoint="e"
            )
            result = client.start_run(name="x", run_type="llm", inputs={})
            assert result is None

    def test_end_run_failure_logs_warning_no_exception(self, caplog):
        """update_run 抛异常 → 仅 warning 日志，不向上传播。"""
        with patch("langsmith.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.update_run.side_effect = RuntimeError("fail")
            MockClient.return_value = mock_instance

            client = LangSmithClient(
                enabled=True, api_key="k", project="p", endpoint="e"
            )
            with caplog.at_level(logging.WARNING, logger="app.tracing.langsmith_client"):
                # 不应抛出异常
                client.end_run(run_id="r1")

            assert any("LangSmith end_run failed" in rec.message for rec in caplog.records)

    def test_start_run_failure_logs_warning(self, caplog):
        """start_run 失败时应有 warning 日志。"""
        with patch("langsmith.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.create_run.side_effect = RuntimeError("oops")
            MockClient.return_value = mock_instance

            client = LangSmithClient(
                enabled=True, api_key="k", project="p", endpoint="e"
            )
            with caplog.at_level(logging.WARNING, logger="app.tracing.langsmith_client"):
                client.start_run(name="x", run_type="llm", inputs={})

            assert any("LangSmith start_run failed" in rec.message for rec in caplog.records)
