"""Tests for ReplicateProvider — 通用 Replicate 图像生成。"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from app.services.image_gen.base import ImageGenApiError, ImageGenTimeoutError, ImageSize
from app.services.image_gen.replicate_provider import ReplicateProvider


def _make_provider(**overrides) -> ReplicateProvider:
    defaults = dict(
        api_key="r8_test_token",
        model="google/imagen-4",
        timeout=5.0,
        max_retries=3,
        extra_params="",
    )
    defaults.update(overrides)
    return ReplicateProvider(**defaults)


def _fake_file_output(content: bytes = b"\x89PNG\r\n") -> MagicMock:
    fo = MagicMock()
    fo.read.return_value = content
    fo.url = "https://replicate.delivery/output/test.png"
    return fo


# ---------------------------------------------------------------------------
# _ensure_data_url
# ---------------------------------------------------------------------------

class TestEnsureDataUrl:

    def test_with_prefix(self) -> None:
        assert ReplicateProvider._ensure_data_url(
            "data:image/png;base64,abc"
        ) == "data:image/png;base64,abc"

    def test_without_prefix(self) -> None:
        assert ReplicateProvider._ensure_data_url(
            "abc123"
        ) == "data:image/jpeg;base64,abc123"


# ---------------------------------------------------------------------------
# _parse_extra_params
# ---------------------------------------------------------------------------

class TestParseExtraParams:

    def test_empty_string(self) -> None:
        assert ReplicateProvider._parse_extra_params("") == {}

    def test_valid_json(self) -> None:
        result = ReplicateProvider._parse_extra_params('{"quality":"auto","moderation":"auto"}')
        assert result == {"quality": "auto", "moderation": "auto"}

    def test_invalid_json_returns_empty(self) -> None:
        assert ReplicateProvider._parse_extra_params("not json") == {}

    def test_non_dict_json_returns_empty(self) -> None:
        assert ReplicateProvider._parse_extra_params("[1,2,3]") == {}


# ---------------------------------------------------------------------------
# _convert_size
# ---------------------------------------------------------------------------

class TestConvertSize:

    def test_16_9(self) -> None:
        assert ReplicateProvider._convert_size(ImageSize(2688, 1536)) == "16:9"

    def test_9_16(self) -> None:
        assert ReplicateProvider._convert_size(ImageSize(1536, 2688)) == "9:16"

    def test_1_1(self) -> None:
        assert ReplicateProvider._convert_size(ImageSize(1024, 1024)) == "1:1"

    def test_3_2(self) -> None:
        assert ReplicateProvider._convert_size(ImageSize(1536, 1024)) == "3:2"


# ---------------------------------------------------------------------------
# _build_input
# ---------------------------------------------------------------------------

class TestBuildInput:

    def test_only_prompt_and_aspect_ratio(self) -> None:
        p = _make_provider()
        params = p._build_input("draw a cat", ImageSize(2688, 1536))
        assert params == {
            "prompt": "draw a cat",
            "aspect_ratio": "16:9",
        }

    def test_extra_params_merged(self) -> None:
        p = _make_provider(
            extra_params='{"quality":"high","output_format":"webp","number_of_images":1}'
        )
        params = p._build_input("test", ImageSize(1024, 1024))
        assert params["quality"] == "high"
        assert params["output_format"] == "webp"
        assert params["number_of_images"] == 1
        assert params["prompt"] == "test"
        assert params["aspect_ratio"] == "1:1"

    def test_extra_params_can_override_aspect_ratio(self) -> None:
        p = _make_provider(extra_params='{"aspect_ratio":"3:2"}')
        params = p._build_input("test", ImageSize(1024, 1024))
        assert params["aspect_ratio"] == "3:2"


# ---------------------------------------------------------------------------
# generate_from_text
# ---------------------------------------------------------------------------

class TestGenerateFromText:

    @pytest.mark.asyncio
    async def test_success_list_output(self) -> None:
        p = _make_provider()
        image_bytes = b"\x89PNG_test_image"
        expected_b64 = base64.b64encode(image_bytes).decode("ascii")

        mock_client = MagicMock()
        mock_client.run.return_value = [_fake_file_output(image_bytes)]

        with patch(
            "app.services.image_gen.replicate_provider.replicate_sdk.Client",
            return_value=mock_client,
        ):
            result = await p.generate_from_text("draw a comic", ImageSize(2688, 1536))

        assert result == f"data:image/png;base64,{expected_b64}"

    @pytest.mark.asyncio
    async def test_success_single_output(self) -> None:
        p = _make_provider()
        image_bytes = b"\x89PNG_single"
        expected_b64 = base64.b64encode(image_bytes).decode("ascii")

        mock_client = MagicMock()
        mock_client.run.return_value = _fake_file_output(image_bytes)

        with patch(
            "app.services.image_gen.replicate_provider.replicate_sdk.Client",
            return_value=mock_client,
        ):
            result = await p.generate_from_text("draw", ImageSize(1024, 1024))

        assert result == f"data:image/png;base64,{expected_b64}"

    @pytest.mark.asyncio
    async def test_empty_output_raises(self) -> None:
        p = _make_provider()
        mock_client = MagicMock()
        mock_client.run.return_value = []

        with patch(
            "app.services.image_gen.replicate_provider.replicate_sdk.Client",
            return_value=mock_client,
        ):
            with pytest.raises(ImageGenApiError, match="未返回图片"):
                await p.generate_from_text("test", ImageSize(1024, 1024))

    @pytest.mark.asyncio
    async def test_none_output_raises(self) -> None:
        p = _make_provider()
        mock_client = MagicMock()
        mock_client.run.return_value = None

        with patch(
            "app.services.image_gen.replicate_provider.replicate_sdk.Client",
            return_value=mock_client,
        ):
            with pytest.raises(ImageGenApiError, match="未返回图片"):
                await p.generate_from_text("test", ImageSize(1024, 1024))

    @pytest.mark.asyncio
    async def test_api_error_raises(self) -> None:
        p = _make_provider()
        mock_client = MagicMock()
        mock_client.run.side_effect = RuntimeError("model not found")

        with patch(
            "app.services.image_gen.replicate_provider.replicate_sdk.Client",
            return_value=mock_client,
        ):
            with pytest.raises(ImageGenApiError, match="调用失败"):
                await p.generate_from_text("test", ImageSize(1024, 1024))

    @pytest.mark.asyncio
    async def test_download_error_raises(self) -> None:
        p = _make_provider()
        fo = _fake_file_output()
        fo.read.side_effect = IOError("connection reset")
        mock_client = MagicMock()
        mock_client.run.return_value = [fo]

        with patch(
            "app.services.image_gen.replicate_provider.replicate_sdk.Client",
            return_value=mock_client,
        ):
            with pytest.raises(ImageGenApiError, match="下载失败"):
                await p.generate_from_text("test", ImageSize(1024, 1024))


# ---------------------------------------------------------------------------
# generate (image-to-image)
# ---------------------------------------------------------------------------

class TestGenerate:

    @pytest.mark.asyncio
    async def test_success_with_image(self) -> None:
        p = _make_provider()
        image_bytes = b"\x89PNG_edited"
        expected_b64 = base64.b64encode(image_bytes).decode("ascii")

        mock_client = MagicMock()
        mock_client.run.return_value = [_fake_file_output(image_bytes)]

        with patch(
            "app.services.image_gen.replicate_provider.replicate_sdk.Client",
            return_value=mock_client,
        ):
            result = await p.generate(
                "edit this", "data:image/jpeg;base64,abc123", ImageSize(2688, 1536)
            )

        assert result == f"data:image/png;base64,{expected_b64}"
        input_params = mock_client.run.call_args[1]["input"]
        assert input_params["input_images"] == ["data:image/jpeg;base64,abc123"]
        assert input_params["prompt"] == "edit this"

    @pytest.mark.asyncio
    async def test_raw_base64_gets_prefix(self) -> None:
        p = _make_provider()
        mock_client = MagicMock()
        mock_client.run.return_value = [_fake_file_output()]

        with patch(
            "app.services.image_gen.replicate_provider.replicate_sdk.Client",
            return_value=mock_client,
        ):
            await p.generate("edit", "raw_b64", ImageSize(1024, 1024))

        input_params = mock_client.run.call_args[1]["input"]
        assert input_params["input_images"] == ["data:image/jpeg;base64,raw_b64"]


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------

class TestTimeout:

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        p = _make_provider(timeout=0.01)
        mock_client = MagicMock()

        def blocking_run(*args, **kwargs):
            import time
            time.sleep(10)

        mock_client.run.side_effect = blocking_run

        with patch(
            "app.services.image_gen.replicate_provider.replicate_sdk.Client",
            return_value=mock_client,
        ):
            with pytest.raises(ImageGenTimeoutError, match="超时"):
                await p.generate_from_text("test", ImageSize(1024, 1024))
