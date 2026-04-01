import { useRef, useCallback } from 'react';
import type { GestureType } from '../types';
import type { NormalizedLandmark } from '../utils/gestureAlgo';
import { detectGesture } from '../utils/gestureAlgo';

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

export function useGestureDetector({
  onGestureDetected,
  okThreshold = DEFAULT_OK_THRESHOLD,
  palmThreshold = DEFAULT_PALM_THRESHOLD,
}: UseGestureDetectorOptions): UseGestureDetectorReturn {
  const counterRef = useRef<number>(0);
  const lastGestureRef = useRef<GestureType>('none');

  const processLandmarks = useCallback(
    (landmarks: NormalizedLandmark[]) => {
      const result = detectGesture(landmarks);
      const { gesture, confidence } = result;

      if (gesture === 'none') {
        // Reset when no gesture detected
        counterRef.current = 0;
        lastGestureRef.current = 'none';
        return;
      }

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
