import type { ScriptData } from '../../types';

interface ScriptPreviewProps {
  data: ScriptData;
  onShuffle: () => void;
  onGenerate: () => void;
  isLoading: boolean;
}

export default function ScriptPreview({ data, onShuffle, onGenerate, isLoading }: ScriptPreviewProps) {
  return (
    <div className="w-full max-w-3xl px-6 py-8">
      {/* Slang title card */}
      <div className="bg-gray-800 rounded-xl p-6 mb-6">
        <h2 className="text-2xl font-bold text-yellow-400 mb-2">&quot;{data.slang}&quot;</h2>
        <p className="text-gray-400 text-sm mb-1">
          Origin: <span className="text-gray-300">{data.origin}</span>
        </p>
        <p className="text-gray-300">{data.explanation}</p>
      </div>

      {/* Panel descriptions */}
      <div className="space-y-3 mb-8">
        {data.panels.map((panel, i) => (
          <div key={i} className="bg-gray-800/50 rounded-lg p-4 border-l-4 border-indigo-500">
            <p className="text-gray-400 text-xs mb-1">Panel {i + 1}</p>
            <p className="text-gray-200">{panel.scene}</p>
            {panel.dialogue && (
              <p className="text-yellow-300/80 text-sm mt-1 italic">{panel.dialogue}</p>
            )}
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-4 justify-center">
        <button
          onClick={onShuffle}
          disabled={isLoading}
          className="px-6 py-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Shuffle
        </button>
        <button
          onClick={onGenerate}
          disabled={isLoading}
          className="px-6 py-3 bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Generate Comic
        </button>
      </div>
    </div>
  );
}
