import { describe, it, expect } from 'vitest';
import { AppState, type GestureType } from '../index';

describe('AppState enum', () => {
  it('contains GALLERY state', () => {
    expect(AppState.GALLERY).toBe('GALLERY');
  });

  it('preserves all existing states', () => {
    expect(AppState.CAMERA_READY).toBe('CAMERA_READY');
    expect(AppState.SCRIPT_LOADING).toBe('SCRIPT_LOADING');
    expect(AppState.SCRIPT_PREVIEW).toBe('SCRIPT_PREVIEW');
    expect(AppState.COMIC_GENERATING).toBe('COMIC_GENERATING');
    expect(AppState.COMIC_READY).toBe('COMIC_READY');
    expect(AppState.HISTORY).toBe('HISTORY');
  });

  it('has exactly 7 states', () => {
    expect(new Set(Object.values(AppState)).size).toBe(7);
  });
});

describe('GestureType', () => {
  it('includes wave gesture', () => {
    const g: GestureType[] = ['ok', 'open_palm', 'wave', 'none'];
    expect(g).toContain('wave');
    expect(g).toHaveLength(4);
  });
});
