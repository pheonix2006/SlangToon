import { test, expect } from '@playwright/test';
import { mockScriptAPI, mockComicAPI, mockHistoryAPI, mockScriptData } from './support/test-utils';

test.describe('Backend API Integration', () => {
  test('health endpoint responds', async ({ request }) => {
    const resp = await request.get('http://localhost:8888/health');
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('ok');
    expect(body.app).toBe('SlangToon');
  });

  test('generate-script API returns valid structure', async ({ page }) => {
    await mockScriptAPI(page);
    const resp = await page.request.post('/api/generate-script', {
      data: {},
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.code).toBe(0);
    expect(body.data.slang).toBeTruthy();
    expect(body.data.origin).toBeTruthy();
    expect(body.data.explanation).toBeTruthy();
    expect(body.data.panel_count).toBeGreaterThanOrEqual(4);
    expect(body.data.panel_count).toBeLessThanOrEqual(6);
    expect(body.data.panels).toHaveLength(body.data.panel_count);
    expect(body.data.panels[0]).toHaveProperty('scene');
    expect(body.data.panels[0]).toHaveProperty('dialogue');
  });

  test('generate-comic API returns valid structure', async ({ page }) => {
    await mockComicAPI(page);
    const resp = await page.request.post('/api/generate-comic', {
      data: mockScriptData,
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.code).toBe(0);
    expect(body.data.comic_url).toBeTruthy();
    expect(body.data.thumbnail_url).toBeTruthy();
    expect(body.data.history_id).toBeTruthy();
  });

  test('history API returns valid structure', async ({ request }) => {
    const resp = await request.get('http://localhost:8888/api/history?page=1&page_size=10');
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.code).toBe(0);
    expect('items' in body.data).toBeTruthy();
    expect('total' in body.data).toBeTruthy();
  });
});

test.describe('Error Handling', () => {
  test('generate-script error returns correct code', async ({ page }) => {
    await page.route('**/api/generate-script', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 50001, message: 'LLM 调用失败' }),
      });
    });
    const resp = await page.request.post('/api/generate-script', {
      data: {},
    });
    const body = await resp.json();
    expect(body.code).toBe(50001);
    expect(body.message).toBeTruthy();
  });

  test('generate-comic error returns correct code', async ({ page }) => {
    await page.route('**/api/generate-comic', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 50005, message: '图片生成失败' }),
      });
    });
    const resp = await page.request.post('/api/generate-comic', {
      data: mockScriptData,
    });
    const body = await resp.json();
    expect(body.code).toBe(50005);
  });

  test('generate-comic with missing fields returns validation error', async ({ page }) => {
    const resp = await page.request.post('http://localhost:8888/api/generate-comic', {
      data: { slang: 'test' },
    });
    expect(resp.status()).toBe(422);
  });

  test('generate-comic with empty body returns validation error', async ({ request }) => {
    const resp = await request.post('http://localhost:8888/api/generate-comic', {
      data: {},
    });
    expect(resp.status()).toBe(422);
  });

  test('generate-comic with invalid panel_count returns validation error', async ({ page }) => {
    const invalidData = {
      ...mockScriptData,
      panel_count: 10,
      panels: Array(10).fill({ scene: 'test', dialogue: '' }),
    };
    const resp = await page.request.post('http://localhost:8888/api/generate-comic', {
      data: invalidData,
    });
    expect(resp.status()).toBe(422);
  });

  test('generate-comic invalid script response error', async ({ page }) => {
    await page.route('**/api/generate-comic', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 50002, message: '脚本响应解析失败' }),
      });
    });
    const resp = await page.request.post('/api/generate-comic', {
      data: mockScriptData,
    });
    const body = await resp.json();
    expect(body.code).toBe(50002);
    expect(body.message).toBeTruthy();
  });
});

test.describe('Frontend App Loads', () => {
  test('app renders without crashing', async ({ page }) => {
    // Navigate to app — even without camera, the page should load
    const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(200);
  });
});
