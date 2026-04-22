import type { ScriptResponse, ComicResponse, HistoryResponse } from '../types';
import { API_BASE_URL, API_ENDPOINTS, TIMEOUTS } from '../constants';

// ---------------------------------------------------------------------------
// 动态超时配置（从后端 /api/config 获取，失败时使用默认值）
// ---------------------------------------------------------------------------

/** 后端超时秒数 + 60s 缓冲 → 前端 fetch 超时毫秒数 */
const BUFFER_MS = 60_000;

const dynamicTimeouts: { script: number; comic: number } = {
  script: TIMEOUTS.SCRIPT_REQUEST,
  comic: TIMEOUTS.COMIC_REQUEST,
};

export async function fetchConfig(): Promise<void> {
  try {
    const resp = await fetch(`${API_BASE_URL}/api/config`, {
      signal: AbortSignal.timeout(5_000),
    });
    if (!resp.ok) return;
    const cfg = await resp.json() as {
      script_timeout_s: number;
      comic_timeout_s: number;
    };
    if (cfg.script_timeout_s) {
      dynamicTimeouts.script = cfg.script_timeout_s * 1000 + BUFFER_MS;
    }
    if (cfg.comic_timeout_s) {
      dynamicTimeouts.comic = cfg.comic_timeout_s * 1000 + BUFFER_MS;
    }
  } catch {
    // 获取失败时保持默认值
  }
}

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function parseApiError(error: unknown): string {
  if (error instanceof ApiError) {
    return `Request failed (${error.status}): ${error.statusText}`;
  }
  if (error instanceof DOMException && error.name === 'TimeoutError') {
    return 'Request timed out, please try again';
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'Request cancelled';
  }
  if (error instanceof TypeError) {
    return 'Network error, please check your connection';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Unknown error';
}

async function request<T>(
  endpoint: string,
  options: RequestInit,
  timeoutMs: number,
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const t0 = performance.now();

  try {
    const response = await fetch(url, {
      ...options,
      signal: AbortSignal.timeout(timeoutMs),
    });

    const traceId = response.headers.get('x-trace-id');
    console.log(
      '[FlowTrace] API response:',
      endpoint,
      '| trace_id:',
      traceId,
      '| status:',
      response.status,
      '| duration_ms:',
      Math.round(performance.now() - t0),
    );

    if (!response.ok) {
      throw new ApiError(
        `HTTP ${response.status}`,
        response.status,
        response.statusText,
      );
    }

    const data: T = await response.json();

    if (
      typeof data === 'object' &&
      data !== null &&
      'code' in data &&
      (data as { code: number }).code !== 0
    ) {
      const msg = 'message' in data
        ? String((data as { message: unknown }).message)
        : 'Server error';
      throw new ApiError(msg, response.status, msg);
    }

    return data;
  } catch (error) {
    throw new Error(parseApiError(error));
  }
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function generateScript(): Promise<ScriptResponse> {
  return request<ScriptResponse>(
    API_ENDPOINTS.GENERATE_SCRIPT,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    },
    dynamicTimeouts.script,
  );
}

export async function generateComic(
  scriptData: {
    slang: string;
    origin: string;
    explanation: string;
    panel_count: number;
    panels: { scene: string; dialogue: string }[];
    reference_image?: string;
  },
): Promise<ComicResponse> {
  return request<ComicResponse>(
    API_ENDPOINTS.GENERATE_COMIC,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scriptData),
    },
    dynamicTimeouts.comic,
  );
}

export async function getHistory(
  page: number,
  pageSize: number,
): Promise<HistoryResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  return request<HistoryResponse>(
    `${API_ENDPOINTS.HISTORY}?${params.toString()}`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    },
    TIMEOUTS.HISTORY_REQUEST,
  );
}
