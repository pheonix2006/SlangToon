import { describe, it, expect } from 'vitest';
import { detectGesture, type NormalizedLandmark } from './gestureAlgo';
import { createWaveBuffer, detectWave } from './gestureAlgo';

/**
 * Helper: create 21 NormalizedLandmark objects with sensible defaults.
 *
 * Default positions simulate a hand facing the camera:
 *  - Wrist (0) at origin
 *  - Finger bases along x-axis
 *  - Finger PIP joints at y=0.6
 *  - Finger TIP joints at y=0.9 (above PIP ⇒ extended)
 *
 * Pass an object like `{ 4: { x: 0.1, y: 0.2, z: 0 } }` to override
 * specific landmark indices.
 */
function makeLandmarks(
  overrides: Partial<Record<number, Partial<NormalizedLandmark>>> = {},
): NormalizedLandmark[] {
  // Base: hand at rest with fingers pointing upward (y decreasing = upward)
  const base: NormalizedLandmark = { x: 0.4, y: 0.6, z: 0 };

  // Fingertip default y is lower (0.3) than PIP default y (0.6),
  // so fingers are "extended" by default.
  const tipY = 0.3;
  const pipY = 0.6;

  const defaults: NormalizedLandmark[] = Array.from({ length: 21 }, () => ({
    ...base,
  }));

  // Set PIP joints (fingers curled if tip y >= pip y)
  defaults[5].y = pipY; // INDEX_MCP
  defaults[6].y = pipY; // INDEX_PIP
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

describe('detectGesture', () => {
  // ---------------------------------------------------------------
  // 1. Empty / null input
  // ---------------------------------------------------------------
  it('returns none with confidence 0 for empty array', () => {
    const result = detectGesture([]);
    expect(result).toEqual({ gesture: 'none', confidence: 0 });
  });

  // ---------------------------------------------------------------
  // 2. Fewer than 21 landmarks
  // ---------------------------------------------------------------
  it('returns none with confidence 0 when fewer than 21 landmarks', () => {
    const result = detectGesture(makeLandmarks().slice(0, 15));
    expect(result).toEqual({ gesture: 'none', confidence: 0 });
  });

  // ---------------------------------------------------------------
  // 3. All-zero landmarks
  // ---------------------------------------------------------------
  it('returns none with confidence 0 for all-zero landmarks', () => {
    const zeroes: NormalizedLandmark[] = Array.from({ length: 21 }, () => ({
      x: 0,
      y: 0,
      z: 0,
    }));
    const result = detectGesture(zeroes);
    expect(result.gesture).toBe('none');
    expect(result.confidence).toBe(0);
  });

  // ---------------------------------------------------------------
  // 4. OK gesture detected
  // ---------------------------------------------------------------
  it('detects OK gesture when thumb tip is close to index tip and other fingers extended', () => {
    const landmarks = makeLandmarks({
      // Thumb tip (4) very close to index tip (8)
      4: { x: 0.35, y: 0.3, z: 0 },
      8: { x: 0.35, y: 0.31, z: 0.001 },
    });
    const result = detectGesture(landmarks);
    expect(result.gesture).toBe('ok');
    expect(result.confidence).toBeGreaterThan(0);
  });

  // ---------------------------------------------------------------
  // 5. Open palm detected
  // ---------------------------------------------------------------
  it('detects open_palm when all 5 fingers are extended', () => {
    const landmarks = makeLandmarks({
      // Thumb tip further from INDEX_MCP than THUMB_IP is
      4: { x: 0.1, y: 0.3, z: 0 },
      3: { x: 0.3, y: 0.5, z: 0 }, // THUMB_IP closer to INDEX_MCP
    });
    const result = detectGesture(landmarks);
    expect(result.gesture).toBe('open_palm');
    expect(result.confidence).toBeGreaterThan(0);
  });

  // ---------------------------------------------------------------
  // 6. Curled fingers → none
  // ---------------------------------------------------------------
  it('returns none when all fingers are curled (tips below PIPs)', () => {
    const landmarks = makeLandmarks({
      // Set all finger tips to y > PIP (curled)
      4: { y: 0.8 },   // THUMB_TIP
      8: { y: 0.8 },   // INDEX_TIP
      12: { y: 0.8 },  // MIDDLE_TIP
      16: { y: 0.8 },  // RING_TIP
      20: { y: 0.8 },  // PINKY_TIP
    });
    const result = detectGesture(landmarks);
    expect(result).toEqual({ gesture: 'none', confidence: 0 });
  });

  // ---------------------------------------------------------------
  // 7. OK gesture confidence increases as thumb-to-index distance decreases
  // ---------------------------------------------------------------
  it('OK gesture confidence increases as thumb-index distance decreases', () => {
    // Far OK (closer to threshold 0.06)
    const far = makeLandmarks({
      4: { x: 0.35, y: 0.3, z: 0 },
      8: { x: 0.35, y: 0.34, z: 0 },
    });
    // Near OK (very close)
    const near = makeLandmarks({
      4: { x: 0.35, y: 0.3, z: 0 },
      8: { x: 0.35, y: 0.3001, z: 0 },
    });

    const farResult = detectGesture(far);
    const nearResult = detectGesture(near);

    expect(farResult.gesture).toBe('ok');
    expect(nearResult.gesture).toBe('ok');
    expect(nearResult.confidence).toBeGreaterThan(farResult.confidence);
  });

  // ---------------------------------------------------------------
  // 8. Only 3 fingers extended (middle, ring, pinky) but no OK or palm → none
  // ---------------------------------------------------------------
  it('returns none when only 3 fingers are extended without thumb-index proximity', () => {
    const landmarks = makeLandmarks({
      // Curl index so it is not extended
      8: { y: 0.8 },
      // Thumb tip far from index tip (not OK)
      4: { x: 0.1, y: 0.3, z: 0 },
      // Thumb not extended for palm (thumb tip closer to INDEX_MCP than THUMB_IP)
      3: { x: 0.1, y: 0.3, z: 0 },
    });
    const result = detectGesture(landmarks);
    // Middle, ring, pinky are still extended but index is not,
    // and thumb tip is not close to index tip → no OK.
    // Thumb is not extended for palm either.
    expect(result.gesture).toBe('none');
  });

  // ---------------------------------------------------------------
  // 9. Confidence always in [0, 1]
  // ---------------------------------------------------------------
  it('always returns confidence in [0, 1] range', () => {
    const scenarios = [
      [],
      makeLandmarks().slice(0, 10),
      makeLandmarks(),
      // OK gesture at threshold boundary
      makeLandmarks({
        4: { x: 0.35, y: 0.3, z: 0 },
        8: { x: 0.35, y: 0.3, z: 0 },
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
