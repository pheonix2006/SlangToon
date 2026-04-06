import { useRef, useCallback } from 'react';
import type { GestureType } from '../types';
import type { NormalizedLandmark } from '../utils/gestureAlgo';
import { detectGesture, createWaveBuffer, detectWave } from '../utils/gestureAlgo';

interface GestureDetectedEvent {
  gesture: GestureType;
  confidence: number;
  detectedAt: Date;
}

interface UseGestureDetectorOptions {
  onGestureDetected: (event: GestureDetectedEvent) => void;
  // Number of consecutive frames needed to confirm a gesture
  okThreshold?: number;
  palmThreshold?: number;
}

interface UseGestureDetectorReturn {
  processLandmarks: (landmarks: NormalizedLandmark[]) => void;
}

// Consecutive frame counts needed to confirm each gesture type
const DEFAULT_OK_THRESHOLD = 8;
const DEFAULT_PALM_THRESHOLD = 5;

// Wave detection parameters
const WAVE_BUFFER_SIZE = 15;       // ~0.5s at 30fps — faster response
const WAVE_THRESHOLD = 0.12;      // Lowered from 0.17 — easier to trigger
const WAVE_COOLDOWN_FRAMES = 45; // Prevent re-trigger for ~1.5s

export function useGestureDetector({
  onGestureDetected,
  okThreshold = DEFAULT_OK_THRESHOLD,
  palmThreshold = DEFAULT_PALM_THRESHOLD,
}: UseGestureDetectorOptions): UseGestureDetectorReturn {
  const counterRef = useRef<number>(0);
  const lastGestureRef = useRef<GestureType>('none');
  const waveBufferRef = useRef(createWaveBuffer(WAVE_BUFFER_SIZE));
  const waveCooldownRef = useRef(0);

  const processLandmarks = useCallback(
    (landmarks: NormalizedLandmark[]) => {
      // Push wrist x into wave buffer every frame for oscillation detection
      if (landmarks.length > 0) {
        waveBufferRef.current.push(landmarks[0].x);
      }

      const result = detectGesture(landmarks);
      const { gesture, confidence } = result;

      // Handle cooldown countdown to prevent rapid re-triggering
      if (waveCooldownRef.current > 0) {
        waveCooldownRef.current -= 1;
      }

      if (gesture === 'none') {
        // Reset when no gesture detected
        counterRef.current = 0;
        lastGestureRef.current = 'none';

        // Check for wave when no other gesture detected and cooldown expired
        if (
          waveCooldownRef.current <= 0 &&
          detectWave(waveBufferRef.current, WAVE_THRESHOLD)
        ) {
          onGestureDetected({
            gesture: 'wave',
            confidence: 0.7,
            detectedAt: new Date(),
          });
          waveBufferRef.current.clear();
          waveCooldownRef.current = WAVE_COOLDOWN_FRAMES;
        }
        return;
      }

      // Non-none gesture: clear wave buffer to prevent false positives
      waveBufferRef.current.clear();

      // Check if same gesture as last frame
      if (gesture === lastGestureRef.current) {
        counterRef.current += 1;

        // Determine threshold based on gesture type
        const threshold =
          gesture === 'ok' ? okThreshold : palmThreshold;

        if (counterRef.current >= threshold) {
          onGestureDetected({
            gesture,
            confidence,
            detectedAt: new Date(),
          });
          // Reset counter after triggering
          counterRef.current = 0;
        }
      } else {
        // Different gesture detected - reset counter and track new gesture
        counterRef.current = 1;
        lastGestureRef.current = gesture;
      }
    },
    [onGestureDetected, okThreshold, palmThreshold],
  );

  return { processLandmarks };
}
