import { useEffect, useRef } from 'react';

interface ThinkingDisplayProps {
  text: string;
  isActive: boolean;
}

export default function ThinkingDisplay({ text, isActive }: ThinkingDisplayProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [text]);

  if (!text) return null;

  return (
    <div
      className={`w-full mt-6 px-8 transition-opacity duration-500 ${
        isActive ? 'opacity-100' : 'opacity-0'
      }`}
    >
      <div
        ref={containerRef}
        className="max-h-[55vh] overflow-y-auto px-6 py-4 rounded-xl text-base font-mono leading-relaxed"
        style={{
          color: 'rgba(255,255,255,0.4)',
          backgroundColor: 'rgba(255,255,255,0.03)',
          scrollbarWidth: 'none',
        }}
      >
        {text}
        {isActive && (
          <span
            className="inline-block w-[2px] h-[1em] ml-[2px] align-middle"
            style={{
              backgroundColor: 'rgba(255,183,77,0.6)',
              animation: 'blink 1s step-end infinite',
            }}
          />
        )}
      </div>
    </div>
  );
}
