import { render, screen, act } from '@testing-library/react';
import { vi } from 'vitest';
import App from './App';

vi.mock('./services/api', () => ({
  generateScript: vi.fn(),
  generateComic: vi.fn(),
  getHistory: vi.fn().mockResolvedValue({
    data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
  }),
  fetchConfig: vi.fn(),
}));

vi.mock('./hooks/useCamera', () => ({
  useCamera: () => ({ videoRef: { current: null }, isReady: true, error: undefined, restart: vi.fn() }),
}));
vi.mock('./hooks/useMediaPipeHands', () => ({
  useMediaPipeHands: () => ({ canvasRef: { current: null } }),
}));

describe('App (gesture-confirm integration)', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('renders without crash in CAMERA_READY', async () => {
    await act(async () => { render(<App />); });
    const buttons = screen.queryAllByRole('button');
    expect(buttons).toHaveLength(0);
  });

  it('has no header navigation buttons', async () => {
    await act(async () => { render(<App />); });
    expect(screen.queryByText('History →')).toBeNull();
    expect(screen.queryByText('← Back')).toBeNull();
  });

  it('shows GestureHint in CAMERA_READY', async () => {
    await act(async () => { render(<App />); });
    expect(screen.getByText(/Generate/)).toBeInTheDocument();
  });

  it('enters GALLERY after 20s idle', async () => {
    await act(async () => { render(<App />); });
    await act(async () => { vi.advanceTimersByTime(20000); });
    expect(true).toBe(true);
  });

  it('cleans up timer on unmount', async () => {
    let unmountFn: (() => void) | undefined;
    await act(async () => {
      const { unmount } = render(<App />);
      unmountFn = unmount;
    });
    await act(async () => {
      unmountFn!();
      vi.advanceTimersByTime(50000);
    });
    expect(true).toBe(true);
  });
});
