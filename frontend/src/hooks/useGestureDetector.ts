import { useRef, useCallback, useState } from 'react';
import type { GestureType } from '../types';
import type { NormalizedLandmark } from '../utils/gestureAlgo';
import { detectGesture, createWaveBuffer, detectWave } from '../utils/gestureAlgo';

const DEFAULT_DEBOUNCE_FRAMES = 3;
const WAVE_BUFFER_SIZE = 15;
const WAVE_THRESHOLD = 0.12;
const WAVE_COOLDOWN_FRAMES = 45;

interface UseGestureDetectorOptions {
  debounceFrames?: number;
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
  const { debounceFrames = DEFAULT_DEBOUNCE_FRAMES, onWaveDetected } = options;

  const [currentGesture, setCurrentGesture] = useState<GestureType>('none');
  const [currentConfidence, setCurrentConfidence] = useState(0);

  const counterRef = useRef(0);
  const pendingGestureRef = useRef<GestureType>('none');
  const confirmedGestureRef = useRef<GestureType>('none');
  const waveBufferRef = useRef(createWaveBuffer(WAVE_BUFFER_SIZE));
  const waveCooldownRef = useRef(0);

  const processLandmarks = useCallback(
    (landmarks: NormalizedLandmark[]) => {
      if (landmarks.length > 0) {
        waveBufferRef.current.push(landmarks[0].x);
      }

      const result = detectGesture(landmarks);
      const { gesture, confidence } = result;

      if (waveCooldownRef.current > 0) waveCooldownRef.current -= 1;

      if (gesture === 'none') {
        if (pendingGestureRef.current === 'none') {
          counterRef.current += 1;
        } else {
          pendingGestureRef.current = 'none';
          counterRef.current = 1;
        }

        if (counterRef.current >= debounceFrames && confirmedGestureRef.current !== 'none') {
          confirmedGestureRef.current = 'none';
          setCurrentGesture('none');
          setCurrentConfidence(0);
        }

        if (waveCooldownRef.current <= 0 && detectWave(waveBufferRef.current, WAVE_THRESHOLD)) {
          onWaveDetected?.();
          waveBufferRef.current.clear();
          waveCooldownRef.current = WAVE_COOLDOWN_FRAMES;
        }
        return;
      }

      waveBufferRef.current.clear();

      if (gesture === pendingGestureRef.current) {
        counterRef.current += 1;
        if (counterRef.current >= debounceFrames && confirmedGestureRef.current !== gesture) {
          confirmedGestureRef.current = gesture;
          setCurrentGesture(gesture);
          setCurrentConfidence(confidence);
        }
      } else {
        pendingGestureRef.current = gesture;
        counterRef.current = 1;
        if (confirmedGestureRef.current !== 'none') {
          confirmedGestureRef.current = 'none';
          setCurrentGesture('none');
          setCurrentConfidence(0);
        }
      }
    },
    [debounceFrames, onWaveDetected],
  );

  return { processLandmarks, currentGesture, currentConfidence };
}
