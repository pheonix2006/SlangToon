import type { StyleOption } from '../../types';

interface StyleCardProps {
  style: StyleOption;
  isSelected: boolean;
  onSelect: (style: StyleOption) => void;
}

export default function StyleCard({
  style,
  isSelected,
  onSelect,
}: StyleCardProps) {
  return (
    <button
      onClick={() => onSelect(style)}
      className={`
        relative p-5 rounded-xl text-left
        transition-all duration-200 ease-in-out
        cursor-pointer group
        ${
          isSelected
            ? 'border-2 border-cyan-400 bg-cyan-500/10 shadow-[0_0_15px_rgba(6,182,212,0.2)]'
            : 'border-2 border-gray-700 bg-gray-800/50 hover:border-gray-500 hover:bg-gray-800/80 hover:scale-[1.02]'
        }
      `}
    >
      {/* Checkmark icon when selected */}
      {isSelected && (
        <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-cyan-500 flex items-center justify-center">
          <svg
            className="w-4 h-4 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
      )}

      {/* Style name */}
      <h3
        className={`
          text-lg font-semibold mb-2 transition-colors
          ${isSelected ? 'text-cyan-300' : 'text-gray-200 group-hover:text-white'}
        `}
      >
        {style.name}
      </h3>

      {/* Style brief description */}
      <p className="text-sm text-gray-400 line-clamp-2 leading-relaxed">
        {style.brief}
      </p>
    </button>
  );
}
