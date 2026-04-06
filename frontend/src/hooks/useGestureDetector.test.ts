import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useGestureDetector } from './useGestureDetector';
import type { NormalizedLandmark } from '../utils/gestureAlgo';
import type { GestureType } from '../types';

/**
 * Helper: create 21 NormalizedLandmark objects with sensible defaults.
 *
 * Default positions simulate a hand facing the camera:
 *  - Wrist (0) at origin
 *  - Finger bases along x-axis
 *  - Finger PIP joints at y=0.6
 *  - Finger TIP joints at y=0.3 (above PIP => extended)
 *
 * Pass an object like `{ 4: { x: 0.1, y: 0.2, z: 0 } }` to override
 * specific landmark indices.
 */
function makeLandmarks(
  overrides: Partial<Record<number, Partial<NormalizedLandmark>>> = {},
): NormalizedLandmark[] {
  const base: NormalizedLandmark = { x: 0.4, y: 0.6, z: 0 };
  const tipY = 0.3;
  const pipY = 0.6;

  const defaults: NormalizedLandmark[] = Array.from({ length: 21 }, () => ({
    ...base,
  }));

  // Set PIP joints
  defaults[5].y = pipY;  // INDEX_MCP
  defaults[6].y = pipY;  // INDEX_PIP
  defaults[10].y = pipY; // MIDDLE_PIP
  defaults[14].y = pipY; // RING_PIP
  defaults[18].y = pipY; // PINKY_PIP

  // Set tip joints (lower y = extended)
  defaults[4].y = tipY;  // THUMB_TIP
  defaults[3].y = 0.5;   // THUMB_IP
  defaults[8].y = tipY;  // INDEX_TIP
  defaults[12].y = tipY; // MIDDLE_TIP
  defaults[16].y = tipY; // RING_TIP
  defaults[20].y = tipY; // PINKY_TIP

  // Spread fingertips horizontally so OK gesture isn't triggered by default
  defaults[4].x = 0.2;   // THUMB_TIP far from INDEX_TIP
  defaults[8].x = 0.35;  // INDEX_TIP
  defaults[12].x = 0.45; // MIDDLE_TIP
  defaults[16].x = 0.55; // RING_TIP
  defaults[20].x = 0.65; // PINKY_TIP

  // Apply overrides
  for (const [idx, override] of Object.entries(overrides)) {
    const i = Number(idx);
    if (i >= 0 && i < 21) {
      defaults[i] = { ...defaults[i], ...override };
    }
  }

  return defaults;
}

/** OK gesture landmarks: thumb tip (4) close to index tip (8), middle/ring/pinky extended */
function makeOKLandmarks(): NormalizedLandmark[] {
  return makeLandmarks({
    4: { x: 0.35, y: 0.3, z: 0 },
    8: { x: 0.35, y: 0.31, z: 0.001 },
  });
}

/** Open palm landmarks: all 5 fingers extended, thumb far from index */
function makePalmLandmarks(): NormalizedLandmark[] {
  return makeLandmarks({
    4: { x: 0.1, y: 0.3, z: 0 },
    3: { x: 0.3, y: 0.5, z: 0 },
  });
}

/** None gesture landmarks: all fingers curled (tips below PIPs) */
function makeNoneLandmarks(): NormalizedLandmark[] {
  return makeLandmarks({
    4: { y: 0.8 },
    8: { y: 0.8 },
    12: { y: 0.8 },
    16: { y: 0.8 },
    20: { y: 0.8 },
  });
}

