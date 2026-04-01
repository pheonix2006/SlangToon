import type { AnalyzeResponse, GenerateResponse, HistoryResponse } from '../types';
import { API_BASE_URL, API_ENDPOINTS, TIMEOUTS } from '../constants';

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
    return `请求失败 (${error.status}): ${error.statusText}`;
  }
  if (error instanceof DOMException && error.name === 'TimeoutError') {
    return '请求超时，请稍后重试';
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return '请求被取消';
  }
  if (error instanceof TypeError) {
    return '网络错误，请检查网络连接';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '未知错误';
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

    // 提取 trace header（在 json() 之前）
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
        : '服务器返回错误';
      throw new ApiError(msg, response.status, msg);
    }

    return data;
  } catch (error) {
    throw new Error(parseApiError(error));
  }
}

export async function analyzePhoto(photoBase64: string): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>(
    API_ENDPOINTS.ANALYZE,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: photoBase64, image_format: 'jpeg' }),
    },
    TIMEOUTS.ANALYZE_REQUEST,
  );
}

export async function generatePoster(
  photoBase64: string,
  styleName: string,
  styleBrief: string,
): Promise<GenerateResponse> {
  return request<GenerateResponse>(
    API_ENDPOINTS.GENERATE,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: photoBase64,
        image_format: 'jpeg',
        style_name: styleName,
        style_brief: styleBrief,
      }),
    },
    TIMEOUTS.GENERATE_REQUEST,
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
