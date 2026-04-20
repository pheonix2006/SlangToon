import { useRef, useState, useEffect, useCallback } from 'react';
import { AppState } from './types';
import type { ScriptData, HistoryItem } from './types';
import { useCamera } from './hooks/useCamera';
import { useGestureDetector } from './hooks/useGestureDetector';
import { useGestureConfirm } from './hooks/useGestureConfirm';
import { useMediaPipeHands } from './hooks/useMediaPipeHands';
import { generateScript, generateComic, getHistory, fetchConfig } from './services/api';
import GlowBackground from './components/GlowBackground/GlowBackground';
import PageTransition from './components/PageTransition';
import CameraView from './components/CameraView/CameraView';
import ScriptPreview from './components/ScriptPreview/ScriptPreview';
import ComicDisplay from './components/ComicDisplay/ComicDisplay';
import HistoryList from './components/HistoryList/HistoryList';
import GalleryView from './components/GalleryView/GalleryView';
import GestureProgressRing from './components/GestureProgressRing/GestureProgressRing';
import GestureHint from './components/GestureHint/GestureHint';
import ErrorDisplay from './components/ErrorDisplay';
import LoadingOrb from './components/LoadingOrb';

function App() {
  const [appState, setAppState] = useState<AppState>(AppState.CAMERA_READY);
  const [scriptData, setScriptData] = useState<ScriptData | null>(null);
  const [comicUrl, setComicUrl] = useState<string>('');
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [galleryItems, setGalleryItems] = useState<HistoryItem[]>([]);

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
    setError(null);
    setAppStateSync(AppState.CAMERA_READY);
  }, [setAppStateSync]);

  const goHistory = useCallback(() => {
    setError(null);
    setAppStateSync(AppState.HISTORY);
  }, [setAppStateSync]);

  // ── Idle Timer ──
  const IDLE_TIMEOUT_MS = 20_000;
  const IDLE_STATES = new Set([AppState.CAMERA_READY, AppState.COMIC_READY]);
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

  // ── Script generation ──
  const handleGenerateScript = useCallback(async () => {
    setError(null);
    setAppStateSync(AppState.SCRIPT_LOADING);
    try {
      const response = await generateScript();
      setScriptData(response.data);
      setAppStateSync(AppState.SCRIPT_PREVIEW);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate script';
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
      if (landmarks.length > 0) {
        processLandmarks(landmarks);
      }
    },
    [processLandmarks],
  );

  const { canvasRef } = useMediaPipeHands({
    videoRef,
    onResults: handleMediaPipeResults,
  });

  // ── Comic generation ──
  const handleGenerateComic = useCallback(async () => {
    if (!scriptData) return;
    setError(null);
    setAppStateSync(AppState.COMIC_GENERATING);
    try {
      const response = await generateComic({
        slang: scriptData.slang,
        origin: scriptData.origin,
        explanation: scriptData.explanation,
        panel_count: scriptData.panel_count,
        panels: scriptData.panels,
      });
      setComicUrl(response.data.comic_url);
      setAppStateSync(AppState.COMIC_READY);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate comic';
      setError(msg);
      setAppStateSync(AppState.SCRIPT_PREVIEW);
    }
  }, [scriptData, setAppStateSync]);

  // ── Gesture confirm layer ──
  const handleGestureAction = useCallback((action: string) => {
    switch (action) {
      case 'generateScript': handleGenerateScript(); break;
      case 'generateComic': handleGenerateComic(); break;
      case 'reshuffleScript': handleGenerateScript(); break;
      case 'startNew': goHome(); break;
      case 'wakeUp': setAppStateSync(AppState.CAMERA_READY); break;
    }
  }, [handleGenerateScript, handleGenerateComic, goHome, setAppStateSync]);

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
  const showCamera = appState === AppState.CAMERA_READY || appState === AppState.GALLERY;
  const isHistory = appState === AppState.HISTORY;

  return (
    <div className="relative w-full h-full bg-black text-white flex flex-col">
      {/* Global glow background */}
      <GlowBackground />

      {/* Main Content */}
      <main className={`relative z-10 flex-1 flex flex-col items-center overflow-auto px-4 ${
        (appState === AppState.COMIC_READY || appState === AppState.SCRIPT_PREVIEW)
          ? 'justify-start'
          : 'justify-center'
      }`}>
        {/* Camera always mounted — CSS-hidden when not needed to keep stream + MediaPipe alive */}
        <div
          className={!showCamera ? 'absolute w-0 h-0 overflow-hidden opacity-0 pointer-events-none' : undefined}
          aria-hidden={!showCamera}
        >
          <PageTransition>
            <div className={`relative w-full max-w-3xl aspect-video rounded-2xl overflow-hidden glass-panel ${
              appState === AppState.GALLERY ? 'absolute opacity-0 pointer-events-none w-0 h-0 overflow-hidden' : ''
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
            {appState === AppState.CAMERA_READY && (
              <div className="mt-5 text-center">
                {error && (
                  <p className="text-sm mb-2" style={{ color: 'rgba(255,183,77,0.6)' }}>{error}</p>
                )}
                <p className="text-[11px] tracking-[0.1em] font-display" style={{ color: 'rgba(255,183,77,0.35)' }}>
                  Show OK sign to generate · Open palm to go back
                </p>
              </div>
            )}
          </PageTransition>
        </div>

        {/* SCRIPT_LOADING / COMIC_GENERATING */}
        {(appState === AppState.SCRIPT_LOADING || appState === AppState.COMIC_GENERATING) && (
          <PageTransition>
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              {error ? (
                <ErrorDisplay
                  message={error}
                  onRetry={appState === AppState.SCRIPT_LOADING ? goHome : handleGenerateComic}
                  retryText="Retry"
                />
              ) : (
                <LoadingOrb
                  label={appState === AppState.SCRIPT_LOADING ? 'CREATING' : 'DRAWING'}
                  subtext={
                    appState === AppState.SCRIPT_LOADING
                      ? '寻找一个有趣的俚语...'
                      : '绘制你的漫画...'
                  }
                />
              )}
            </div>
          </PageTransition>
        )}

        {/* SCRIPT_PREVIEW */}
        {appState === AppState.SCRIPT_PREVIEW && scriptData && (
          <PageTransition>
            <ScriptPreview
              data={scriptData}
            />
          </PageTransition>
        )}

        {/* COMIC_READY */}
        {appState === AppState.COMIC_READY && (
          <PageTransition>
            <ComicDisplay
              comicUrl={comicUrl}
              slang={scriptData?.slang ?? ''}
            />
          </PageTransition>
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
          <PageTransition>
            <GalleryView items={galleryItems} />
          </PageTransition>
        )}
      </main>
      <GestureProgressRing gesture={activeGesture} progress={progress} label={label} />
      <GestureHint appState={appState} />
    </div>
  );
}

export default App;