describe('useGestureDetector', () => {
  it('triggers callback after OK threshold (3 frames)', () => {
    const onGestureDetected = vi.fn();
    const { result } = renderHook(() =>
      useGestureDetector({ onGestureDetected, okThreshold: 3, palmThreshold: 2 }),
    );

    // Frame 1: counter becomes 1 (first OK frame), no trigger
    result.current.processLandmarks(makeOKLandmarks());
    expect(onGestureDetected).not.toHaveBeenCalled();

    // Frame 2: counter becomes 2, no trigger
    result.current.processLandmarks(makeOKLandmarks());
    expect(onGestureDetected).not.toHaveBeenCalled();

    // Frame 3: counter becomes 3 >= threshold(3), triggers
    result.current.processLandmarks(makeOKLandmarks());
    expect(onGestureDetected).toHaveBeenCalledTimes(1);
    expect(onGestureDetected).toHaveBeenCalledWith(
      expect.objectContaining({
        gesture: 'ok',
        confidence: expect.any(Number),
        detectedAt: expect.any(Date),
      }),
    );
  });

  it('triggers callback after palm threshold (2 frames)', () => {
    const onGestureDetected = vi.fn();
    const { result } = renderHook(() =>
      useGestureDetector({ onGestureDetected, okThreshold: 3, palmThreshold: 2 }),
    );

    // Frame 1: counter becomes 1 (first palm frame), no trigger
    result.current.processLandmarks(makePalmLandmarks());
    expect(onGestureDetected).not.toHaveBeenCalled();

    // Frame 2: counter becomes 2 >= threshold(2), triggers
    result.current.processLandmarks(makePalmLandmarks());
    expect(onGestureDetected).toHaveBeenCalledTimes(1);
    expect(onGestureDetected).toHaveBeenCalledWith(
      expect.objectContaining({
        gesture: 'open_palm',
      }),
    );
  });

  it('resets counter when gesture changes', () => {
    const onGestureDetected = vi.fn();
    const { result } = renderHook(() =>
      useGestureDetector({ onGestureDetected, okThreshold: 3, palmThreshold: 2 }),
    );

    // 2 OK frames (counter = 2)
    result.current.processLandmarks(makeOKLandmarks());
    result.current.processLandmarks(makeOKLandmarks());
    expect(onGestureDetected).not.toHaveBeenCalled();

    // Switch to palm: counter resets to 1
    result.current.processLandmarks(makePalmLandmarks());
    expect(onGestureDetected).not.toHaveBeenCalled();

    // 2nd palm frame: counter = 2 >= threshold(2), triggers palm
    result.current.processLandmarks(makePalmLandmarks());
    expect(onGestureDetected).toHaveBeenCalledTimes(1);
    expect(onGestureDetected).toHaveBeenCalledWith(
      expect.objectContaining({ gesture: 'open_palm' }),
    );

    // OK was never triggered
    const okCalls = onGestureDetected.mock.calls.filter(
      (call: unknown[]) => (call[0] as { gesture: string }).gesture === 'ok',
    );
    expect(okCalls).toHaveLength(0);
  });

  it('resets counter on none gesture', () => {
    const onGestureDetected = vi.fn();
    const { result } = renderHook(() =>
      useGestureDetector({ onGestureDetected, okThreshold: 3, palmThreshold: 2 }),
    );

    // 2 OK frames (counter = 2)
    result.current.processLandmarks(makeOKLandmarks());
    result.current.processLandmarks(makeOKLandmarks());
    expect(onGestureDetected).not.toHaveBeenCalled();

    // 1 none frame: resets counter to 0, lastGesture to 'none'
    result.current.processLandmarks(makeNoneLandmarks());
    expect(onGestureDetected).not.toHaveBeenCalled();

    // 1st OK frame after reset: counter = 1
    result.current.processLandmarks(makeOKLandmarks());
    expect(onGestureDetected).not.toHaveBeenCalled();

    // 2nd OK frame after reset: counter = 2
    result.current.processLandmarks(makeOKLandmarks());
    expect(onGestureDetected).not.toHaveBeenCalled();

    // 3rd OK frame after reset: counter = 3 >= threshold(3), triggers
    result.current.processLandmarks(makeOKLandmarks());
    expect(onGestureDetected).toHaveBeenCalledTimes(1);
    expect(onGestureDetected).toHaveBeenCalledWith(
      expect.objectContaining({ gesture: 'ok' }),
    );
  });
});

