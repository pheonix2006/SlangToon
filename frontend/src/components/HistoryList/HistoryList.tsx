import { useState } from 'react';
import type { HistoryItem } from '../../types';

interface HistoryListProps {
  items: HistoryItem[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onBack?: () => void;
  onSelectItem?: (item: HistoryItem) => void;
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

export default function HistoryList({
  items,
  isLoading = false,
  error = null,
  onRetry,
  onBack,
  onSelectItem,
}: HistoryListProps) {
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

  const handleSelectItem = (item: HistoryItem) => {
    setSelectedItem(item);
    onSelectItem?.(item);
  };

  const handleBack = () => {
    if (selectedItem) {
      setSelectedItem(null);
    } else {
      onBack?.();
    }
  };

  // Full comic view
  if (selectedItem) {
    return (
      <div className="flex flex-col items-center gap-4 w-full max-w-2xl mx-auto">
        {/* Back button */}
        <button
          onClick={handleBack}
          className="self-start px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors flex items-center gap-2"
        >
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to list
        </button>

        {/* Full comic image */}
        <img
          src={selectedItem.comic_url}
          alt={`Comic for "${selectedItem.slang}"`}
          className="w-full rounded-xl border border-gray-700"
        />

        {/* Comic info */}
        <div className="text-center">
          <p className="text-gray-300 font-medium">
            &quot;{selectedItem.slang}&quot;
          </p>
          <p className="text-gray-400 text-sm mt-1">
            Origin: <span className="text-gray-300">{selectedItem.origin}</span>
            &nbsp;&middot;&nbsp;
            {selectedItem.panel_count} panels
          </p>
          <p className="text-gray-500 text-xs mt-1">
            {formatDate(selectedItem.created_at)}
          </p>
        </div>
      </div>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="h-10 w-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-gray-400 mt-3">Loading history...</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <p className="text-red-400 mb-4">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Header with back button */}
      <div className="flex items-center gap-4">
        {onBack && (
          <button
            onClick={handleBack}
            className="p-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
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
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>
        )}
        <h2 className="text-2xl font-bold text-white">History</h2>
      </div>

      {/* Empty state */}
      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <svg
            className="h-16 w-16 text-gray-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <p className="text-gray-500 text-lg">No history yet</p>
          <p className="text-gray-600 text-sm">Your generated comics will appear here</p>
        </div>
      ) : (
        /* History items grid */
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => handleSelectItem(item)}
              className="group flex flex-col gap-2 rounded-xl overflow-hidden border border-gray-700 hover:border-gray-500 bg-gray-800/50 transition-all hover:scale-[1.02]"
            >
              {/* Thumbnail */}
              <div className="aspect-[3/4] overflow-hidden">
                <img
                  src={item.thumbnail_url || item.comic_url}
                  alt={item.slang}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                />
              </div>

              {/* Info */}
              <div className="px-3 pb-3 text-left">
                <p className="text-sm font-medium text-yellow-400 truncate">
                  &quot;{item.slang}&quot;
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {item.panel_count} panels &middot; {formatDate(item.created_at)}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
