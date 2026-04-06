import type { GestureType } from '../types';

export interface GestureResult {
  gesture: GestureType;
  confidence: number;
}

export interface NormalizedLandmark {
  x: number;
  y: number;
  z: number;
}

// Hand landmark indices
const THUMB_TIP = 4;
const THUMB_IP = 3;
const INDEX_TIP = 8;
const INDEX_PIP = 6;
const INDEX_MCP = 5;
const MIDDLE_TIP = 12;
const MIDDLE_PIP = 10;
const RING_TIP = 16;
const RING_PIP = 14;
const PINKY_TIP = 20;
const PINKY_PIP = 18;

function distance(
  a: NormalizedLandmark,
  b: NormalizedLandmark,
): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  const dz = a.z - b.z;
  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

function isFingerExtended(
  landmarks: NormalizedLandmark[],
  tipIndex: number,
  pipIndex: number,
): boolean {
  return landmarks[tipIndex].y < landmarks[pipIndex].y;
}

export function detectGesture(
  landmarks: NormalizedLandmark[],
): GestureResult {
  if (!landmarks || landmarks.length < 21) {
    return { gesture: 'none', confidence: 0 };
  }

  // Check for OK sign: thumb tip close to index tip, other 3 fingers extended
  const thumbTipToIndexTip = distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]);
  const okThreshold = 0.06;

  const middleExtended = isFingerExtended(landmarks, MIDDLE_TIP, MIDDLE_PIP);
  const ringExtended = isFingerExtended(landmarks, RING_TIP, RING_PIP);
  const pinkyExtended = isFingerExtended(landmarks, PINKY_TIP, PINKY_PIP);

  if (
    thumbTipToIndexTip < okThreshold &&
    middleExtended &&
    ringExtended &&
    pinkyExtended
  ) {
    const confidence = Math.max(0, 1 - thumbTipToIndexTip / okThreshold);
    return { gesture: 'ok', confidence };
  }

  // Check for open palm: all 5 fingers extended
  const thumbExtended =
    distance(landmarks[THUMB_TIP], landmarks[INDEX_MCP]) >
    distance(landmarks[THUMB_IP], landmarks[INDEX_MCP]);

  const indexExtended = isFingerExtended(landmarks, INDEX_TIP, INDEX_PIP);

  if (
    thumbExtended &&
    indexExtended &&
    middleExtended &&
    ringExtended &&
    pinkyExtended
  ) {
    const fingerCount = [
      thumbExtended,
      indexExtended,
      middleExtended,
      ringExtended,
      pinkyExtended,
    ].filter(Boolean).length;
    const confidence = fingerCount / 5;
    return { gesture: 'open_palm', confidence };
  }

  return { gesture: 'none', confidence: 0 };
}

/** Ring buffer for storing wrist x-coordinates across frames for wave detection. */
export interface WaveBuffer {
  /** Push a new x-coordinate value. */
  push(x: number): void;
  /** Clear all stored values. */
  clear(): void;
  /** Number of values currently stored. */
  readonly size: number;
  /** Return values in chronological order (oldest first). */
  toArray(): number[];
}

/**
 * Create a ring buffer with fixed capacity for wave detection.
 * @param capacity Maximum number of frames to store (recommend 15-20).
 */
export function createWaveBuffer(capacity: number): WaveBuffer {
  const buf = new Array(capacity).fill(NaN);
  let wi = 0, count = 0;
  return {
    push(x) { buf[wi] = x; wi = (wi + 1) % capacity; if (count < capacity) count++; },
    clear() { buf.fill(NaN); wi = 0; count = 0; },
    get size() { return count; },
    toArray() {
      if (count < capacity) return buf.slice(0, count);
      const r = new Array(capacity);
      for (let i = 0; i < capacity; i++) r[i] = buf[(wi + i) % capacity];
      return r;
    },
  };
}

/**
 * Detect if the wrist has been waving based on x-coordinate oscillation.
 * Uses peak-to-peak amplitude detection on the buffer.
 *
 * @param buf WaveBuffer containing recent wrist x-coordinates
 * @param threshold Minimum peak-to-peak amplitude to qualify as a wave (recommend 0.15-0.20)
 * @returns true if waving detected, false otherwise
 */
export function detectWave(buf: WaveBuffer, threshold: number): boolean {
  const data = buf.toArray();
  if (data.length < 10) return false;
  let min = Infinity, max = -Infinity;
  for (const v of data) {
    if (!Number.isFinite(v)) continue;
    if (v < min) min = v;
    if (v > max) max = v;
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return false;
  return (max - min) >= threshold;
}
