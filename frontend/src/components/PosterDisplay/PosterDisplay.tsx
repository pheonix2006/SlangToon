interface PosterDisplayProps {
  posterUrl: string;
  styleName?: string;
  isGenerating?: boolean;
  onRegenerate?: () => void;
  onRetake?: () => void;
  onGoToHistory?: () => void;
  onSave?: () => void;
}

export default function PosterDisplay({
  posterUrl,
  styleName,
  isGenerating = false,
  onRegenerate,
  onRetake,
  onGoToHistory,
  onSave,
}: PosterDisplayProps) {
  const handleSave = async () => {
    if (!posterUrl) return;

    // Fetch the image as blob to ensure correct download regardless of proxy/CORS
    try {
      const resp = await fetch(posterUrl);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `poster-${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      onSave?.();
    } catch {
      // Fallback: direct navigation
      const link = document.createElement('a');
      link.href = posterUrl;
      link.download = `poster-${Date.now()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      onSave?.();
    }
  };

  return (
    <div className="flex flex-col items-center gap-6 w-full max-w-2xl mx-auto">
      {/* Poster image display */}
      <div className="relative w-full rounded-xl overflow-hidden border border-gray-700">
        <img
          src={posterUrl}
          alt="生成的海报"
          className="w-full h-auto object-contain"
        />

        {/* Loading overlay during generation */}
        {isGenerating && (
          <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center gap-4 backdrop-blur-sm">
            <div className="h-12 w-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-white text-lg font-medium">正在生成海报...</p>
          </div>
        )}
      </div>

      {/* Style info */}
      {styleName && (
        <p className="text-gray-400 text-sm">
          风格: <span className="text-cyan-400">{styleName}</span>
        </p>
      )}

      {/* Action buttons row */}
      <div className="flex flex-wrap justify-center gap-3">
        <button
          onClick={handleSave}
          disabled={isGenerating || !posterUrl}
          className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          {/* Download icon */}
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          保存下载
        </button>

        {onRegenerate && (
          <button
            onClick={onRegenerate}
            disabled={isGenerating}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors flex items-center gap-2"
          >
            {/* Refresh icon */}
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            重新生成
          </button>
        )}

        {onRetake && (
          <button
            onClick={onRetake}
            disabled={isGenerating}
            className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-white rounded-lg transition-colors flex items-center gap-2"
          >
            {/* Camera icon */}
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            重新拍照
          </button>
        )}

        {onGoToHistory && (
          <button
            onClick={onGoToHistory}
            disabled={isGenerating}
            className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:text-gray-500 text-white rounded-lg transition-colors flex items-center gap-2"
          >
            {/* History icon */}
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            历史记录
          </button>
        )}
      </div>
    </div>
  );
}
