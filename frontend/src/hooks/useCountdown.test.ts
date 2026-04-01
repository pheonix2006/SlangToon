import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCountdown } from './useCountdown';

describe('useCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('initializes with default seconds (3)', () => {
    const { result } = renderHook(() => useCountdown());
    expect(result.current.remaining).toBe(3);
  });

  it('counts down each second when active', () => {
    const { result } = renderHook(() => useCountdown({ active: true }));

    expect(result.current.remaining).toBe(3);

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.remaining).toBe(2);

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.remaining).toBe(1);
  });

  it('calls onComplete when reaching 0', () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() =>
      useCountdown({ seconds: 2, onComplete, active: true })
    );

    expect(result.current.remaining).toBe(2);

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(result.current.remaining).toBe(0);
    expect(onComplete).toHaveBeenCalled();
  });

  it('does not decrement when inactive', () => {
    const { result } = renderHook(() =>
      useCountdown({ active: false })
    );

    expect(result.current.remaining).toBe(3);

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.remaining).toBe(3);
  });

  it('reset restores countdown', () => {
    const { result } = renderHook(() =>
      useCountdown({ seconds: 3, active: true })
    );

    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(result.current.remaining).toBe(1);

    act(() => {
      result.current.reset();
    });
    expect(result.current.remaining).toBe(3);
  });
});
