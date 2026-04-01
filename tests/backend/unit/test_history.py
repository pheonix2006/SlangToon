import pytest


@pytest.mark.asyncio
async def test_history_empty(client, tmp_data_dir):
    """空历史记录 — items 为空列表, total 为 0"""
    resp = await client.get("/api/history")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["items"] == []
    assert data["data"]["total"] == 0


@pytest.mark.asyncio
async def test_history_default_pagination(client):
    """默认分页参数 — page==1, page_size==20"""
    resp = await client.get("/api/history")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_history_custom_pagination(client):
    """自定义 page_size=5"""
    resp = await client.get("/api/history", params={"page_size": 5})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert data["total_pages"] == 1  # 空数据时 total_pages 为 max(1, ...)


@pytest.mark.asyncio
async def test_history_page_beyond_total(client):
    """请求超出总页数的 page — items 为空"""
    resp = await client.get("/api/history", params={"page": 9999})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 9999


@pytest.mark.asyncio
async def test_history_invalid_page(client):
    """page=0 — 应返回 422 验证错误"""
    resp = await client.get("/api/history", params={"page": 0})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_history_page_size_exceeds_limit(client):
    """page_size=200 超过上限 100 — 应返回 422 验证错误"""
    resp = await client.get("/api/history", params={"page_size": 200})
    assert resp.status_code == 422


# ------------------------------------------------------------------
# 补充: 有数据时的分页行为
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_history_with_data(client, tmp_data_dir):
    """有记录时返回正确的分页数据"""
    import json
    history_file = tmp_data_dir / "history.json"
    records = [
        {"id": f"id-{i}", "slang": f"slang-{i}", "origin": "Western",
         "explanation": f"explain-{i}", "panel_count": 4,
         "comic_url": f"/comic-{i}.png", "thumbnail_url": f"/thumb-{i}.png",
         "comic_prompt": f"prompt-{i}", "created_at": f"2026-03-{29 - i:02d}T12:00:00+00:00"}
        for i in range(5)
    ]
    history_file.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    resp = await client.get("/api/history")
    data = resp.json()["data"]
    assert data["total"] == 5
    assert len(data["items"]) == 5
    assert data["total_pages"] == 1


@pytest.mark.asyncio
async def test_history_order_descending(client, tmp_data_dir):
    """历史记录应按插入顺序倒序排列（最新在前）"""
    import json
    history_file = tmp_data_dir / "history.json"
    records = [
        {"id": "first", "slang": "old-slang", "origin": "Western",
         "explanation": "old explain", "panel_count": 4,
         "comic_url": "/c1.png", "thumbnail_url": "/t1.png",
         "comic_prompt": "p1", "created_at": "2026-03-28T10:00:00+00:00"},
        {"id": "second", "slang": "new-slang", "origin": "Eastern",
         "explanation": "new explain", "panel_count": 5,
         "comic_url": "/c2.png", "thumbnail_url": "/t2.png",
         "comic_prompt": "p2", "created_at": "2026-03-29T10:00:00+00:00"},
    ]
    history_file.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    resp = await client.get("/api/history")
    items = resp.json()["data"]["items"]
    # JSON 中 first 在前 = 最先插入 = 最新在前（insert(0) 逻辑）
    assert items[0]["id"] == "first"
    assert items[1]["id"] == "second"


@pytest.mark.asyncio
async def test_history_negative_page(client):
    """page=-1 — 应返回 422"""
    resp = await client.get("/api/history", params={"page": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_history_record_fields_complete(client, tmp_data_dir):
    """历史记录字段应完整"""
    import json
    history_file = tmp_data_dir / "history.json"
    record = {
        "id": "test-id", "slang": "Break a leg", "origin": "Western",
        "explanation": "Good luck wish", "panel_count": 4,
        "comic_url": "/comic.png", "thumbnail_url": "/thumb.png",
        "comic_prompt": "neon lights", "created_at": "2026-03-29T12:00:00+00:00",
    }
    history_file.write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")

    resp = await client.get("/api/history")
    item = resp.json()["data"]["items"][0]
    assert item["id"] == "test-id"
    assert item["slang"] == "Break a leg"
    assert item["comic_prompt"] == "neon lights"
    assert item["comic_url"] == "/comic.png"
    assert item["thumbnail_url"] == "/thumb.png"
    assert item["created_at"] == "2026-03-29T12:00:00+00:00"


@pytest.mark.asyncio
async def test_history_page_size_one(client, tmp_data_dir):
    """page_size=1 每页只返回 1 条"""
    import json
    history_file = tmp_data_dir / "history.json"
    records = [
        {"id": f"id-{i}", "slang": f"s{i}", "origin": "Western",
         "explanation": f"exp-{i}", "panel_count": 4,
         "comic_url": f"/c{i}.png", "thumbnail_url": f"/t{i}.png",
         "comic_prompt": f"p{i}", "created_at": "2026-03-29T12:00:00+00:00"}
        for i in range(3)
    ]
    history_file.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    resp = await client.get("/api/history", params={"page_size": 1})
    data = resp.json()["data"]
    assert len(data["items"]) == 1
    assert data["total"] == 3
    assert data["total_pages"] == 3
