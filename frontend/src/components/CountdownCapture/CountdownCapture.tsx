import { useState, useEffect, useCallback, useRef } from 'react';

interface CountdownCaptureProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onCapture: (base64: string) => void;
  duration?: number;
}

export default function CountdownCapture({
  videoRef,
  onCapture,
  duration = 3,
}: CountdownCaptureProps) {
  const [count, setCount] = useState(duration);
  const [flash, setFlash] = useState(false);
  const capturedRef = useRef(false);

  const captureFrame = useCallback(() => {
    const video = videoRef.current;
    if (!video || capturedRef.current) return;
    capturedRef.current = true;

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    const base64 = canvas.toDataURL('image/jpeg', 0.8);

    setFlash(true);
    setTimeout(() => onCapture(base64), 300);
  }, [videoRef, onCapture]);

  useEffect(() => {
    if (count <= 0) {
      captureFrame();
      return;
    }
    const timer = setTimeout(() => setCount(c => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [count, captureFrame]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {flash && (
        <div className="absolute inset-0 bg-white animate-flash z-50 pointer-events-none" />
      )}

      {count > 0 && (
        <div
          key={count}
          className="text-[200px] font-bold text-white drop-shadow-2xl animate-countdown select-none"
          style={{ textShadow: '0 0 60px rgba(255,255,255,0.5)' }}
        >
          {count}
        </div>
      )}

      {count <= 0 && !flash && (
        <div className="text-4xl text-white animate-pulse">📸</div>
      )}
    </div>
  );
}
