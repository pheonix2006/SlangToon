import type { AppState } from '../../types';
import { GESTURE_MAP } from '../../constants/gestureMap';

const GESTURE_EMOJI: Record<string, string> = {
  ok: '👌',
  open_palm: '🖐️',
  wave: '👋',
};

interface GestureHintProps {
  appState: AppState;
}

export default function GestureHint({ appState }: GestureHintProps) {
  const actions = GESTURE_MAP[appState];
  if (!actions || actions.length === 0 || actions.every(a => !a.label)) return null;

  return (
    <div
      className="fixed bottom-8 left-0 right-0 z-40 flex justify-center gap-6 pointer-events-none"
    >
      {actions
        .filter(a => a.label)
        .map(a => (
          <span
            key={a.action}
            className="text-xs tracking-wider font-display"
            style={{ color: 'rgba(255,183,77,0.4)' }}
          >
            {GESTURE_EMOJI[a.gesture] ?? ''} {a.label}
          </span>
        ))}
    </div>
  );
}
