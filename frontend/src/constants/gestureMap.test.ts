import { describe, it, expect } from 'vitest';
import { AppState } from '../types';
import { GESTURE_MAP } from './gestureMap';

describe('GESTURE_MAP', () => {
  it('covers every AppState', () => {
    for (const state of Object.values(AppState)) {
      expect(GESTURE_MAP).toHaveProperty(state);
    }
  });

  it('COUNTDOWN and GENERATING are locked (empty)', () => {
    expect(GESTURE_MAP[AppState.COUNTDOWN]).toEqual([]);
    expect(GESTURE_MAP[AppState.GENERATING]).toEqual([]);
  });

  it('CAMERA_READY has ok gesture with 2000ms hold', () => {
    const actions = GESTURE_MAP[AppState.CAMERA_READY];
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({ gesture: 'ok', holdMs: 2000, action: 'startCountdown' });
  });

  it('COMIC_READY has ok gesture for startNew', () => {
    const actions = GESTURE_MAP[AppState.COMIC_READY];
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({ gesture: 'ok', holdMs: 2000, action: 'startNew' });
  });

  it('GALLERY has wave with holdMs=0 (immediate)', () => {
    const actions = GESTURE_MAP[AppState.GALLERY];
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({ gesture: 'wave', holdMs: 0, action: 'wakeUp' });
  });

  it('HISTORY is locked (empty)', () => {
    expect(GESTURE_MAP[AppState.HISTORY]).toEqual([]);
  });

  it('every action has a non-empty action string', () => {
    for (const actions of Object.values(GESTURE_MAP)) {
      for (const a of actions) {
        expect(a.action).toBeTruthy();
      }
    }
  });
});
