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
        {"id": f"id-{i}", "style_name": f"style-{i}", "prompt": f"prompt-{i}",
         "poster_url": f"/poster-{i}.png", "thumbnail_url": f"/thumb-{i}.png",
         "photo_url": f"/photo-{i}.jpg", "created_at": f"2026-03-{29 - i:02d}T12:00:00+00:00"}
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
        {"id": "first", "style_name": "old", "prompt": "p1",
         "poster_url": "/p1.png", "thumbnail_url": "/t1.png",
         "photo_url": "/ph1.jpg", "created_at": "2026-03-28T10:00:00+00:00"},
        {"id": "second", "style_name": "new", "prompt": "p2",
         "poster_url": "/p2.png", "thumbnail_url": "/t2.png",
         "photo_url": "/ph2.jpg", "created_at": "2026-03-29T10:00:00+00:00"},
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
        "id": "test-id", "style_name": "cyberpunk", "prompt": "neon lights",
        "poster_url": "/poster.png", "thumbnail_url": "/thumb.png",
        "photo_url": "/photo.jpg", "created_at": "2026-03-29T12:00:00+00:00",
    }
    history_file.write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")

    resp = await client.get("/api/history")
    item = resp.json()["data"]["items"][0]
    assert item["id"] == "test-id"
    assert item["style_name"] == "cyberpunk"
    assert item["prompt"] == "neon lights"
    assert item["poster_url"] == "/poster.png"
    assert item["thumbnail_url"] == "/thumb.png"
    assert item["photo_url"] == "/photo.jpg"
    assert item["created_at"] == "2026-03-29T12:00:00+00:00"


@pytest.mark.asyncio
async def test_history_page_size_one(client, tmp_data_dir):
    """page_size=1 每页只返回 1 条"""
    import json
    history_file = tmp_data_dir / "history.json"
    records = [
        {"id": f"id-{i}", "style_name": f"s{i}", "prompt": f"p{i}",
         "poster_url": f"/p{i}.png", "thumbnail_url": f"/t{i}.png",
         "photo_url": f"/ph{i}.jpg", "created_at": "2026-03-29T12:00:00+00:00"}
        for i in range(3)
    ]
    history_file.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    resp = await client.get("/api/history", params={"page_size": 1})
    data = resp.json()["data"]
    assert len(data["items"]) == 1
    assert data["total"] == 3
    assert data["total_pages"] == 3
