import { AppState } from '../types';
import type { GestureAction } from '../types';

export const GESTURE_MAP: Record<AppState, GestureAction[]> = {
  [AppState.CAMERA_READY]: [
    { gesture: 'ok', holdMs: 2000, action: 'startCountdown', label: 'Take Photo' },
  ],
  [AppState.COUNTDOWN]: [],
  [AppState.GENERATING]: [],
  [AppState.COMIC_READY]: [
    { gesture: 'ok', holdMs: 2000, action: 'startNew', label: 'New Slang' },
  ],
  [AppState.GALLERY]: [
    { gesture: 'wave', holdMs: 0, action: 'wakeUp', label: '' },
  ],
  [AppState.HISTORY]: [],
};
