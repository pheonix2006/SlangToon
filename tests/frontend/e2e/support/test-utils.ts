import { Page } from '@playwright/test';

export async function mockScriptAPI(page: Page) {
  await page.route('**/api/generate-script', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'success',
        data: {
          slang: 'Break a leg',
          origin: 'Western theater tradition',
          explanation: 'Used to wish good luck before a performance, ironically hoping the show is so successful that actors must bow so much their legs break.',
          panel_count: 8,
          panels: [
            {
              scene: 'A nervous actor paces backstage, clutching a crumpled script. The stage manager glances at the clock.',
              dialogue: 'Narrator: "It was opening night..."',
            },
            {
              scene: 'Friends gather around the actor, giving thumbs up with warm smiles.',
              dialogue: 'Friend: "You\'ve got this!"',
            },
            {
              scene: 'The actor steps onto the stage under a bright spotlight. The audience is a sea of silhouettes.',
              dialogue: '',
            },
            {
              scene: 'Standing ovation! Confetti falls. The actor beams with joy and happy tears.',
              dialogue: 'Narrator: "Break a leg indeed."',
            },
            {
              scene: 'The actor bows gracefully as the curtain begins to close.',
              dialogue: '',
            },
            {
              scene: 'Backstage, the cast celebrates with a group hug.',
              dialogue: 'Director: "Incredible!"',
            },
            {
              scene: 'The actor looks at the crumpled script, now smoothed out and signed by the cast.',
              dialogue: '',
            },
            {
              scene: 'The actor walks out of the theater into the night, smiling under the marquee lights.',
              dialogue: 'Narrator: "And that\'s how you break a leg."',
            },
          ],
        },
      }),
    });
  });
}

export async function mockComicAPI(page: Page) {
  await page.route('**/api/generate-comic', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'success',
        data: {
          comic_url: '/data/comics/test-comic.png',
          thumbnail_url: '/data/comics/test-thumb.png',
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
              slang: 'Break a leg',
              origin: 'Western theater tradition',
              explanation: 'Used to wish good luck before a performance.',
              panel_count: 8,
              comic_url: '/data/comics/comic1.png',
              thumbnail_url: '/data/comics/thumb1.png',
              comic_prompt: 'A 8-panel comic about theater...',
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

/** Mock data matching the generate-script API response structure. */
export const mockScriptData = {
  slang: 'Break a leg',
  origin: 'Western theater tradition',
  explanation: 'Used to wish good luck before a performance.',
  panel_count: 8,
  panels: [
    {
      scene: 'A nervous actor paces backstage, clutching a crumpled script.',
      dialogue: 'Narrator: "It was opening night..."',
    },
    {
      scene: 'Friends gather around the actor, giving thumbs up.',
      dialogue: 'Friend: "You\'ve got this!"',
    },
    {
      scene: 'The actor steps onto the stage under a bright spotlight.',
      dialogue: '',
    },
    {
      scene: 'Standing ovation! Confetti falls.',
      dialogue: 'Narrator: "Break a leg indeed."',
    },
    {
      scene: 'The actor bows gracefully as the curtain begins to close.',
      dialogue: '',
    },
    {
      scene: 'Backstage, the cast celebrates with a group hug.',
      dialogue: 'Director: "Incredible!"',
    },
    {
      scene: 'The actor looks at the crumpled script, now smoothed out and signed by the cast.',
      dialogue: '',
    },
    {
      scene: 'The actor walks out of the theater into the night, smiling under the marquee lights.',
      dialogue: 'Narrator: "And that\'s how you break a leg."',
    },
  ],
};
