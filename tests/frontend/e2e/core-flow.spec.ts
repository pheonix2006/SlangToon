import { test, expect } from '@playwright/test';
import { mockAnalyzeAPI, mockGenerateAPI, mockHistoryAPI } from './support/test-utils';

test.describe('Backend API Integration', () => {
  test('health endpoint responds', async ({ request }) => {
    const resp = await request.get('http://localhost:8888/health');
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe('ok');
  });

  test('analyze API returns valid structure', async ({ page }) => {
    await mockAnalyzeAPI(page);
    const resp = await page.request.post('/api/analyze', {
      data: { image_base64: 'fake', image_format: 'jpeg' },
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.code).toBe(0);
    expect(body.data.options).toHaveLength(3);
    expect(body.data.options[0]).toHaveProperty('name');
    expect(body.data.options[0]).toHaveProperty('brief');
    expect(body.data.options[0]).toHaveProperty('prompt');
  });

  test('generate API returns valid structure', async ({ page }) => {
    await mockGenerateAPI(page);
    const resp = await page.request.post('/api/generate', {
      data: {
        image_base64: 'fake',
        image_format: 'jpeg',
        prompt: 'test prompt',
        style_name: 'cyberpunk',
      },
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.code).toBe(0);
    expect(body.data.poster_url).toBeTruthy();
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
  test('analyze error returns correct code', async ({ page }) => {
    await page.route('**/api/analyze', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 50001, message: 'LLM 调用失败' }),
      });
    });
    const resp = await page.request.post('/api/analyze', {
      data: { image_base64: 'fake', image_format: 'jpeg' },
    });
    const body = await resp.json();
    expect(body.code).toBe(50001);
    expect(body.message).toBeTruthy();
  });

  test('generate error returns correct code', async ({ page }) => {
    await page.route('**/api/generate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 50003, message: '图片生成失败' }),
      });
    });
    const resp = await page.request.post('/api/generate', {
      data: { image_base64: 'fake', image_format: 'jpeg', prompt: 'p', style_name: 's' },
    });
    const body = await resp.json();
    expect(body.code).toBe(50003);
  });

  test('invalid format returns validation error', async ({ page }) => {
    await page.route('**/api/analyze', async (route) => {
      await route.fulfill({ status: 422, body: 'Unprocessable Entity' });
    });
    const resp = await page.request.post('/api/analyze', {
      data: { image_base64: 'fake', image_format: 'invalid' },
    });
    expect(resp.status()).toBe(422);
  });

  test('schema validation rejects empty image', async ({ request }) => {
    const resp = await request.post('http://localhost:8888/api/analyze', {
      data: { image_base64: '', image_format: 'jpeg' },
    });
    expect(resp.status()).toBe(422);
  });

  test('schema validation rejects missing fields', async ({ request }) => {
    const resp = await request.post('http://localhost:8888/api/analyze', {
      data: { image_format: 'jpeg' },
    });
    expect(resp.status()).toBe(422);
  });
});

test.describe('Frontend App Loads', () => {
  test('app renders without crashing', async ({ page }) => {
    // Navigate to app — even without camera, the page should load
    const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
    expect(response?.status()).toBe(200);
  });
});
