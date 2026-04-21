import { useRef, useCallback, useState } from 'react';
import type { GestureType } from '../types';
import type { NormalizedLandmark } from '../utils/gestureAlgo';
import { detectGesture, createWaveBuffer, detectWave } from '../utils/gestureAlgo';

const DEFAULT_DEBOUNCE_MS = 500;
const MIN_CONFIDENCE = 0.5;
const WAVE_BUFFER_SIZE = 10;
const WAVE_THRESHOLD = 0.12;
const WAVE_COOLDOWN_FRAMES = 30;

interface UseGestureDetectorOptions {
  debounceMs?: number;
  onWaveDetected?: () => void;
}

interface UseGestureDetectorReturn {
  processLandmarks: (landmarks: NormalizedLandmark[]) => void;
  currentGesture: GestureType;
  currentConfidence: number;
}

export function useGestureDetector(
  options: UseGestureDetectorOptions = {},
): UseGestureDetectorReturn {
  const { debounceMs = DEFAULT_DEBOUNCE_MS, onWaveDetected } = options;

  const [currentGesture, setCurrentGesture] = useState<GestureType>('none');
  const [currentConfidence, setCurrentConfidence] = useState(0);

  const pendingGestureRef = useRef<GestureType>('none');
  const pendingStartRef = useRef<number | null>(null);
  const confirmedGestureRef = useRef<GestureType>('none');
  const noneStartRef = useRef<number | null>(null);
  const waveBufferRef = useRef(createWaveBuffer(WAVE_BUFFER_SIZE));
  const waveCooldownRef = useRef(0);

  const processLandmarks = useCallback(
    (landmarks: NormalizedLandmark[]) => {
      if (landmarks.length > 0) {
        waveBufferRef.current.push(landmarks[0].x);
      }

      const result = detectGesture(landmarks);
      let gesture = result.gesture;
      const confidence = result.confidence;

      if (waveCooldownRef.current > 0) waveCooldownRef.current -= 1;

      if (waveCooldownRef.current <= 0 && detectWave(waveBufferRef.current, WAVE_THRESHOLD)) {
        onWaveDetected?.();
        waveBufferRef.current.clear();
        waveCooldownRef.current = WAVE_COOLDOWN_FRAMES;
      }

      if (gesture !== 'none' && confidence < MIN_CONFIDENCE) {
        gesture = 'none';
      }

      const now = Date.now();

      if (gesture === 'none') {
        pendingGestureRef.current = 'none';
        pendingStartRef.current = null;

        if (noneStartRef.current === null) {
          noneStartRef.current = now;
        }

        if (confirmedGestureRef.current !== 'none' && now - noneStartRef.current >= debounceMs) {
          confirmedGestureRef.current = 'none';
          setCurrentGesture('none');
          setCurrentConfidence(0);
        }
        return;
      }

      noneStartRef.current = null;

      if (gesture === pendingGestureRef.current) {
        const elapsed = now - (pendingStartRef.current ?? now);
        if (elapsed >= debounceMs && confirmedGestureRef.current !== gesture) {
          confirmedGestureRef.current = gesture;
          setCurrentGesture(gesture);
          setCurrentConfidence(confidence);
        }
      } else {
        pendingGestureRef.current = gesture;
        pendingStartRef.current = now;
        if (confirmedGestureRef.current !== 'none') {
          confirmedGestureRef.current = 'none';
          setCurrentGesture('none');
          setCurrentConfidence(0);
        }
      }
    },
    [debounceMs, onWaveDetected],
  );

  return { processLandmarks, currentGesture, currentConfidence };
}
