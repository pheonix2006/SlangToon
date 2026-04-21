import { AppState } from '../types';
import type { GestureAction } from '../types';

export const GESTURE_MAP: Record<AppState, GestureAction[]> = {
  [AppState.CAMERA_READY]: [
    { gesture: 'ok', holdMs: 2000, action: 'generateScript', label: 'Generate' },
  ],
  [AppState.SCRIPT_LOADING]: [],
  [AppState.SCRIPT_PREVIEW]: [
    { gesture: 'ok', holdMs: 2000, action: 'generateComic', label: 'Create Comic' },
    { gesture: 'open_palm', holdMs: 2000, action: 'reshuffleScript', label: 'Reshuffle' },
  ],
  [AppState.COMIC_GENERATING]: [],
  [AppState.COMIC_READY]: [
    { gesture: 'ok', holdMs: 2000, action: 'startNew', label: 'New Slang' },
  ],
  [AppState.GALLERY]: [
    { gesture: 'wave', holdMs: 0, action: 'wakeUp', label: '' },
  ],
  [AppState.HISTORY]: [],
};
