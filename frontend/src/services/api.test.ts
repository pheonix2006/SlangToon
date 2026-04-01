import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { generateScript, generateComic, getHistory } from './api';

const mockFetch = vi.fn();
const originalFetch = globalThis.fetch;

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch);
  mockFetch.mockReset();
});

afterEach(() => {
  vi.stubGlobal('fetch', originalFetch);
});

function mockJsonResponse(data: unknown) {
  return {
    ok: true,
    status: 200,
    statusText: 'OK',
    headers: { get: () => null },
    json: () => Promise.resolve(data),
  } as Response;
}

function mockErrorResponse(status: number, statusText: string) {
  return {
    ok: false,
    status,
    statusText,
    headers: { get: () => null },
    json: () => Promise.resolve({}),
  } as Response;
}

// ─── generateScript ──────────────────────────────────────────────────────────

describe('generateScript', () => {
  const successBody = {
    code: 0,
    message: 'ok',
    data: {
      slang: 'YYDS',
      origin: 'The Shining',
      explanation: '永远的神',
      panel_count: 4,
      panels: [
        { scene: 'scene1', dialogue: 'dialogue1' },
      ],
    },
  };

  it('sends POST to /api/generate-script with empty body', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(successBody));

    await generateScript();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];

    expect(url).toBe('/api/generate-script');
    expect(options.method).toBe('POST');
    expect(options.headers).toEqual({ 'Content-Type': 'application/json' });

    const parsed = JSON.parse(options.body);
    expect(parsed).toEqual({});
  });

  it('returns script data on success', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(successBody));

    const result = await generateScript();
    expect(result.code).toBe(0);
    expect(result.data.slang).toBe('YYDS');
    expect(result.data.panels).toHaveLength(1);
  });

  it('throws on network error (TypeError) with correct message', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(generateScript()).rejects.toThrow('网络错误，请检查网络连接');
  });

  it('throws on business error (code !== 0) with server message', async () => {
    const bizError = { code: 500, message: '获取俚语失败' };
    mockFetch.mockResolvedValue(mockJsonResponse(bizError));

    await expect(generateScript()).rejects.toThrow('获取俚语失败');
  });

  it('throws on HTTP error (status 500)', async () => {
    mockFetch.mockResolvedValue(mockErrorResponse(500, 'Internal Server Error'));

    await expect(generateScript()).rejects.toThrow('请求失败 (500)');
  });
});

// ─── generateComic ───────────────────────────────────────────────────────────

describe('generateComic', () => {
  const scriptData = {
    slang: 'YYDS',
    origin: 'The Shining',
    explanation: '永远的神',
    panel_count: 4,
    panels: [
      { scene: 'scene1', dialogue: 'dialogue1' },
    ],
  };
  const successBody = {
    code: 0,
    message: 'ok',
    data: { comic_url: 'url', thumbnail_url: 'thumb', history_id: '1' },
  };

  it('sends POST to /api/generate-comic with script data', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(successBody));

    await generateComic(scriptData);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];

    expect(url).toBe('/api/generate-comic');
    expect(options.method).toBe('POST');
    expect(options.headers).toEqual({ 'Content-Type': 'application/json' });

    const parsed = JSON.parse(options.body);
    expect(parsed).toEqual(scriptData);
  });

  it('throws on network error', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(generateComic(scriptData)).rejects.toThrow(
      '网络错误，请检查网络连接',
    );
  });
});

// ─── getHistory ──────────────────────────────────────────────────────────────

describe('getHistory', () => {
  const successBody = {
    code: 0,
    message: 'ok',
    data: { items: [], total: 0, page: 2, page_size: 5, total_pages: 0 },
  };

  it('sends GET with correct query params (page=2, page_size=5 in URL)', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(successBody));

    await getHistory(2, 5);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];

    expect(url).toContain('/api/history?');
    expect(url).toContain('page=2');
    expect(url).toContain('page_size=5');
    expect(options.method).toBe('GET');
  });

  it('throws on network error', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(getHistory(1, 10)).rejects.toThrow('网络错误，请检查网络连接');
  });
});
