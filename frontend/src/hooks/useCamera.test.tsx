import { render, act, screen } from '@testing-library/react';
import { useCamera } from './useCamera';

function TestComponent({ onReady }: { onReady?: (api: ReturnType<typeof useCamera>) => void }) {
  const api = useCamera();
  return (
    <div>
      <video ref={api.videoRef} data-testid="video" />
      <span data-testid="isReady">{String(api.isReady)}</span>
      <span data-testid="error">{api.error ?? ''}</span>
      {onReady && onReady(api)}
    </div>
  );
}

describe('useCamera', () => {
  const mockStop = vi.fn();
  const mockStream = {
    getTracks: () => [{ stop: mockStop }],
  };

  beforeEach(() => {
    mockStop.mockClear();
    vi.spyOn(navigator.mediaDevices, 'getUserMedia').mockResolvedValue(
      mockStream as unknown as MediaStream,
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('calls getUserMedia on mount with correct constraints', async () => {
    render(<TestComponent />);

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
      video: {
        facingMode: 'user',
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });
    expect(screen.getByTestId('isReady').textContent).toBe('true');
    expect(screen.getByTestId('error').textContent).toBe('');
  });

  it('handles NotAllowedError', async () => {
    vi.spyOn(navigator.mediaDevices, 'getUserMedia').mockRejectedValue(
      new DOMException('Permission denied', 'NotAllowedError'),
    );

    render(<TestComponent />);

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(screen.getByTestId('error').textContent).toBe('请允许摄像头访问权限');
    expect(screen.getByTestId('isReady').textContent).toBe('false');
  });

  it('handles NotFoundError', async () => {
    vi.spyOn(navigator.mediaDevices, 'getUserMedia').mockRejectedValue(
      new DOMException('No device', 'NotFoundError'),
    );

    render(<TestComponent />);

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(screen.getByTestId('error').textContent).toBe('未检测到摄像头设备');
  });

  it('restart calls getUserMedia again', async () => {
    let api: ReturnType<typeof useCamera> | null = null;

    function RestartComponent() {
      api = useCamera();
      return (
        <div>
          <video ref={api.videoRef} data-testid="video" />
        </div>
      );
    }

    render(<RestartComponent />);

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    const callsBeforeRestart = vi.mocked(navigator.mediaDevices.getUserMedia).mock.calls.length;

    await act(() => {
      api!.restart();
    });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    const callsAfterRestart = vi.mocked(navigator.mediaDevices.getUserMedia).mock.calls.length;
    expect(callsAfterRestart).toBeGreaterThan(callsBeforeRestart);
  });

  it('cleanup stops tracks on unmount', async () => {
    const { unmount } = render(<TestComponent />);

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    unmount();

    expect(mockStop).toHaveBeenCalled();
  });
});
