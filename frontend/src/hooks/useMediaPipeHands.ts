import { useRef, useEffect, useCallback } from 'react';

// Hand landmark connection pairs
const HAND_CONNECTIONS: [number, number][] = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [0, 9], [9, 10], [10, 11], [11, 12],
  [0, 13], [13, 14], [14, 15], [15, 16],
  [0, 17], [17, 18], [18, 19], [19, 20],
  [5, 9], [9, 13], [13, 17],
];

export interface LandmarkPoint {
  x: number;
  y: number;
  z: number;
}

interface UseMediaPipeHandsOptions {
  onResults: (landmarks: LandmarkPoint[]) => void;
  videoRef?: React.RefObject<HTMLVideoElement | null>;
}

interface UseMediaPipeHandsReturn {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
}

function drawHandLandmarks(
  ctx: CanvasRenderingContext2D,
  landmarks: LandmarkPoint[],
  width: number,
  height: number,
) {
  ctx.clearRect(0, 0, width, height);

  // Draw connections (gold lines)
  ctx.strokeStyle = 'rgba(255, 183, 77, 0.4)';
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.shadowColor = 'transparent';
  ctx.shadowBlur = 0;

  for (const [start, end] of HAND_CONNECTIONS) {
    const from = landmarks[start];
    const to = landmarks[end];
    if (!from || !to) continue;

    ctx.beginPath();
    ctx.moveTo(from.x * width, from.y * height);
    ctx.lineTo(to.x * width, to.y * height);
    ctx.stroke();
  }

  // Draw landmark dots (gold with glow)
  ctx.shadowColor = 'rgba(255, 183, 77, 0.6)';
  ctx.shadowBlur = 12;
  ctx.fillStyle = '#FFB74D';
  for (const lm of landmarks) {
    ctx.beginPath();
    ctx.arc(lm.x * width, lm.y * height, 5, 0, 2 * Math.PI);
    ctx.fill();
  }

  // Reset shadow
  ctx.shadowColor = 'transparent';
  ctx.shadowBlur = 0;
}

export function useMediaPipeHands({
  onResults,
  videoRef,
}: UseMediaPipeHandsOptions): UseMediaPipeHandsReturn {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const handsRef = useRef<// eslint-disable-next-line @typescript-eslint/no-explicit-any
  Record<string, unknown> | null>(null);
  const animFrameRef = useRef<number>(0);

  const handleResults = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (results: any) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      canvas.width = results.image?.width || canvas.width;
      canvas.height = results.image?.height || canvas.height;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const multiHandLandmarks = results.multiHandLandmarks as
        | LandmarkPoint[][]
        | undefined;

      if (multiHandLandmarks && multiHandLandmarks.length > 0) {
        for (const landmarks of multiHandLandmarks) {
          drawHandLandmarks(ctx, landmarks, canvas.width, canvas.height);
        }
        // Pass the first detected hand's landmarks
        onResults(multiHandLandmarks[0]);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        onResults([]);
      }
    },
    [onResults],
  );

  useEffect(() => {
    let active = true;

    async function initHands() {
      try {
        const mpHands = await import('@mediapipe/hands');
        const Hands = mpHands.Hands;

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const hands: any = new Hands({
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          locateFile: (file: string) =>
            `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
        });

        hands.setOptions({
          maxNumHands: 1,
          modelComplexity: 1,
          minDetectionConfidence: 0.7,
          minTrackingConfidence: 0.7,
        });

        hands.onResults(handleResults);
        handsRef.current = hands;

        if (videoRef?.current) {
          const videoEl = videoRef.current;
          // Use requestAnimationFrame loop to send frames
          async function sendFrame() {
            if (!active) return;
            if (videoEl && videoEl.readyState >= 2 && handsRef.current) {
              try {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                await (handsRef.current as any).send({ image: videoEl });
              } catch {
                // Frame send may fail if camera not ready
              }
            }
            animFrameRef.current = requestAnimationFrame(sendFrame);
          }
          sendFrame();
        }
      } catch (err) {
        console.error('Failed to initialize MediaPipe Hands:', err);
      }
    }

    initHands();

    return () => {
      active = false;
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const h = handsRef.current as any;
      if (h && typeof h.close === 'function') {
        h.close();
      }
      handsRef.current = null;
    };
  }, [handleResults, videoRef]);

  return { canvasRef };
}
