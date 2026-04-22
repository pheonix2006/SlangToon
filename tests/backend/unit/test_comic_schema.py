"""Tests for ComicRequest schema — reference_image field."""

import pytest
from pydantic import ValidationError
from app.schemas.comic import ComicRequest


class TestComicRequestReferenceImage:

    def _base_data(self, **overrides):
        data = {
            "slang": "Break a leg",
            "origin": "Western theater",
            "explanation": "Good luck",
            "panel_count": 4,
            "panels": [
                {"scene": f"Scene {i}", "dialogue": f"Line {i}"}
                for i in range(4)
            ],
        }
        data.update(overrides)
        return data

    def test_without_reference_image(self):
        req = ComicRequest(**self._base_data())
        assert req.reference_image is None

    def test_with_reference_image(self):
        b64 = "data:image/jpeg;base64,/9j/4AAQ..."
        req = ComicRequest(**self._base_data(reference_image=b64))
        assert req.reference_image == b64

    def test_reference_image_none_explicit(self):
        req = ComicRequest(**self._base_data(reference_image=None))
        assert req.reference_image is None

    def test_model_dump_includes_reference_image(self):
        b64 = "data:image/jpeg;base64,abc123"
        req = ComicRequest(**self._base_data(reference_image=b64))
        dumped = req.model_dump()
        assert dumped["reference_image"] == b64

    def test_model_dump_without_reference_image(self):
        req = ComicRequest(**self._base_data())
        dumped = req.model_dump()
        assert dumped["reference_image"] is None
