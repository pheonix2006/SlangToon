import { useRef, useState, useEffect, useCallback } from 'react';
import { AppState } from './types';
import type { ScriptData, HistoryItem } from './types';
import { useCamera } from './hooks/useCamera';
import { useGestureDetector } from './hooks/useGestureDetector';
import { useGestureConfirm } from './hooks/useGestureConfirm';
import { useMediaPipeHands } from './hooks/useMediaPipeHands';
import { generateScriptStream, generateComic, getHistory, fetchConfig } from './services/api';
import GlowBackground from './components/GlowBackground/GlowBackground';
import PageTransition from './components/PageTransition';
import CameraView from './components/CameraView/CameraView';
import { CountdownCapture } from './components/CountdownCapture';
import ComicDisplay from './components/ComicDisplay/ComicDisplay';
import HistoryList from './components/HistoryList/HistoryList';
import GalleryView from './components/GalleryView/GalleryView';
import GestureProgressRing from './components/GestureProgressRing/GestureProgressRing';
import GestureHint from './components/GestureHint/GestureHint';
import ErrorDisplay from './components/ErrorDisplay';
import LoadingOrb from './components/LoadingOrb';
import ThinkingDisplay from './components/ThinkingDisplay/ThinkingDisplay';

function App() {
  const [appState, setAppState] = useState<AppState>(AppState.CAMERA_READY);
  const [scriptData, setScriptData] = useState<ScriptData | null>(null);
  const [comicUrl, setComicUrl] = useState<string>('');
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [galleryItems, setGalleryItems] = useState<HistoryItem[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_referenceImage, setReferenceImage] = useState<string | null>(null);
  const [thinkingText, setThinkingText] = useState('');
  const [generatingPhase, setGeneratingPhase] = useState<'thinking' | 'comic'>('thinking');

  const appStateRef = useRef<AppState>(appState);
  const setAppStateSync = useCallback((newState: AppState) => {
    appStateRef.current = newState;
    setAppState(newState);
  }, []);

  // ── Fetch backend config (timeouts) ──
  useEffect(() => {
    fetchConfig();
  }, []);

  // ── Navigation ──
  const goHome = useCallback(() => {
    setScriptData(null);
    setComicUrl('');
    setReferenceImage(null);
    setError(null);
    setAppStateSync(AppState.CAMERA_READY);
  }, [setAppStateSync]);


  // ── Idle Timer ──
  const IDLE_TIMEOUT_MS = 20_000;
  const IDLE_STATES = new Set([AppState.CAMERA_READY, AppState.COMIC_READY]);
  const GLOW_STATES = new Set([AppState.GENERATING]);
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const startIdleTimer = useCallback(() => {
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    idleTimerRef.current = setTimeout(() => setAppStateSync(AppState.GALLERY), IDLE_TIMEOUT_MS);
  }, [setAppStateSync]);

  const resetIdleTimer = useCallback(() => { startIdleTimer(); }, [startIdleTimer]);

  useEffect(() => {
    if (IDLE_STATES.has(appState)) startIdleTimer();
    else if (idleTimerRef.current) { clearTimeout(idleTimerRef.current); idleTimerRef.current = null; }
    return () => { if (idleTimerRef.current) clearTimeout(idleTimerRef.current); };
  }, [appState, startIdleTimer]);

  // ── Camera ──
  const { videoRef, isReady, error: cameraError, restart: restartCamera } = useCamera();

  // ── Unified generation: script → comic (串行) ──
  const handleGenerate = useCallback(async (capturedImage: string) => {
    setReferenceImage(capturedImage);
    setError(null);
    setThinkingText('');
    setGeneratingPhase('thinking');
    setAppStateSync(AppState.GENERATING);

    try {
      let scriptResult: ScriptData | null = null;

      await generateScriptStream(
        (text) => setThinkingText((prev) => prev + text),
        (data) => {
          scriptResult = data;
          setScriptData(data);
          setGeneratingPhase('comic');
        },
        (msg) => {
          throw new Error(msg);
        },
      );

      if (!scriptResult) {
        throw new Error('No script data received');
      }

      const script = scriptResult as ScriptData;
      const comicResponse = await generateComic({
        slang: script.slang,
        origin: script.origin,
        explanation: script.explanation,
        panel_count: script.panel_count,
        panels: script.panels,
        reference_image: capturedImage,
      });
      setComicUrl(comicResponse.data.comic_url);
      setAppStateSync(AppState.COMIC_READY);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate';
      setError(msg);
      setAppStateSync(AppState.CAMERA_READY);
    }
  }, [setAppStateSync]);

  // ── Gesture detection (frame-level) ──
  const handleWaveDetected = useCallback(() => {
    if (appStateRef.current === AppState.GALLERY) {
      setAppStateSync(AppState.CAMERA_READY);
    }
  }, [setAppStateSync]);

  const { processLandmarks, currentGesture } = useGestureDetector({
    onWaveDetected: handleWaveDetected,
  });

  const handleMediaPipeResults = useCallback(
    (landmarks: { x: number; y: number; z: number }[]) => {
      processLandmarks(landmarks);
    },
    [processLandmarks],
  );

  const { canvasRef } = useMediaPipeHands({
    videoRef,
    onResults: handleMediaPipeResults,
  });

  // ── Gesture confirm layer ──
  const handleGestureAction = useCallback((action: string) => {
    switch (action) {
      case 'startCountdown': setAppStateSync(AppState.COUNTDOWN); break;
      case 'startNew': goHome(); break;
      case 'wakeUp': setAppStateSync(AppState.CAMERA_READY); break;
    }
  }, [goHome, setAppStateSync]);

  const { activeGesture, progress, label, feedGesture } = useGestureConfirm({
    appState,
    onConfirmed: handleGestureAction,
  });

  // Feed currentGesture to confirm layer + reset idle timer
  useEffect(() => {
    feedGesture(currentGesture);
    if (currentGesture !== 'none' && IDLE_STATES.has(appState)) {
      resetIdleTimer();
    }
  }, [currentGesture, feedGesture, appState, resetIdleTimer]);

  // ── History ──
  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    setError(null);
    try {
      const response = await getHistory(1, 20);
      setHistoryItems(response.data.items);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load history';
      setError(msg);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (appState === AppState.HISTORY) {
      fetchHistory();
    }
  }, [appState, fetchHistory]);

  // ── Gallery data ──
  useEffect(() => {
    if (appState === AppState.GALLERY) {
      getHistory(1, 50).then(r => setGalleryItems(r.data.items)).catch(() => {});
    }
  }, [appState]);

  // ── Render ──
  // Camera must stay mounted (not just alive in GALLERY) — CSS-hidden when unused
  // so the <video> element is never unmounted, preserving the stream + MediaPipe loop
  const showCamera = appState === AppState.CAMERA_READY
      || appState === AppState.COUNTDOWN
      || appState === AppState.GALLERY;
  const isHistory = appState === AppState.HISTORY;

  return (
    <div className="relative w-full h-full bg-black text-white flex flex-col">
      {/* Global glow background — only during loading states */}
      {GLOW_STATES.has(appState) && <GlowBackground />}

      {/* Main Content */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center overflow-hidden">
        {/* Camera always mounted — CSS-hidden when not needed to keep stream + MediaPipe alive */}
        <div
          className={!showCamera ? 'absolute w-0 h-0 overflow-hidden opacity-0 pointer-events-none' : undefined}
          aria-hidden={!showCamera}
        >
          <div className={`fixed inset-0 ${
            appState === AppState.GALLERY ? 'opacity-0 pointer-events-none' : ''
          }`}>
            <CameraView
              videoRef={videoRef}
              canvasRef={canvasRef}
              className={`w-full h-full ${isReady ? '' : 'invisible'}`}
            />
            {!isReady && appState !== AppState.GALLERY && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                {cameraError ? (
                  <ErrorDisplay message={cameraError} onRetry={restartCamera} retryText="Restart Camera" />
                ) : (
                  <p className="text-[11px]" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    Starting camera...
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* COUNTDOWN */}
        {appState === AppState.COUNTDOWN && (
          <CountdownCapture
            videoRef={videoRef}
            onCapture={handleGenerate}
          />
        )}

        {/* GENERATING */}
        {appState === AppState.GENERATING && (
          <PageTransition>
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              {error ? (
                <ErrorDisplay
                  message={error}
                  onRetry={goHome}
                  retryText="Try Again"
                />
              ) : (
                <>
                  <LoadingOrb
                    label={generatingPhase === 'thinking' ? 'THINKING' : 'CREATING'}
                    subtext={generatingPhase === 'thinking' ? 'AI 正在构思剧本...' : '正在生成漫画...'}
                  />
                  <ThinkingDisplay
                    text={thinkingText}
                    isActive={generatingPhase === 'thinking'}
                  />
                </>
              )}
            </div>
          </PageTransition>
        )}

        {/* COMIC_READY */}
        {appState === AppState.COMIC_READY && (
          <ComicDisplay
            comicUrl={comicUrl}
            slang={scriptData?.slang ?? ''}
          />
        )}

        {/* HISTORY */}
        {isHistory && (
          <PageTransition>
            <HistoryList
              items={historyItems}
              isLoading={historyLoading}
              error={error}
              onRetry={fetchHistory}
              onBack={goHome}
            />
          </PageTransition>
        )}

        {/* GALLERY */}
        {appState === AppState.GALLERY && (
          <GalleryView items={galleryItems} />
        )}
      </main>
      <GestureProgressRing gesture={activeGesture} progress={progress} label={label} />
      <GestureHint appState={appState} />
    </div>
  );
}

export default App;
