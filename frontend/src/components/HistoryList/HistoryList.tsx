import { useState } from 'react';
import type { HistoryItem } from '../../types';
import LoadingOrb from '../LoadingOrb';
import GlassButton from '../GlassButton';

interface HistoryListProps {
  items: HistoryItem[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onBack?: () => void;
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
}: HistoryListProps) {
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

  const handleBack = () => {
    if (selectedItem) {
      setSelectedItem(null);
    } else {
      onBack?.();
    }
  };

  // Detail view
  if (selectedItem) {
    return (
      <div
        className="flex flex-col items-center gap-5 w-full max-w-2xl mx-auto px-6 py-4"
        style={{ animation: 'fade-scale-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards' }}
      >
        <button
          onClick={handleBack}
          className="self-start text-[11px] tracking-[0.15em] font-display cursor-pointer"
          style={{ color: 'rgba(255,183,77,0.4)' }}
        >
          ← Back to list
        </button>

        <div className="w-full rounded-xl overflow-hidden gold-border gold-glow">
          <img
            src={selectedItem.comic_url}
            alt={`Comic for "${selectedItem.slang}"`}
            className="w-full h-auto"
          />
        </div>

        <div className="text-center">
          <p className="font-accent italic text-lg" style={{ color: '#FFF3E0' }}>
            &ldquo;{selectedItem.slang}&rdquo;
          </p>
          <p className="text-[10px] mt-2" style={{ color: 'rgba(255,255,255,0.3)' }}>
            {selectedItem.origin} · {selectedItem.panel_count} panels · {formatDate(selectedItem.created_at)}
          </p>
        </div>
      </div>
    );
  }

  // Loading
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <LoadingOrb label="LOADING" subtext="Loading history..." />
      </div>
    );
  }

  // Error
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <p className="text-sm" style={{ color: 'rgba(255,255,255,0.6)' }}>{error}</p>
        {onRetry && (
          <GlassButton onClick={onRetry}>Retry</GlassButton>
        )}
      </div>
    );
  }

  // Grid view
  return (
    <div
      className="flex flex-col gap-6 w-full px-6 py-4"
      style={{ animation: 'fade-scale-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards' }}
    >
      {/* Empty state */}
      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center"
            style={{ border: '1px solid rgba(255,183,77,0.15)' }}
          >
            <span style={{ color: 'rgba(255,183,77,0.3)' }}>○</span>
          </div>
          <p className="text-sm font-display tracking-wider" style={{ color: 'rgba(255,183,77,0.4)' }}>
            No history yet
          </p>
          <p className="text-[11px]" style={{ color: 'rgba(255,255,255,0.2)' }}>
            Your generated comics will appear here
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 2xl:grid-cols-5 gap-4">
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => setSelectedItem(item)}
              className="group flex flex-col gap-2 rounded-xl overflow-hidden glass-panel transition-all duration-200 hover:-translate-y-0.5 cursor-pointer"
            >
              <div className="aspect-[3/4] overflow-hidden">
                <img
                  src={item.thumbnail_url || item.comic_url}
                  alt={item.slang}
                  className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
                />
              </div>
              <div className="px-3 pb-3 text-left">
                <p className="text-xs truncate" style={{ color: 'rgba(255,183,77,0.6)' }}>
                  &ldquo;{item.slang}&rdquo;
                </p>
                <p className="text-[10px] mt-0.5" style={{ color: 'rgba(255,255,255,0.25)' }}>
                  {item.panel_count} panels · {formatDate(item.created_at)}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
