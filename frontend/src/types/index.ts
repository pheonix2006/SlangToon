export enum AppState {
  CAMERA_READY = 'CAMERA_READY',
  COUNTDOWN = 'COUNTDOWN',
  PHOTO_TAKEN = 'PHOTO_TAKEN',
  ANALYZING = 'ANALYZING',
  STYLE_SELECTION = 'STYLE_SELECTION',
  GENERATING = 'GENERATING',
  POSTER_READY = 'POSTER_READY',
  HISTORY = 'HISTORY',
}

export type GestureType = 'ok' | 'open_palm' | 'none';

export interface StyleOption {
  name: string;
  brief: string;
}

export interface AnalyzeResponse {
  code: number;
  message: string;
  data: { options: StyleOption[] };
}

export interface GenerateResponse {
  code: number;
  message: string;
  data: { poster_url: string; thumbnail_url: string; history_id: string };
}

export interface HistoryItem {
  id: string;
  photo_url: string;
  poster_url: string;
  thumbnail_url: string;
  style_name: string;
  prompt: string;
  created_at: string;
}

export interface HistoryResponse {
  code: number;
  message: string;
  data: {
    items: HistoryItem[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}
