/** 最长边像素上限，足够 Vision LLM 分析，大幅降低传输体积 */
const MAX_IMAGE_DIMENSION = 1280;

/**
 * Captures the current video frame, downscales if needed, and returns it as a JPEG base64 string.
 * @param videoElement - The HTML video element to capture from
 * @returns Base64 encoded JPEG string (without the data URL prefix)
 */
export function captureFrame(videoElement: HTMLVideoElement): string {
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');

  if (!ctx) {
    throw new Error('无法创建 Canvas 2D 上下文');
  }

  let { videoWidth: w, videoHeight: h } = videoElement;

  // Downscale when longest edge exceeds MAX_IMAGE_DIMENSION
  if (Math.max(w, h) > MAX_IMAGE_DIMENSION) {
    const scale = MAX_IMAGE_DIMENSION / Math.max(w, h);
    w = Math.round(w * scale);
    h = Math.round(h * scale);
  }

  canvas.width = w;
  canvas.height = h;
  ctx.drawImage(videoElement, 0, 0, w, h);

  const dataUrl = canvas.toDataURL('image/jpeg', 0.85);

  // Strip the "data:image/jpeg;base64," prefix
  const base64 = dataUrl.replace(/^data:image\/jpeg;base64,/, '');

  // Clean up
  canvas.width = 0;
  canvas.height = 0;

  return base64;
}
