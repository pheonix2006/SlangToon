import { useRef, useState, useEffect, useCallback } from 'react';

interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  isReady: boolean;
  error: string | null;
  restart: () => void;
}

async function startStream(
  videoElement: HTMLVideoElement,
): Promise<MediaStream> {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: 'user',
      width: { ideal: 1280 },
      height: { ideal: 720 },
    },
    audio: false,
  });

  videoElement.srcObject = stream;
  await videoElement.play();

  return stream;
}

export function useCamera(): UseCameraReturn {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const cleanup = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsReady(false);
  }, []);

  const start = useCallback(async () => {
    cleanup();
    setError(null);

    const video = videoRef.current;
    if (!video) return;

    try {
      const stream = await startStream(video);
      streamRef.current = stream;
      setIsReady(true);
    } catch (err) {
      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        setError('请允许摄像头访问权限');
      } else if (err instanceof DOMException && err.name === 'NotFoundError') {
        setError('未检测到摄像头设备');
      } else {
        setError('无法启动摄像头');
      }
      setIsReady(false);
    }
  }, [cleanup]);

  const restart = useCallback(() => {
    start();
  }, [start]);

  useEffect(() => {
    start();
    return () => {
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { videoRef, isReady, error, restart };
}
