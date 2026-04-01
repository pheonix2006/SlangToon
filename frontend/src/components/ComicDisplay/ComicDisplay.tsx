interface ComicDisplayProps {
  comicUrl: string;
  slang: string;
  onNew: () => void;
  onGoToHistory: () => void;
}

export default function ComicDisplay({ comicUrl, slang, onNew, onGoToHistory }: ComicDisplayProps) {
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = comicUrl;
    link.download = `slangtoon-${slang.replace(/\s+/g, '-').toLowerCase()}.png`;
    link.click();
  };

  return (
    <div className="w-full max-w-4xl px-6 py-8">
      <h2 className="text-xl font-bold text-yellow-400 mb-4 text-center">&quot;{slang}&quot;</h2>

      <div className="rounded-xl overflow-hidden shadow-2xl border border-gray-700">
        <img
          src={comicUrl}
          alt={`Comic strip for "${slang}"`}
          className="w-full h-auto"
        />
      </div>

      <div className="flex gap-4 justify-center mt-6">
        <button
          onClick={handleDownload}
          className="px-6 py-3 bg-green-600 rounded-lg hover:bg-green-500 transition-colors"
        >
          Download
        </button>
        <button
          onClick={onGoToHistory}
          className="px-6 py-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
        >
          History
        </button>
        <button
          onClick={onNew}
          className="px-6 py-3 bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors"
        >
          New Slang
        </button>
      </div>
    </div>
  );
}
