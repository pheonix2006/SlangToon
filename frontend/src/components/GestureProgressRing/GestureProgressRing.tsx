import type { GestureType } from '../../types';

interface GestureProgressRingProps {
  gesture: GestureType | null;
  progress: number;
  label: string;
}

const GESTURE_EMOJI: Record<string, string> = {
  ok: '👌',
  open_palm: '🖐️',
};

const RADIUS = 52;
const STROKE = 6;
const SIZE = (RADIUS + STROKE) * 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function GestureProgressRing({ gesture, progress, label }: GestureProgressRingProps) {
  if (!gesture) return null;

  const offset = CIRCUMFERENCE * (1 - progress);
  const isComplete = progress >= 1;

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center pointer-events-none transition-transform duration-200 ${
        isComplete ? 'scale-110' : 'scale-100'
      }`}
    >
      <div className="flex flex-col items-center gap-3">
        <div className="relative" style={{ width: SIZE, height: SIZE }}>
          <svg width={SIZE} height={SIZE} className="-rotate-90">
            <circle
              cx={RADIUS + STROKE}
              cy={RADIUS + STROKE}
              r={RADIUS}
              fill="none"
              stroke="rgba(255,183,77,0.15)"
              strokeWidth={STROKE}
            />
            <circle
              cx={RADIUS + STROKE}
              cy={RADIUS + STROKE}
              r={RADIUS}
              fill="none"
              stroke="rgba(255,183,77,0.8)"
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              style={{ strokeDashoffset: `${offset}`, transition: 'stroke-dashoffset 80ms linear' }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center text-4xl">
            <span>{GESTURE_EMOJI[gesture] ?? ''}</span>
          </div>
        </div>
        {label && (
          <span
            className="text-xs tracking-widest font-display"
            style={{ color: 'rgba(255,183,77,0.7)' }}
          >
            {label}
          </span>
        )}
      </div>
    </div>
  );
}
