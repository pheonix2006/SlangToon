import { useState, useEffect, useRef, useCallback } from 'react';
import type { HistoryItem } from '../../types';

interface GalleryViewProps {
  items: HistoryItem[];
  intervalMs?: number;
}

function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4" data-testid="gallery-empty">
      <h1
        className="text-3xl tracking-[0.3em] font-display"
        style={{ color: 'rgba(255,183,77,0.5)', animation: 'gallery-breathe 4s ease-in-out infinite' }}
      >
        SLANGTOON
      </h1>
      <p
        className="text-sm font-display tracking-wider"
        style={{ color: 'rgba(255,255,255,0.25)' }}
      >
        Wave to create your first comic
      </p>
    </div>
  );
}

export default function GalleryView({ items, intervalMs = 8000 }: GalleryViewProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const advance = useCallback(() => {
    if (items.length <= 1) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % items.length);
      setIsTransitioning(false);
    }, 600);
  }, [items.length]);

  useEffect(() => {
    if (items.length <= 1) return;
    timerRef.current = setInterval(advance, intervalMs);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [advance, intervalMs, items.length]);

  const item = items[currentIndex];

  if (items.length === 0) {
    return (
      <div data-testid="gallery-view" className="relative w-full h-full flex flex-col">
        <EmptyState />
      </div>
    );
  }

  return (
    <div data-testid="gallery-view" className="relative w-full h-full flex flex-col">
      {/* Entrance overlay - black fade in */}
      <div
        data-testid="gallery-entrance"
        className="absolute inset-0 pointer-events-none z-20"
        style={{ animation: 'gallery-entrance-fade 2000ms ease-in-out forwards' }}
      />

      {/* Top hint */}
      <p
        className="text-center text-[10px] tracking-[0.2em] font-display shrink-0 pt-2"
        style={{ color: 'rgba(255,255,255,0.15)' }}
      >
        Wave to interact
      </p>

      {/* Main content: left text + right image */}
      <div className="flex-1 flex gap-8 px-8 py-6 items-center justify-center overflow-hidden">
        {/* Left — museum label */}
        <div
          className="flex flex-col justify-center gap-5 w-[320px] shrink-0"
          data-testid="gallery-label"
          style={{ transition: 'opacity 1200ms ease-in-out', opacity: isTransitioning ? 0 : 1 }}
        >
          <p
            className="text-[11px] tracking-[0.25em] font-display"
            style={{ color: 'rgba(255,183,77,0.35)' }}
          >
            SLANGTOON
          </p>
          <h2
            className="text-2xl italic leading-tight font-accent"
            style={{ color: '#FFF3E0' }}
          >
            &ldquo;{item.slang}&rdquo;
          </h2>
          <p
            className="text-xs tracking-wide"
            style={{ color: 'rgba(255,183,77,0.55)' }}
          >
            {item.origin}
          </p>
          <p
            className="text-sm leading-relaxed"
            style={{ color: 'rgba(255,255,255,0.65)' }}
          >
            {item.explanation}
          </p>
          {/* Dot indicators */}
          <div className="flex gap-2 mt-2" data-testid="gallery-dots">
            {items.map((_, idx) => (
              <span
                key={idx}
                data-testid={`gallery-dot-${idx}`}
                className="rounded-full w-2 h-2"
                style={{
                  backgroundColor:
                    idx === currentIndex ? '#FFB74D' : 'rgba(255,255,255,0.25)',
                  transition: 'background-color 1200ms ease-in-out',
                }}
              />
            ))}
          </div>
        </div>

        {/* Right — comic image */}
        <div className="flex-1 max-w-lg flex items-center justify-center"
          style={{ transition: 'opacity 1200ms ease-in-out', opacity: isTransitioning ? 0 : 1 }}
        >
          <div className="rounded-xl overflow-hidden gold-border gold-glow w-full">
            <img
              src={item.comic_url}
              alt={`Comic for "${item.slang}"`}
              className="w-full h-auto object-contain"
              style={{ aspectRatio: '9/16' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
