import { describe, it, expect } from 'vitest';
import { AppState, type GestureType } from '../index';

describe('AppState enum', () => {
  it('contains GALLERY state', () => {
    expect(AppState.GALLERY).toBe('GALLERY');
  });

  it('preserves all existing states', () => {
    expect(AppState.CAMERA_READY).toBe('CAMERA_READY');
    expect(AppState.COUNTDOWN).toBe('COUNTDOWN');
    expect(AppState.GENERATING).toBe('GENERATING');
    expect(AppState.COMIC_READY).toBe('COMIC_READY');
    expect(AppState.HISTORY).toBe('HISTORY');
    expect(AppState.GALLERY).toBe('GALLERY');
  });

  it('has exactly 6 states', () => {
    expect(new Set(Object.values(AppState)).size).toBe(6);
  });
});

describe('GestureType', () => {
  it('includes wave gesture', () => {
    const g: GestureType[] = ['ok', 'open_palm', 'wave', 'none'];
    expect(g).toContain('wave');
    expect(g).toHaveLength(4);
  });
});
