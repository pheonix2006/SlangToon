export enum AppState {
  CAMERA_READY = 'CAMERA_READY',
  SCRIPT_LOADING = 'SCRIPT_LOADING',
  SCRIPT_PREVIEW = 'SCRIPT_PREVIEW',
  COMIC_GENERATING = 'COMIC_GENERATING',
  COMIC_READY = 'COMIC_READY',
  HISTORY = 'HISTORY',
  GALLERY = 'GALLERY',
}

export type GestureType = 'ok' | 'open_palm' | 'wave' | 'none';

export interface Panel {
  scene: string;
  dialogue: string;
}

export interface ScriptData {
  slang: string;
  origin: string;
  explanation: string;
  panel_count: number;
  panels: Panel[];
}

export interface ScriptResponse {
  code: number;
  message: string;
  data: ScriptData;
}

export interface ComicResponse {
  code: number;
  message: string;
  data: {
    comic_url: string;
    thumbnail_url: string;
    history_id: string;
  };
}

export interface HistoryItem {
  id: string;
  slang: string;
  origin: string;
  explanation: string;
  panel_count: number;
  comic_url: string;
  thumbnail_url: string;
  comic_prompt: string;
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
