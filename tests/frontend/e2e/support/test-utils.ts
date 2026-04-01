import { Page } from '@playwright/test';

export async function mockAnalyzeAPI(page: Page) {
  await page.route('**/api/analyze', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'success',
        data: {
          options: [
            { name: '赛博朋克', brief: '霓虹光影', prompt: 'cyberpunk neon city prompt' },
            { name: '武侠江湖', brief: '水墨刀剑', prompt: 'wuxia sword and ink prompt' },
            { name: '蒸汽朋克', brief: '齿轮蒸汽', prompt: 'steampunk gears and steam prompt' },
          ],
        },
      }),
    });
  });
}

export async function mockGenerateAPI(page: Page) {
  await page.route('**/api/generate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'success',
        data: {
          poster_url: '/data/posters/test-poster.png',
          thumbnail_url: '/data/posters/test-thumb.png',
          history_id: 'test-id-123',
        },
      }),
    });
  });
}

export async function mockHistoryAPI(page: Page) {
  await page.route('**/api/history', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'success',
        data: {
          items: [
            {
              id: '1',
              style_name: '赛博朋克',
              prompt: 'prompt',
              poster_url: '/poster1.png',
              thumbnail_url: '/thumb1.png',
              photo_url: '/photo1.jpg',
              created_at: '2026-03-29T10:00:00',
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      }),
    });
  });
}
