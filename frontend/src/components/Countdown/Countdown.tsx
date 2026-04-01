interface CountdownProps {
  remaining: number;
}

export default function Countdown({ remaining }: CountdownProps) {
  if (remaining <= 0) {
    return null;
  }

  return (
    <div className="absolute inset-0 flex items-center justify-center z-40 pointer-events-none">
      <div className="relative">
        {/* Pulse ring animation */}
        <div
          className="absolute inset-0 rounded-full bg-white/20 animate-ping"
          style={{
            animationDuration: '1s',
            animationIterationCount: '1',
          }}
        />

        {/* Main number */}
        <div
          className="
            relative w-28 h-28 flex items-center justify-center
            rounded-full bg-black/50 backdrop-blur-sm
            border-2 border-white/30
            animate-pulse
          "
        >
          <span className="text-7xl font-bold text-white drop-shadow-lg">
            {remaining}
          </span>
        </div>
      </div>
    </div>
  );
}
