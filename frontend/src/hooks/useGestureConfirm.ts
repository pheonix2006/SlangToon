import { useRef, useState, useCallback, useEffect } from 'react';
import type { AppState, GestureType, GestureAction } from '../types';
import { GESTURE_MAP } from '../constants/gestureMap';

const COOLDOWN_MS = 1000;
const TICK_INTERVAL_MS = 50;
const GRACE_MS = 300;

interface UseGestureConfirmOptions {
  appState: AppState;
  onConfirmed: (action: string) => void;
}

interface UseGestureConfirmReturn {
  activeGesture: GestureType | null;
  progress: number;
  label: string;
  feedGesture: (gesture: GestureType) => void;
}

export function useGestureConfirm({
  appState,
  onConfirmed,
}: UseGestureConfirmOptions): UseGestureConfirmReturn {
  const [activeGesture, setActiveGesture] = useState<GestureType | null>(null);
  const [progress, setProgress] = useState(0);
  const [label, setLabel] = useState('');

  const startTimeRef = useRef<number | null>(null);
  const matchedActionRef = useRef<GestureAction | null>(null);
  const cooldownUntilRef = useRef(0);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const graceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTick = useCallback(() => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
  }, []);

  const clearGrace = useCallback(() => {
    if (graceTimerRef.current) {
      clearTimeout(graceTimerRef.current);
      graceTimerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    clearTick();
    clearGrace();
    startTimeRef.current = null;
    matchedActionRef.current = null;
    setActiveGesture(null);
    setProgress(0);
    setLabel('');
  }, [clearTick, clearGrace]);

  useEffect(() => { reset(); }, [appState, reset]);
  useEffect(() => () => { clearTick(); clearGrace(); }, [clearTick, clearGrace]);

  const feedGesture = useCallback(
    (gesture: GestureType) => {
      const now = Date.now();

      if (now < cooldownUntilRef.current) {
        if (matchedActionRef.current) reset();
        return;
      }

      const actions = GESTURE_MAP[appState];
      const matched = actions.find(a => a.gesture === gesture) ?? null;

      if (!matched || gesture === 'none') {
        if (matchedActionRef.current) {
          if (!graceTimerRef.current) {
            graceTimerRef.current = setTimeout(() => {
              graceTimerRef.current = null;
              reset();
            }, GRACE_MS);
          }
        }
        return;
      }

      clearGrace();

      if (matched.holdMs === 0) {
        cooldownUntilRef.current = now + COOLDOWN_MS;
        onConfirmed(matched.action);
        reset();
        return;
      }

      if (matchedActionRef.current?.action === matched.action) {
        return;
      }

      clearTick();
      matchedActionRef.current = matched;
      startTimeRef.current = now;
      setActiveGesture(gesture);
      setLabel(matched.label);
      setProgress(0);

      tickRef.current = setInterval(() => {
        const elapsed = Date.now() - (startTimeRef.current ?? now);
        const p = Math.min(elapsed / matched.holdMs, 1);
        setProgress(p);

        if (p >= 1) {
          clearTick();
          clearGrace();
          cooldownUntilRef.current = Date.now() + COOLDOWN_MS;
          onConfirmed(matched.action);
          startTimeRef.current = null;
          matchedActionRef.current = null;
          setActiveGesture(null);
          setProgress(0);
          setLabel('');
        }
      }, TICK_INTERVAL_MS);
    },
    [appState, onConfirmed, reset, clearTick, clearGrace],
  );

  return { activeGesture, progress, label, feedGesture };
}
