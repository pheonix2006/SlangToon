import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGestureDetector } from './useGestureDetector';
import type { NormalizedLandmark } from '../utils/gestureAlgo';

function makeLandmarks(
  overrides: Partial<Record<number, Partial<NormalizedLandmark>>> = {},
): NormalizedLandmark[] {
  const base: NormalizedLandmark = { x: 0.4, y: 0.6, z: 0 };
  const tipY = 0.3;
  const pipY = 0.6;
  const defaults: NormalizedLandmark[] = Array.from({ length: 21 }, () => ({ ...base }));
  defaults[5].y = pipY;
  defaults[6].y = pipY;
  defaults[10].y = pipY;
  defaults[14].y = pipY;
  defaults[18].y = pipY;
  defaults[4].y = tipY;
  defaults[3].y = 0.5;
  defaults[8].y = tipY;
  defaults[12].y = tipY;
  defaults[16].y = tipY;
  defaults[20].y = tipY;
  defaults[4].x = 0.2;
  defaults[8].x = 0.35;
  defaults[12].x = 0.45;
  defaults[16].x = 0.55;
  defaults[20].x = 0.65;
  for (const [idx, override] of Object.entries(overrides)) {
    const i = Number(idx);
    if (i >= 0 && i < 21) defaults[i] = { ...defaults[i], ...override };
  }
  return defaults;
}

function makeOKLandmarks(): NormalizedLandmark[] {
  return makeLandmarks({
    4: { x: 0.35, y: 0.3, z: 0 },
    8: { x: 0.35, y: 0.31, z: 0.001 },
  });
}

function makePalmLandmarks(): NormalizedLandmark[] {
  return makeLandmarks({
    4: { x: 0.1, y: 0.3, z: 0 },
    3: { x: 0.3, y: 0.5, z: 0 },
  });
}

function makeNoneLandmarks(): NormalizedLandmark[] {
  return makeLandmarks({
    4: { x: 0.2, y: 0.7, z: 0 },
    8: { x: 0.35, y: 0.7, z: 0 },
    12: { x: 0.45, y: 0.7, z: 0 },
    16: { x: 0.55, y: 0.7, z: 0 },
    20: { x: 0.65, y: 0.7, z: 0 },
  });
}

describe('useGestureDetector (frame-level output)', () => {
  it('initial state is none with 0 confidence', () => {
    const { result } = renderHook(() => useGestureDetector());
    expect(result.current.currentGesture).toBe('none');
    expect(result.current.currentConfidence).toBe(0);
  });

  it('outputs ok after 3 consecutive OK frames (debounce)', () => {
    const { result } = renderHook(() => useGestureDetector({ debounceFrames: 3 }));
    act(() => result.current.processLandmarks(makeOKLandmarks()));
    expect(result.current.currentGesture).toBe('none');
    act(() => result.current.processLandmarks(makeOKLandmarks()));
    expect(result.current.currentGesture).toBe('none');
    act(() => result.current.processLandmarks(makeOKLandmarks()));
    expect(result.current.currentGesture).toBe('ok');
  });

  it('resets to none when gesture changes mid-debounce', () => {
    const { result } = renderHook(() => useGestureDetector({ debounceFrames: 3 }));
    act(() => result.current.processLandmarks(makeOKLandmarks()));
    act(() => result.current.processLandmarks(makeOKLandmarks()));
    act(() => result.current.processLandmarks(makePalmLandmarks()));
    expect(result.current.currentGesture).toBe('none');
  });

  it('outputs open_palm after debounce threshold', () => {
    const { result } = renderHook(() => useGestureDetector({ debounceFrames: 3 }));
    for (let i = 0; i < 3; i++) {
      act(() => result.current.processLandmarks(makePalmLandmarks()));
    }
    expect(result.current.currentGesture).toBe('open_palm');
  });

  it('returns to none after none frames exceed debounce', () => {
    const { result } = renderHook(() => useGestureDetector({ debounceFrames: 3 }));
    for (let i = 0; i < 3; i++) {
      act(() => result.current.processLandmarks(makeOKLandmarks()));
    }
    expect(result.current.currentGesture).toBe('ok');
    for (let i = 0; i < 3; i++) {
      act(() => result.current.processLandmarks(makeNoneLandmarks()));
    }
    expect(result.current.currentGesture).toBe('none');
  });

  it('detects wave via onWaveDetected callback', () => {
    const onWave = vi.fn();
    const { result } = renderHook(() => useGestureDetector({ onWaveDetected: onWave }));
    for (let i = 0; i < 15; i++) {
      const landmarks = makeNoneLandmarks();
      landmarks[0].x = 0.4 + 0.1 * Math.sin(i * Math.PI / 3);
      act(() => result.current.processLandmarks(landmarks));
    }
    expect(onWave).toHaveBeenCalled();
  });

  it('wave cooldown prevents rapid re-trigger', () => {
    const onWave = vi.fn();
    const { result } = renderHook(() => useGestureDetector({ onWaveDetected: onWave }));
    for (let i = 0; i < 15; i++) {
      const landmarks = makeNoneLandmarks();
      landmarks[0].x = 0.4 + 0.1 * Math.sin(i * Math.PI / 3);
      act(() => result.current.processLandmarks(landmarks));
    }
    expect(onWave).toHaveBeenCalledTimes(1);
    for (let i = 0; i < 15; i++) {
      const landmarks = makeNoneLandmarks();
      landmarks[0].x = 0.4 + 0.1 * Math.sin(i * Math.PI / 3);
      act(() => result.current.processLandmarks(landmarks));
    }
    expect(onWave).toHaveBeenCalledTimes(1);
  });
});
