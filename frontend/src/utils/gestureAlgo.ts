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
