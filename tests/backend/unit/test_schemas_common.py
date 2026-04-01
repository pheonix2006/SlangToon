from app.schemas.common import ApiResponse, ErrorResponse, ErrorCode
from app.schemas.history import HistoryItem, HistoryResponse


# ── ApiResponse ──────────────────────────────────────────────────────────────


class TestApiResponse:
    def test_success_default_values(self):
        resp = ApiResponse()
        assert resp.code == 0
        assert resp.message == "success"
        assert resp.data is None

    def test_success_with_data(self):
        resp = ApiResponse(data={"key": "value"})
        assert resp.data == {"key": "value"}
        assert resp.code == 0
        assert resp.message == "success"

    def test_error_response(self):
        resp = ApiResponse(code=50001, message="LLM 调用失败")
        assert resp.code == 50001
        assert resp.message == "LLM 调用失败"
        assert resp.data is None

    def test_serialization(self):
        resp = ApiResponse(data={"result": 42})
        dumped = resp.model_dump()
        assert dumped == {
            "code": 0,
            "message": "success",
            "data": {"result": 42},
        }


# ── ErrorResponse ────────────────────────────────────────────────────────────


class TestErrorResponse:
    def test_required_fields(self):
        err = ErrorResponse(code=40001, message="参数错误")
        assert err.code == 40001
        assert err.message == "参数错误"
        assert err.data is None

    def test_with_optional_data(self):
        err = ErrorResponse(code=50003, message="图片生成失败", data={"detail": "timeout"})
        assert err.code == 50003
        assert err.message == "图片生成失败"
        assert err.data == {"detail": "timeout"}


# ── ErrorCode ────────────────────────────────────────────────────────────────


class TestErrorCode:
    def test_values_are_unique(self):
        values = [
            ErrorCode.BAD_REQUEST,
            ErrorCode.UNSUPPORTED_FORMAT,
            ErrorCode.IMAGE_TOO_LARGE,
            ErrorCode.VISION_LLM_FAILED,
            ErrorCode.VISION_LLM_INVALID,
            ErrorCode.IMAGE_GEN_FAILED,
            ErrorCode.IMAGE_DOWNLOAD_FAILED,
            ErrorCode.INTERNAL_ERROR,
        ]
        assert len(values) == len(set(values)), "ErrorCode values must be unique"

    def test_error_ranges(self):
        client_errors = [
            ErrorCode.BAD_REQUEST,
            ErrorCode.UNSUPPORTED_FORMAT,
            ErrorCode.IMAGE_TOO_LARGE,
        ]
        server_errors = [
            ErrorCode.VISION_LLM_FAILED,
            ErrorCode.VISION_LLM_INVALID,
            ErrorCode.IMAGE_GEN_FAILED,
            ErrorCode.IMAGE_DOWNLOAD_FAILED,
            ErrorCode.INTERNAL_ERROR,
        ]

        for code in client_errors:
            assert 40000 <= code <= 49999, f"Client error {code} out of 4xxxx range"

        for code in server_errors:
            assert 50000 <= code <= 59999, f"Server error {code} out of 5xxxx range"


# ── History Schemas ──────────────────────────────────────────────────────────


class TestHistorySchemas:
    def test_history_item_required_fields(self):
        item = HistoryItem(
            id="abc123",
            style_name="动漫风格",
            prompt="一只可爱的猫咪",
            poster_url="https://example.com/poster.png",
            thumbnail_url="https://example.com/thumb.png",
            photo_url="https://example.com/photo.jpg",
            created_at="2026-03-29T12:00:00Z",
        )
        assert item.id == "abc123"
        assert item.style_name == "动漫风格"
        assert item.prompt == "一只可爱的猫咪"
        assert item.poster_url == "https://example.com/poster.png"
        assert item.thumbnail_url == "https://example.com/thumb.png"
        assert item.photo_url == "https://example.com/photo.jpg"
        assert item.created_at == "2026-03-29T12:00:00Z"

    def test_history_item_optional_photo_url(self):
        item = HistoryItem(
            id="abc123",
            style_name="动漫风格",
            prompt="一只可爱的猫咪",
            poster_url="https://example.com/poster.png",
            thumbnail_url="https://example.com/thumb.png",
            created_at="2026-03-29T12:00:00Z",
        )
        assert item.photo_url == ""

    def test_history_response_fields(self):
        resp = HistoryResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert resp.items == []
        assert resp.total == 0
        assert resp.page == 1
        assert resp.page_size == 20
        assert resp.total_pages == 0
