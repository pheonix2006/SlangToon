import { useState, useEffect } from 'react';

interface ComicDisplayProps {
  comicUrl: string;
  slang: string;
  explanation?: string;
}

export default function ComicDisplay({ comicUrl, slang, explanation }: ComicDisplayProps) {
  const [labelVisible, setLabelVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLabelVisible(false), 5000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black">
      <img
        src={comicUrl}
        alt={`Comic strip for "${slang}"`}
        className="max-w-full max-h-full object-contain"
      />
      {/* Bottom gradient for label readability */}
      <div
        className="absolute bottom-0 left-0 right-0 h-32 pointer-events-none"
        style={{ background: 'linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%)' }}
      />
      <div
        data-testid="comic-label"
        className="absolute bottom-8 left-8 right-8 transition-opacity duration-1000"
        style={{ opacity: labelVisible ? 1 : 0 }}
      >
        <p
          className="text-xs tracking-[0.2em] uppercase font-display"
          style={{ color: 'rgba(255,183,77,0.4)' }}
        >
          &ldquo;{slang}&rdquo;
        </p>
        {explanation && (
          <p
            className="text-sm mt-1 leading-relaxed"
            style={{ color: 'rgba(255,255,255,0.5)' }}
          >
            {explanation}
          </p>
        )}
      </div>
    </div>
  );
}
