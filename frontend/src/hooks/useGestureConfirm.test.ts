import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGestureConfirm } from './useGestureConfirm';
import { AppState } from '../types';
import type { GestureType } from '../types';

describe('useGestureConfirm', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('initial state: no active gesture, progress 0', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.CAMERA_READY, onConfirmed }),
    );
    expect(result.current.activeGesture).toBeNull();
    expect(result.current.progress).toBe(0);
    expect(result.current.label).toBe('');
  });

  it('starts tracking when matching gesture detected', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.CAMERA_READY, onConfirmed }),
    );
    act(() => result.current.feedGesture('ok'));
    expect(result.current.activeGesture).toBe('ok');
    expect(result.current.label).toBe('Generate');
  });

  it('progress increases over time and triggers at holdMs', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.CAMERA_READY, onConfirmed }),
    );
    act(() => result.current.feedGesture('ok'));
    act(() => { vi.advanceTimersByTime(1500); });
    expect(result.current.progress).toBeGreaterThan(0.4);
    expect(result.current.progress).toBeLessThan(0.6);
    expect(onConfirmed).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(1500); });
    expect(onConfirmed).toHaveBeenCalledWith('generateScript');
  });

  it('resets progress when gesture changes', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.CAMERA_READY, onConfirmed }),
    );
    act(() => result.current.feedGesture('ok'));
    act(() => { vi.advanceTimersByTime(1500); });
    act(() => result.current.feedGesture('none'));
    expect(result.current.activeGesture).toBeNull();
    expect(result.current.progress).toBe(0);
    expect(onConfirmed).not.toHaveBeenCalled();
  });

  it('ignores gestures not in GESTURE_MAP for current state', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.CAMERA_READY, onConfirmed }),
    );
    act(() => result.current.feedGesture('open_palm'));
    expect(result.current.activeGesture).toBeNull();
    expect(result.current.progress).toBe(0);
  });

  it('locked states ignore all gestures', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.SCRIPT_LOADING, onConfirmed }),
    );
    act(() => result.current.feedGesture('ok'));
    expect(result.current.activeGesture).toBeNull();
    act(() => { vi.advanceTimersByTime(5000); });
    expect(onConfirmed).not.toHaveBeenCalled();
  });

  it('holdMs=0 triggers immediately (wave in GALLERY)', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.GALLERY, onConfirmed }),
    );
    act(() => result.current.feedGesture('wave'));
    expect(onConfirmed).toHaveBeenCalledWith('wakeUp');
  });

  it('cooldown prevents re-trigger for 1 second after confirmation', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.CAMERA_READY, onConfirmed }),
    );
    act(() => result.current.feedGesture('ok'));
    act(() => { vi.advanceTimersByTime(3000); });
    expect(onConfirmed).toHaveBeenCalledTimes(1);
    act(() => result.current.feedGesture('ok'));
    act(() => { vi.advanceTimersByTime(500); });
    expect(result.current.activeGesture).toBeNull();
    act(() => { vi.advanceTimersByTime(600); });
    act(() => result.current.feedGesture('ok'));
    expect(result.current.activeGesture).toBe('ok');
  });

  it('resets when appState changes', () => {
    const onConfirmed = vi.fn();
    const { result, rerender } = renderHook(
      ({ state }) => useGestureConfirm({ appState: state, onConfirmed }),
      { initialProps: { state: AppState.CAMERA_READY as AppState } },
    );
    act(() => result.current.feedGesture('ok'));
    act(() => { vi.advanceTimersByTime(1500); });
    expect(result.current.progress).toBeGreaterThan(0);
    rerender({ state: AppState.SCRIPT_LOADING });
    expect(result.current.activeGesture).toBeNull();
    expect(result.current.progress).toBe(0);
  });

  it('SCRIPT_PREVIEW: ok triggers generateComic', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.SCRIPT_PREVIEW, onConfirmed }),
    );
    act(() => result.current.feedGesture('ok'));
    expect(result.current.label).toBe('Create Comic');
    act(() => { vi.advanceTimersByTime(3000); });
    expect(onConfirmed).toHaveBeenCalledWith('generateComic');
  });

  it('SCRIPT_PREVIEW: open_palm triggers reshuffleScript', () => {
    const onConfirmed = vi.fn();
    const { result } = renderHook(() =>
      useGestureConfirm({ appState: AppState.SCRIPT_PREVIEW, onConfirmed }),
    );
    act(() => result.current.feedGesture('open_palm'));
    expect(result.current.label).toBe('Reshuffle');
    act(() => { vi.advanceTimersByTime(3000); });
    expect(onConfirmed).toHaveBeenCalledWith('reshuffleScript');
  });
});
