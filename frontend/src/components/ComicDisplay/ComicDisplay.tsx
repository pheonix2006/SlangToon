import { useState, useEffect } from 'react';

interface ComicDisplayProps {
  comicUrl: string;
  slang: string;
}

export default function ComicDisplay({ comicUrl, slang }: ComicDisplayProps) {
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
      <div
        data-testid="comic-label"
        className="absolute bottom-8 left-8 transition-opacity duration-1000"
        style={{ opacity: labelVisible ? 1 : 0 }}
      >
        <p
          className="text-xs tracking-[0.2em] uppercase font-display"
          style={{ color: 'rgba(255,183,77,0.4)' }}
        >
          &ldquo;{slang}&rdquo;
        </p>
      </div>
    </div>
  );
}
