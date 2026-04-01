export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const API_ENDPOINTS = {
  ANALYZE: '/api/analyze',
  GENERATE: '/api/generate',
  HISTORY: '/api/history',
} as const;

export const TIMEOUTS = {
  ANALYZE_REQUEST: 200_000,
  GENERATE_REQUEST: 400_000,
  HISTORY_REQUEST: 10_000,
} as const;

export const COUNTDOWN_SECONDS = 3;
