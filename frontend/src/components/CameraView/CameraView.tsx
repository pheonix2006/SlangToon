interface CameraViewProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  className?: string;
}

export default function CameraView({
  videoRef,
  canvasRef,
  className = '',
}: CameraViewProps) {
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ transform: 'scaleX(-1)' }}
        className="w-full h-full object-cover"
      />

      {/* Canvas overlay for hand landmarks */}
      <canvas
        ref={canvasRef}
        style={{ transform: 'scaleX(-1)' }}
        className="absolute top-0 left-0 w-full h-full pointer-events-none"
      />
    </div>
  );
}
