import { useState, useEffect, useRef, useCallback } from 'react';
import { COUNTDOWN_SECONDS } from '../constants';

interface UseCountdownOptions {
  seconds?: number;
  onComplete?: () => void;
  active?: boolean;
}

interface UseCountdownReturn {
  remaining: number;
  reset: () => void;
}

export function useCountdown({
  seconds = COUNTDOWN_SECONDS,
  onComplete,
  active = false,
}: UseCountdownOptions = {}): UseCountdownReturn {
  const [remaining, setRemaining] = useState(seconds);
  const onCompleteRef = useRef(onComplete);

  // Keep onComplete ref up to date
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const reset = useCallback(() => {
    setRemaining(seconds);
  }, [seconds]);

  useEffect(() => {
    if (!active) {
      return;
    }

    if (remaining <= 0) {
      onCompleteRef.current?.();
      return;
    }

    const timer = setInterval(() => {
      setRemaining((prev) => {
        const next = prev - 1;
        return next;
      });
    }, 1000);

    return () => {
      clearInterval(timer);
    };
  }, [active, remaining]);

  // Fire onComplete when remaining reaches 0
  useEffect(() => {
    if (active && remaining === 0) {
      onCompleteRef.current?.();
    }
  }, [active, remaining]);

  return { remaining, reset };
}
