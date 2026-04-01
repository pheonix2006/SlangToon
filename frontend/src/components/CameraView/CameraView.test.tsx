import { render } from '@testing-library/react';
import { createRef } from 'react';
import CameraView from './CameraView';

describe('CameraView', () => {
  it('renders video element', () => {
    const videoRef = createRef<HTMLVideoElement>();
    const canvasRef = createRef<HTMLCanvasElement>();

    const { container } = render(<CameraView videoRef={videoRef} canvasRef={canvasRef} />);

    const video = container.querySelector('video');
    expect(video).toBeInTheDocument();
  });

  it('video has scaleX(-1) transform', () => {
    const videoRef = createRef<HTMLVideoElement>();
    const canvasRef = createRef<HTMLCanvasElement>();

    const { container } = render(<CameraView videoRef={videoRef} canvasRef={canvasRef} />);

    const video = container.querySelector('video');
    expect(video).toHaveStyle({ transform: 'scaleX(-1)' });
  });

  it('renders canvas overlay with pointer-events-none class', () => {
    const videoRef = createRef<HTMLVideoElement>();
    const canvasRef = createRef<HTMLCanvasElement>();

    render(<CameraView videoRef={videoRef} canvasRef={canvasRef} />);

    const canvas = document.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
    expect(canvas!.className).toContain('pointer-events-none');
  });
});
