import { useState, useCallback, useRef, useEffect } from 'react';
import { AppState } from './types';
import type { GestureType, StyleOption, HistoryItem } from './types';
import { useCamera } from './hooks/useCamera';
import { useGestureDetector } from './hooks/useGestureDetector';
import { useMediaPipeHands } from './hooks/useMediaPipeHands';
import { useCountdown } from './hooks/useCountdown';
import { analyzePhoto, generatePoster, getHistory } from './services/api';
import { captureFrame } from './utils/captureFrame';
import CameraView from './components/CameraView/CameraView';
import GestureOverlay from './components/GestureOverlay/GestureOverlay';
import Countdown from './components/Countdown/Countdown';
import StyleSelection from './components/StyleSelection/StyleSelection';
import PosterDisplay from './components/PosterDisplay/PosterDisplay';
import HistoryList from './components/HistoryList/HistoryList';
import ErrorDisplay from './components/ErrorDisplay';

function App() {
  // ── State machine ──────────────────────────────────────────
  const [appState, setAppState] = useState<AppState>(AppState.CAMERA_READY);
  const [photo, setPhoto] = useState<string>('');
  const [styleOptions, setStyleOptions] = useState<StyleOption[]>([]);
  const [selectedOption, setSelectedOption] = useState<StyleOption | null>(null);
  const [posterUrl, setPosterUrl] = useState<string>('');
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [gesture, setGesture] = useState<GestureType>('none');
  const [gestureConfidence, setGestureConfidence] = useState<number>(0);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Ref to keep latest appState accessible in callbacks without re-subscribing
  const appStateRef = useRef<AppState>(appState);
  useEffect(() => {
    appStateRef.current = appState;
  }, [appState]);

  // ── Navigation helpers ─────────────────────────────────────
  const goHome = useCallback(() => {
    setPhoto('');
    setStyleOptions([]);
    setSelectedOption(null);
    setPosterUrl('');
    setAppState(AppState.CAMERA_READY);
    // Note: do NOT clear error here — caller should manage error display
  }, []);

  const goHistory = useCallback(() => {
    setError(null);
    setAppState(AppState.HISTORY);
  }, []);

  // ── Camera hook ────────────────────────────────────────────
  const { videoRef, isReady, error: cameraError, restart: restartCamera } = useCamera();

  // ── Gesture handling ───────────────────────────────────────
  const onGestureDetected = useCallback(
    (event: { gesture: GestureType; confidence: number }) => {
      setGesture(event.gesture);
      setGestureConfidence(event.confidence);

      const state = appStateRef.current;

      // OK gesture in CAMERA_READY → start countdown
      if (event.gesture === 'ok' && state === AppState.CAMERA_READY) {
        setAppState(AppState.COUNTDOWN);
        return;
      }

      // Open palm anywhere except POSTER_READY → go back to camera
      if (event.gesture === 'open_palm' && state !== AppState.POSTER_READY) {
        goHome();
        return;
      }
    },
    [goHome],
  );

  // gestureDetector MUST be declared BEFORE handleMediaPipeResults
  const { processLandmarks } = useGestureDetector({
    onGestureDetected,
  });

  // handleMediaPipeResults MUST be declared BEFORE useMediaPipeHands
  const handleMediaPipeResults = useCallback(
    (landmarks: { x: number; y: number; z: number }[]) => {
      if (landmarks.length > 0) {
        processLandmarks(landmarks);
      }
    },
    [processLandmarks],
  );

  // ── MediaPipe hands hook ───────────────────────────────────
  const { canvasRef } = useMediaPipeHands({
    videoRef,
    onResults: handleMediaPipeResults,
  });

  // ── Countdown hook ─────────────────────────────────────────
  const onCountdownComplete = useCallback(async () => {
    const video = videoRef.current;
    if (!video) {
      setError('无法访问摄像头，请重试');
      goHome();
      return;
    }

    try {
      // Capture frame
      const base64Photo = captureFrame(video);
      setPhoto(base64Photo);

      // Transition to analyzing
      console.log('[FlowTrace] state:', AppState.ANALYZING, '| action:', 'analyze_start', '| image_size:', base64Photo.length);
      setAppState(AppState.ANALYZING);

      // Analyze photo for style recommendations
      const response = await analyzePhoto(base64Photo);
      setStyleOptions(response.data.options);

      // Transition to style selection
      console.log('[FlowTrace] state:', AppState.STYLE_SELECTION, '| options_count:', response.data.options.length);
      setAppState(AppState.STYLE_SELECTION);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '拍照失败，请重试';
      console.error('[App] Analyze failed:', msg);
      setError(msg);
      // Stay on camera view so user can see the error and retry
      goHome();
    }
  }, [videoRef, goHome]);

  const { remaining } = useCountdown({
    seconds: 3,
    active: appState === AppState.COUNTDOWN,
    onComplete: onCountdownComplete,
  });

  // ── Style selection handler ────────────────────────────────
  const handleSelectStyle = useCallback(
    async (style: StyleOption) => {
      setSelectedOption(style);
      setError(null);
      console.log('[FlowTrace] state:', AppState.GENERATING, '| style:', style.name, '| brief:', style.brief);
      setAppState(AppState.GENERATING);

      try {
        const response = await generatePoster(photo, style.name, style.brief);
        setPosterUrl(response.data.poster_url);
        console.log('[FlowTrace] state:', AppState.POSTER_READY, '| poster_url:', response.data.poster_url);
        setAppState(AppState.POSTER_READY);
      } catch (err) {
        const msg = err instanceof Error ? err.message : '生成海报失败，请重试';
        setError(msg);
        setAppState(AppState.STYLE_SELECTION);
      }
    },
    [photo],
  );

  // ── History data fetching ──────────────────────────────────
  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    setError(null);
    try {
      const response = await getHistory(1, 20);
      setHistoryItems(response.data.items);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '加载历史记录失败';
      setError(msg);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  // Fetch history when entering HISTORY state
  useEffect(() => {
    if (appState === AppState.HISTORY) {
      fetchHistory();
    }
  }, [appState, fetchHistory]);

  // ── Poster actions ─────────────────────────────────────────
  const handleRegenerate = useCallback(async () => {
    if (!selectedOption) return;
    setAppState(AppState.GENERATING);
    setError(null);

    try {
      const response = await generatePoster(photo, selectedOption.name, selectedOption.brief);
      setPosterUrl(response.data.poster_url);
      setAppState(AppState.POSTER_READY);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '重新生成失败';
      setError(msg);
      setAppState(AppState.POSTER_READY);
    }
  }, [photo, selectedOption]);

  // ── Determine whether to show camera view ──────────────────
  const showCamera =
    appState === AppState.CAMERA_READY ||
    appState === AppState.COUNTDOWN;

  const showGestureOverlay =
    appState === AppState.CAMERA_READY ||
    appState === AppState.COUNTDOWN;

  // ── Render ─────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-gray-800 shrink-0">
        <h1
          className="text-xl font-bold cursor-pointer select-none"
          onClick={goHome}
        >
          Pose Art Generator
        </h1>
        <button
          className="px-4 py-2 text-sm bg-gray-700 rounded hover:bg-gray-600 transition-colors"
          onClick={goHistory}
        >
          历史记录
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center overflow-auto">
        {/* ── Camera + Countdown overlay ─────────────────── */}
        {showCamera && (
          <div className="relative w-full max-w-3xl aspect-video bg-gray-800 rounded-xl overflow-hidden">
            {/* video element must always be in DOM so useCamera can attach stream */}
            <CameraView
              videoRef={videoRef}
              canvasRef={canvasRef}
              className={`w-full h-full ${isReady ? '' : 'invisible'}`}
            />
            {isReady && appState === AppState.COUNTDOWN && <Countdown remaining={remaining} />}
            {!isReady && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                {cameraError ? (
                  <ErrorDisplay
                    message={cameraError}
                    onRetry={restartCamera}
                    retryText="重新启动摄像头"
                  />
                ) : (
                  <p className="text-gray-400">正在启动摄像头...</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Gesture overlay ────────────────────────────── */}
        {showGestureOverlay && isReady && (
          <GestureOverlay gesture={gesture} confidence={gestureConfidence} />
        )}

        {/* ── Hint text below camera ─────────────────────── */}
        {appState === AppState.CAMERA_READY && isReady && (
          <div className="mt-4 text-center">
            {error && (
              <p className="text-red-400 text-sm mb-2">{error}</p>
            )}
            <p className="text-gray-400 text-sm">
              摆出 <span className="text-green-400 font-medium">OK 手势</span> 拍照
              &nbsp;&middot;&nbsp;
              摆出 <span className="text-green-400 font-medium">张开手掌</span> 返回
            </p>
          </div>
        )}

        {/* ── Analyzing state ────────────────────────────── */}
        {appState === AppState.ANALYZING && (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            {error ? (
              <ErrorDisplay message={error} onRetry={goHome} retryText="返回重试" />
            ) : (
              <>
                <div className="h-12 w-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-gray-400 text-lg">正在分析照片...</p>
                <p className="text-gray-600 text-sm">Vision LLM 分析中，通常需要 10-30 秒</p>
              </>
            )}
          </div>
        )}

        {/* ── Style selection ────────────────────────────── */}
        {appState === AppState.STYLE_SELECTION && (
          <div className="w-full max-w-4xl px-6 py-8">
            <StyleSelection
              styles={styleOptions}
              selectedStyle={selectedOption}
              onSelectStyle={handleSelectStyle}
              error={error}
              onRetry={goHome}
              photoThumbnail={photo}
            />
          </div>
        )}

        {/* ── Generating state ───────────────────────────── */}
        {appState === AppState.GENERATING && (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            {error ? (
              <ErrorDisplay message={error} onRetry={() => { setError(null); setAppState(AppState.STYLE_SELECTION); }} retryText="返回选择" />
            ) : (
              <>
                <div className="h-16 w-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-white text-lg font-medium">正在生成海报...</p>
                <p className="text-gray-500 text-sm">AI 构思构图 + 生成图片中，通常需要 30-90 秒</p>
              </>
            )}
          </div>
        )}

        {/* ── Poster display ─────────────────────────────── */}
        {appState === AppState.POSTER_READY && (
          <div className="w-full max-w-2xl px-6 py-8">
            {error ? (
              <ErrorDisplay
                message={error}
                onRetry={handleRegenerate}
                retryText="重新生成"
              />
            ) : (
              <PosterDisplay
                posterUrl={posterUrl}
                styleName={selectedOption?.name}
                onRegenerate={handleRegenerate}
                onRetake={goHome}
                onGoToHistory={goHistory}
              />
            )}
          </div>
        )}

        {/* ── History view ───────────────────────────────── */}
        {appState === AppState.HISTORY && (
          <div className="w-full max-w-4xl px-6 py-8">
            <HistoryList
              items={historyItems}
              isLoading={historyLoading}
              error={error}
              onRetry={fetchHistory}
              onBack={goHome}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
