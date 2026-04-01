import { useRef, useState, useEffect, useCallback } from 'react';
import { AppState } from './types';
import type { ScriptData, HistoryItem } from './types';
import { useCamera } from './hooks/useCamera';
import { useGestureDetector } from './hooks/useGestureDetector';
import { useMediaPipeHands } from './hooks/useMediaPipeHands';
import { generateScript, generateComic, getHistory } from './services/api';
import CameraView from './components/CameraView/CameraView';
import ScriptPreview from './components/ScriptPreview/ScriptPreview';
import ComicDisplay from './components/ComicDisplay/ComicDisplay';
import HistoryList from './components/HistoryList/HistoryList';
import ErrorDisplay from './components/ErrorDisplay';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  // ── State machine ──
  const [appState, setAppState] = useState<AppState>(AppState.CAMERA_READY);
  const [scriptData, setScriptData] = useState<ScriptData | null>(null);
  const [comicUrl, setComicUrl] = useState<string>('');
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const appStateRef = useRef<AppState>(appState);
  useEffect(() => {
    appStateRef.current = appState;
  }, [appState]);

  // ── Navigation helpers ──
  const goHome = useCallback(() => {
    setScriptData(null);
    setComicUrl('');
    setAppState(AppState.CAMERA_READY);
  }, []);

  const goHistory = useCallback(() => {
    setError(null);
    setAppState(AppState.HISTORY);
  }, []);

  // ── Camera hook ──
  const { videoRef, isReady, error: cameraError, restart: restartCamera } = useCamera();

  // ── Gesture handling ──
  const onGestureDetected = useCallback(
    (event: { gesture: 'ok' | 'open_palm' | 'none'; confidence: number }) => {
      const state = appStateRef.current;

      if (event.gesture === 'ok' && state === AppState.CAMERA_READY) {
        handleGenerateScript();
        return;
      }

      if (event.gesture === 'open_palm' && state !== AppState.COMIC_READY) {
        goHome();
      }
    },
    [goHome],
  );

  const { processLandmarks } = useGestureDetector({ onGestureDetected });

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

  // ── Script generation ──
  const handleGenerateScript = useCallback(async () => {
    setError(null);
    setAppState(AppState.SCRIPT_LOADING);

    try {
      const response = await generateScript();
      setScriptData(response.data);
      setAppState(AppState.SCRIPT_PREVIEW);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate script';
      setError(msg);
      setAppState(AppState.CAMERA_READY);
    }
  }, []);

  // ── Comic generation ──
  const handleGenerateComic = useCallback(async () => {
    if (!scriptData) return;

    setError(null);
    setAppState(AppState.COMIC_GENERATING);

    try {
      const response = await generateComic({
        slang: scriptData.slang,
        origin: scriptData.origin,
        explanation: scriptData.explanation,
        panel_count: scriptData.panel_count,
        panels: scriptData.panels,
      });
      setComicUrl(response.data.comic_url);
      setAppState(AppState.COMIC_READY);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate comic';
      setError(msg);
      setAppState(AppState.SCRIPT_PREVIEW);
    }
  }, [scriptData]);

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

  // ── Render ──
  const showCamera = appState === AppState.CAMERA_READY;

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-gray-800 shrink-0">
        <h1
          className="text-xl font-bold cursor-pointer select-none"
          onClick={goHome}
        >
          SlangToon
        </h1>
        <button
          className="px-4 py-2 text-sm bg-gray-700 rounded hover:bg-gray-600 transition-colors"
          onClick={goHistory}
        >
          History
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center overflow-auto">
        {showCamera && (
          <div className="relative w-full max-w-3xl aspect-video bg-gray-800 rounded-xl overflow-hidden">
            <CameraView
              videoRef={videoRef}
              canvasRef={canvasRef}
              className={`w-full h-full ${isReady ? '' : 'invisible'}`}
            />
            {!isReady && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                {cameraError ? (
                  <ErrorDisplay message={cameraError} onRetry={restartCamera} retryText="Restart Camera" />
                ) : (
                  <p className="text-gray-400">Starting camera...</p>
                )}
              </div>
            )}
          </div>
        )}

        {showCamera && isReady && (
          <div className="mt-4 text-center">
            {error && <p className="text-red-400 text-sm mb-2">{error}</p>}
            <p className="text-gray-400 text-sm">
              Show <span className="text-green-400 font-medium">OK sign</span> to generate
              &nbsp;&middot;&nbsp;
              Show <span className="text-green-400 font-medium">open palm</span> to go back
            </p>
          </div>
        )}

        {(appState === AppState.SCRIPT_LOADING || appState === AppState.COMIC_GENERATING) && (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            {error ? (
              <ErrorDisplay
                message={error}
                onRetry={
                  appState === AppState.SCRIPT_LOADING
                    ? goHome
                    : handleGenerateComic
                }
                retryText="Retry"
              />
            ) : (
              <>
                <LoadingSpinner />
                <p className="text-gray-400 text-lg">
                  {appState === AppState.SCRIPT_LOADING
                    ? 'Creating something fun...'
                    : 'Drawing your comic...'}
                </p>
              </>
            )}
          </div>
        )}

        {appState === AppState.SCRIPT_PREVIEW && scriptData && (
          <ScriptPreview
            data={scriptData}
            onShuffle={handleGenerateScript}
            onGenerate={handleGenerateComic}
            isLoading={false}
          />
        )}

        {appState === AppState.COMIC_READY && (
          <ComicDisplay
            comicUrl={comicUrl}
            slang={scriptData?.slang ?? ''}
            onNew={goHome}
            onGoToHistory={goHistory}
          />
        )}

        {appState === AppState.HISTORY && (
          <HistoryList
            items={historyItems}
            isLoading={historyLoading}
            error={error}
            onRetry={fetchHistory}
            onBack={goHome}
          />
        )}
      </main>
    </div>
  );
}

export default App;
