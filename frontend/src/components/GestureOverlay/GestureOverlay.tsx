import type { GestureType } from '../../types';

interface GestureOverlayProps {
  gesture: GestureType;
  confidence?: number;
}

const GESTURE_LABELS: Record<GestureType, string> = {
  ok: 'OK 手势已识别',
  open_palm: '张开手掌已识别',
  none: '等待手势...',
};

export default function GestureOverlay({
  gesture,
  confidence,
}: GestureOverlayProps) {
  const isDetected = gesture !== 'none';

  return (
    <div
      className={`
        fixed bottom-6 left-1/2 -translate-x-1/2 z-50
        px-6 py-3 rounded-full
        backdrop-blur-md
        transition-all duration-300 ease-in-out
        ${
          isDetected
            ? 'bg-green-500/20 border border-green-400/50 shadow-[0_0_20px_rgba(34,197,94,0.3)]'
            : 'bg-gray-800/60 border border-gray-600/50'
        }
      `}
    >
      <div className="flex items-center gap-3">
        {/* Status indicator dot */}
        <div
          className={`
            w-2.5 h-2.5 rounded-full transition-colors duration-300
            ${isDetected ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}
          `}
        />

        {/* Gesture label */}
        <span
          className={`
            text-sm font-medium transition-colors duration-300
            ${isDetected ? 'text-green-300' : 'text-gray-400'}
          `}
        >
          {GESTURE_LABELS[gesture]}
        </span>

        {/* Confidence indicator */}
        {isDetected && confidence !== undefined && (
          <span className="text-xs text-green-400/70">
            {Math.round(confidence * 100)}%
          </span>
        )}
      </div>
    </div>
  );
}
