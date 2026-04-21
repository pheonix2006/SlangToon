import { useState, useEffect, useRef, useCallback } from 'react';
import type { HistoryItem } from '../../types';

interface GalleryViewProps {
  items: HistoryItem[];
  intervalMs?: number;
}

function EmptyState() {
  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center gap-4 bg-black" data-testid="gallery-empty">
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
  const transitioningRef = useRef(false);

  const advance = useCallback(() => {
    if (items.length <= 1) return;
    if (transitioningRef.current) return;
    transitioningRef.current = true;
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % items.length);
      setIsTransitioning(false);
      transitioningRef.current = false;
    }, 1500);
  }, [items.length]);

  useEffect(() => {
    if (items.length <= 1) return;
    timerRef.current = setInterval(advance, intervalMs);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [advance, intervalMs, items.length]);

  const item = items[currentIndex];

  if (items.length === 0) return <EmptyState />;

  return (
    <div data-testid="gallery-view" className="fixed inset-0 bg-black">
      {/* Entrance overlay */}
      <div
        data-testid="gallery-entrance"
        className="absolute inset-0 pointer-events-none z-20"
        style={{ animation: 'gallery-entrance-fade 2000ms ease-in-out forwards' }}
      />

      {/* Fullscreen comic image */}
      <div className="absolute inset-0 flex items-center justify-center">
        <img
          src={item.comic_url}
          alt={`Comic for "${item.slang}"`}
          className="max-w-full max-h-full object-contain transition-opacity duration-[1500ms] ease-in-out"
          style={{ opacity: isTransitioning ? 0 : 1 }}
        />
      </div>

      {/* Bottom gradient for label readability */}
      <div
        className="absolute bottom-0 left-0 right-0 h-48 pointer-events-none"
        style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 50%, transparent 100%)' }}
      />

      {/* Museum label — bottom-left */}
      <div
        className="absolute bottom-8 left-8 z-10 flex flex-col gap-2 transition-opacity duration-[1500ms] ease-in-out"
        style={{ opacity: isTransitioning ? 0 : 1 }}
      >
        <p
          className="text-[10px] tracking-[0.25em] font-display"
          style={{ color: 'rgba(255,183,77,0.3)' }}
        >
          SLANGTOON
        </p>
        <h2
          className="text-lg italic leading-tight font-accent"
          style={{ color: 'rgba(255,243,224,0.85)' }}
        >
          &ldquo;{item.slang}&rdquo;
        </h2>
        <p
          className="text-[10px] tracking-wide"
          style={{ color: 'rgba(255,183,77,0.45)' }}
        >
          {item.origin}
        </p>
        <p
          className="text-xs leading-relaxed max-w-xs"
          style={{ color: 'rgba(255,255,255,0.5)' }}
        >
          {item.explanation}
        </p>
        {/* Dot indicators */}
        <div className="flex gap-2 mt-1" data-testid="gallery-dots">
          {items.map((_, idx) => (
            <span
              key={idx}
              data-testid={`gallery-dot-${idx}`}
              className="rounded-full w-1.5 h-1.5"
              style={{
                backgroundColor:
                  idx === currentIndex ? 'rgba(255,183,77,0.6)' : 'rgba(255,255,255,0.15)',
                transition: 'background-color 1500ms ease-in-out',
              }}
            />
          ))}
        </div>
      </div>

      {/* Hint — top-right, very subtle */}
      <p
        className="absolute top-4 right-6 z-10 text-[9px] tracking-[0.2em] font-display"
        style={{ color: 'rgba(255,255,255,0.12)' }}
      >
        Wave to interact
      </p>
    </div>
  );
}
