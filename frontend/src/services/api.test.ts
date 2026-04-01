import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { analyzePhoto, generatePoster, getHistory } from './api';

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
    json: () => Promise.resolve(data),
  } as Response;
}

function mockErrorResponse(status: number, statusText: string) {
  return {
    ok: false,
    status,
    statusText,
    json: () => Promise.resolve({}),
  } as Response;
}

// ─── analyzePhoto ────────────────────────────────────────────────────────────

describe('analyzePhoto', () => {
  const base64 = 'aGVsbG8=';
  const successBody = {
    code: 0,
    message: 'ok',
    data: { options: [{ name: 'style1', brief: 'b' }] },
  };

  it('sends POST with correct URL, method, Content-Type header, and body fields', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(successBody));

    await analyzePhoto(base64);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];

    expect(url).toBe('/api/analyze');
    expect(options.method).toBe('POST');
    expect(options.headers).toEqual({ 'Content-Type': 'application/json' });

    const parsed = JSON.parse(options.body);
    expect(parsed).toEqual({
      image_base64: base64,
      image_format: 'jpeg',
    });
  });

  it('throws on network error (TypeError) with correct message', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(analyzePhoto(base64)).rejects.toThrow('网络错误，请检查网络连接');
  });

  it('throws on business error (code !== 0) with server message', async () => {
    const bizError = { code: 500, message: '图片格式不支持' };
    mockFetch.mockResolvedValue(mockJsonResponse(bizError));

    await expect(analyzePhoto(base64)).rejects.toThrow('图片格式不支持');
  });

  it('throws on HTTP error (status 500)', async () => {
    mockFetch.mockResolvedValue(mockErrorResponse(500, 'Internal Server Error'));

    await expect(analyzePhoto(base64)).rejects.toThrow('请求失败 (500)');
  });
});

// ─── generatePoster ──────────────────────────────────────────────────────────

describe('generatePoster', () => {
  const base64 = 'aGVsbG8=';
  const styleName = 'cyberpunk';
  const styleBrief = 'a beautiful poster';
  const successBody = {
    code: 0,
    message: 'ok',
    data: { poster_url: 'url', thumbnail_url: 'thumb', history_id: '1' },
  };

  it('sends POST with correct body fields (image_base64, image_format, style_name, style_brief)', async () => {
    mockFetch.mockResolvedValue(mockJsonResponse(successBody));

    await generatePoster(base64, styleName, styleBrief);

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];

    expect(url).toBe('/api/generate');
    expect(options.method).toBe('POST');
    expect(options.headers).toEqual({ 'Content-Type': 'application/json' });

    const parsed = JSON.parse(options.body);
    expect(parsed).toEqual({
      image_base64: base64,
      image_format: 'jpeg',
      style_name: styleName,
      style_brief: styleBrief,
    });
  });

  it('throws on network error', async () => {
    mockFetch.mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(generatePoster(base64, styleName, styleBrief)).rejects.toThrow(
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
