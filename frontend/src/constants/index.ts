export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const API_ENDPOINTS = {
  GENERATE_SCRIPT: '/api/generate-script',
  GENERATE_COMIC: '/api/generate-comic',
  HISTORY: '/api/history',
} as const;

export const TIMEOUTS = {
  SCRIPT_REQUEST: 360_000, // 6 min — 匹配后端 LLM 超时 300s + 余量
  COMIC_REQUEST: 400_000,
  HISTORY_REQUEST: 10_000,
} as const;