describe('Wave detection integration', () => {
  /**
   * Helper: create landmarks with a specific wrist x value.
   * Uses makeNoneLandmarks as base so detectGesture returns 'none',
   * allowing wave detection logic to be tested in isolation.
   */
  function makeWristLandmarks(wristX: number): NormalizedLandmark[] {
    const lm = makeNoneLandmarks();
    lm[0] = { ...lm[0], x: wristX };
    return lm;
  }

  it('detects wave gesture after oscillating frames', () => {
    const gestures: GestureType[] = [];
    const { result } = renderHook(() =>
      useGestureDetector({
        onGestureDetected: (e) => gestures.push(e.gesture),
        okThreshold: 3,
        palmThreshold: 2,
      }),
    );

    // Simulate oscillating wrist (wave motion) with amplitude > threshold
    // detectWave needs >= 12 samples and peak-to-peak >= ~0.17
    for (let i = 0; i < 20; i++) {
      result.current.processLandmarks(
        makeWristLandmarks(i % 2 === 0 ? 0.25 : 0.55),
      );
    }

    expect(gestures).toContain('wave');
  });

  it('does not trigger wave for stationary wrist', () => {
    const gestures: GestureType[] = [];
    const { result } = renderHook(() =>
      useGestureDetector({
        onGestureDetected: (e) => gestures.push(e.gesture),
        okThreshold: 3,
        palmThreshold: 2,
      }),
    );

    // Stationary wrist - no oscillation
    for (let i = 0; i < 25; i++) {
      result.current.processLandmarks(makeWristLandmarks(0.4));
    }

    expect(gestures).not.toContain('wave');
  });

  it('clears wave buffer when non-none gesture detected', () => {
    const gestures: GestureType[] = [];
    const { result } = renderHook(() =>
      useGestureDetector({
        onGestureDetected: (e) => gestures.push(e.gesture),
        okThreshold: 3,
        palmThreshold: 2,
      }),
    );

    // Some oscillation frames — fewer than min required (10) so no wave triggers yet
    for (let i = 0; i < 8; i++) {
      result.current.processLandmarks(
        makeWristLandmarks(i % 2 === 0 ? 0.25 : 0.55),
      );
    }

    // Now send OK gesture repeatedly to fill the wave buffer with stationary values
    // and also clear any accumulated wave state
    for (let i = 0; i < 12; i++) {
      result.current.processLandmarks(makeOKLandmarks());
    }

    // Continue with stationary none-gesture wrist - should NOT trigger wave
    // because buffer was cleared by the OK gesture and refilled with stationary data
    for (let i = 0; i < 10; i++) {
      result.current.processLandmarks(makeWristLandmarks(0.4));
    }

    // Wave should not have been triggered during the post-OK stationary phase
    const waveCount = gestures.filter((g) => g === 'wave').length;
    // The key assertion: after OK clears the buffer, stationary data shouldn't trigger wave
    expect(waveCount).toBe(0);
  });

  it('wave detection does not interfere with existing OK detection', () => {
    const gestures: GestureType[] = [];
    const { result } = renderHook(() =>
      useGestureDetector({
        onGestureDetected: (e) => gestures.push(e.gesture),
        okThreshold: 3,
        palmThreshold: 2,
      }),
    );

    // Send enough OK frames to trigger
    for (let i = 0; i < 3; i++) {
      result.current.processLandmarks(makeOKLandmarks());
    }

    expect(gestures).toContain('ok');
    // No false wave during OK detection
    expect(gestures).not.toContain('wave');
  });

  it('wave detection does not interfere with existing open_palm detection', () => {
    const gestures: GestureType[] = [];
    const { result } = renderHook(() =>
      useGestureDetector({
        onGestureDetected: (e) => gestures.push(e.gesture),
        okThreshold: 3,
        palmThreshold: 2,
      }),
    );

    // Send enough palm frames to trigger
    for (let i = 0; i < 2; i++) {
      result.current.processLandmarks(makePalmLandmarks());
    }

    expect(gestures).toContain('open_palm');
    expect(gestures).not.toContain('wave');
  });
});
