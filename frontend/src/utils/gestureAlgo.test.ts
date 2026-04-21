import { describe, it, expect } from 'vitest';
import { detectGesture, type NormalizedLandmark } from './gestureAlgo';
import { createWaveBuffer, detectWave } from './gestureAlgo';

/**
 * Helper: create 21 NormalizedLandmark objects with sensible defaults.
 *
 * Default positions simulate a hand facing the camera with all fingers extended
 * (open palm). Pass overrides to customize specific landmarks.
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

  defaults[5].y = pipY; // INDEX_MCP
  defaults[6].y = pipY; // INDEX_PIP
  defaults[10].y = pipY; // MIDDLE_PIP
  defaults[14].y = pipY; // RING_PIP
  defaults[18].y = pipY; // PINKY_PIP

  defaults[4].y = tipY;  // THUMB_TIP
  defaults[3].y = 0.5;   // THUMB_IP
  defaults[8].y = tipY;  // INDEX_TIP
  defaults[12].y = tipY; // MIDDLE_TIP
  defaults[16].y = tipY; // RING_TIP
  defaults[20].y = tipY; // PINKY_TIP

  defaults[4].x = 0.2;   // THUMB_TIP far from INDEX_TIP
  defaults[8].x = 0.35;  // INDEX_TIP
  defaults[12].x = 0.45; // MIDDLE_TIP
  defaults[16].x = 0.55; // RING_TIP
  defaults[20].x = 0.65; // PINKY_TIP

  for (const [idx, override] of Object.entries(overrides)) {
    const i = Number(idx);
    if (i >= 0 && i < 21) {
      defaults[i] = { ...defaults[i], ...override };
    }
  }

  return defaults;
}

describe('detectGesture', () => {
  it('returns none with confidence 0 for empty array', () => {
    const result = detectGesture([]);
    expect(result).toEqual({ gesture: 'none', confidence: 0 });
  });

  it('returns none with confidence 0 when fewer than 21 landmarks', () => {
    const result = detectGesture(makeLandmarks().slice(0, 15));
    expect(result).toEqual({ gesture: 'none', confidence: 0 });
  });

  it('returns none with confidence 0 for all-zero landmarks', () => {
    const zeroes: NormalizedLandmark[] = Array.from({ length: 21 }, () => ({
      x: 0, y: 0, z: 0,
    }));
    const result = detectGesture(zeroes);
    expect(result.gesture).toBe('none');
    expect(result.confidence).toBe(0);
  });

  it('detects OK gesture when thumb+index form circle and other fingers extended', () => {
    const landmarks = makeLandmarks({
      // Thumb curled toward index MCP, close to index tip
      4: { x: 0.38, y: 0.62, z: 0 },  // THUMB_TIP curled
      8: { x: 0.39, y: 0.63, z: 0 },  // INDEX_TIP curled, close to thumb
      3: { x: 0.3, y: 0.5, z: 0 },    // THUMB_IP further from INDEX_MCP
    });
    const result = detectGesture(landmarks);
    expect(result.gesture).toBe('ok');
    expect(result.confidence).toBeGreaterThan(0);
  });

  it('does not detect OK when index is extended (palm-like)', () => {
    const landmarks = makeLandmarks({
      // Thumb and index tips close, but index is extended (y < pip.y)
      4: { x: 0.35, y: 0.3, z: 0 },
      8: { x: 0.35, y: 0.31, z: 0.001 },
    });
    const result = detectGesture(landmarks);
    expect(result.gesture).not.toBe('ok');
  });

  it('detects open_palm when all 5 fingers are extended', () => {
    const landmarks = makeLandmarks({
      4: { x: 0.1, y: 0.3, z: 0 },
      3: { x: 0.3, y: 0.5, z: 0 },
    });
    const result = detectGesture(landmarks);
    expect(result.gesture).toBe('open_palm');
    expect(result.confidence).toBeGreaterThan(0);
  });

  it('returns none when all fingers are curled (tips below PIPs)', () => {
    const landmarks = makeLandmarks({
      4: { y: 0.8 },
      8: { y: 0.8 },
      12: { y: 0.8 },
      16: { y: 0.8 },
      20: { y: 0.8 },
    });
    const result = detectGesture(landmarks);
    expect(result).toEqual({ gesture: 'none', confidence: 0 });
  });

  it('OK gesture confidence increases as thumb-index distance decreases', () => {
    const far = makeLandmarks({
      4: { x: 0.38, y: 0.62, z: 0 },
      8: { x: 0.38, y: 0.66, z: 0 },  // further from thumb
      3: { x: 0.3, y: 0.5, z: 0 },
    });
    const near = makeLandmarks({
      4: { x: 0.38, y: 0.62, z: 0 },
      8: { x: 0.38, y: 0.621, z: 0 }, // very close to thumb
      3: { x: 0.3, y: 0.5, z: 0 },
    });

    const farResult = detectGesture(far);
    const nearResult = detectGesture(near);

    expect(farResult.gesture).toBe('ok');
    expect(nearResult.gesture).toBe('ok');
    expect(nearResult.confidence).toBeGreaterThan(farResult.confidence);
  });

  it('returns none when only 3 fingers are extended without thumb-index proximity', () => {
    const landmarks = makeLandmarks({
      8: { y: 0.8 },
      4: { x: 0.1, y: 0.3, z: 0 },
      3: { x: 0.1, y: 0.3, z: 0 },
    });
    const result = detectGesture(landmarks);
    expect(result.gesture).toBe('none');
  });

  it('always returns confidence in [0, 1] range', () => {
    const scenarios = [
      [],
      makeLandmarks().slice(0, 10),
      makeLandmarks(),
      // OK gesture
      makeLandmarks({
        4: { x: 0.38, y: 0.62, z: 0 },
        8: { x: 0.39, y: 0.63, z: 0 },
        3: { x: 0.3, y: 0.5, z: 0 },
      }),
      // Open palm
      makeLandmarks({
        4: { x: 0.1, y: 0.3, z: 0 },
        3: { x: 0.3, y: 0.5, z: 0 },
      }),
    ];

    for (const landmarks of scenarios) {
      const result = detectGesture(landmarks);
      expect(result.confidence).toBeGreaterThanOrEqual(0);
      expect(result.confidence).toBeLessThanOrEqual(1);
    }
  });
});

describe('Wave detection', () => {
  const BUF = 10;

  it('returns false when buffer not full', () => {
    const buf = createWaveBuffer(BUF);
    for (let i = 0; i < BUF - 1; i++) { buf.push(0.5); }
    expect(detectWave(buf, 0.12)).toBe(false);
  });

  it('detects oscillation above threshold', () => {
    const buf = createWaveBuffer(BUF);
    for (let i = 0; i < BUF; i++) { buf.push(i % 2 === 0 ? 0.3 : 0.55); }
    expect(detectWave(buf, 0.12)).toBe(true);
  });

  it('returns false for stationary wrist', () => {
    const buf = createWaveBuffer(BUF);
    for (let i = 0; i < BUF; i++) { buf.push(0.45); }
    expect(detectWave(buf, 0.12)).toBe(false);
  });

  it('returns false below threshold', () => {
    const buf = createWaveBuffer(BUF);
    for (let i = 0; i < BUF; i++) { buf.push(i % 2 === 0 ? 0.44 : 0.50); }
    expect(detectWave(buf, 0.12)).toBe(false);
  });

  it('handles circular buffer overflow', () => {
    const buf = createWaveBuffer(BUF);
    for (let i = 0; i < BUF * 2; i++) { buf.push(i % 2 === 0 ? 0.3 : 0.55); }
    expect(detectWave(buf, 0.12)).toBe(true);
  });

  it('resets after clear()', () => {
    const buf = createWaveBuffer(BUF);
    for (let i = 0; i < BUF; i++) { buf.push(i % 2 === 0 ? 0.3 : 0.55); }
    expect(detectWave(buf, 0.12)).toBe(true);
    buf.clear();
    expect(detectWave(buf, 0.12)).toBe(false);
  });
});
