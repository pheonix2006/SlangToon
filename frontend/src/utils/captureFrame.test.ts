import { captureFrame } from './captureFrame';

describe('captureFrame', () => {
  let videoElement: HTMLVideoElement;
  let mockCtx: CanvasRenderingContext2D;
  let getContextSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    videoElement = document.createElement('video');

    // videoWidth / videoHeight are read-only getters in jsdom; override with defineProperty
    Object.defineProperty(videoElement, 'videoWidth', { value: 640, configurable: true });
    Object.defineProperty(videoElement, 'videoHeight', { value: 480, configurable: true });

    mockCtx = {
      drawImage: vi.fn(),
    } as unknown as CanvasRenderingContext2D;

    getContextSpy = vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(mockCtx);
  });

  afterEach(() => {
    getContextSpy.mockRestore();
  });

  it('sets canvas dimensions from video (videoWidth=640, videoHeight=480)', () => {
    const widthSpy = vi.spyOn(HTMLCanvasElement.prototype, 'width', 'set');
    const heightSpy = vi.spyOn(HTMLCanvasElement.prototype, 'height', 'set');

    vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue(
      'data:image/jpeg;base64,abc123',
    );

    captureFrame(videoElement);

    // width is set to 640 first (capture), then 0 (cleanup)
    expect(widthSpy).toHaveBeenNthCalledWith(1, 640);
    expect(heightSpy).toHaveBeenNthCalledWith(1, 480);

    widthSpy.mockRestore();
    heightSpy.mockRestore();
  });

  it('calls drawImage with video element and correct dimensions', () => {
    vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue(
      'data:image/jpeg;base64,abc123',
    );

    captureFrame(videoElement);

    expect(mockCtx.drawImage).toHaveBeenCalledWith(videoElement, 0, 0, 640, 480);
  });

  it('calls toDataURL with image/jpeg and quality 0.85', () => {
    const toDataURLSpy = vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue(
      'data:image/jpeg;base64,abc123',
    );

    captureFrame(videoElement);

    expect(toDataURLSpy).toHaveBeenCalledWith('image/jpeg', 0.85);

    toDataURLSpy.mockRestore();
  });

  it('returns base64 without data: prefix', () => {
    vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue(
      'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD',
    );

    const result = captureFrame(videoElement);

    expect(result).toBe('/9j/4AAQSkZJRgABAQAAAQABAAD');
    expect(result).not.toMatch(/^data:image/);
  });

  it('cleans up canvas dimensions after capture (width=0, height=0)', () => {
    const widthSpy = vi.spyOn(HTMLCanvasElement.prototype, 'width', 'set');
    const heightSpy = vi.spyOn(HTMLCanvasElement.prototype, 'height', 'set');

    vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue(
      'data:image/jpeg;base64,abc123',
    );

    captureFrame(videoElement);

    // Second call sets dimensions to 0 for cleanup
    expect(widthSpy).toHaveBeenNthCalledWith(2, 0);
    expect(heightSpy).toHaveBeenNthCalledWith(2, 0);

    widthSpy.mockRestore();
    heightSpy.mockRestore();
  });
});
