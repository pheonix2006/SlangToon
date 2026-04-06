import type { ScriptData } from '../../types';
import GlassButton from '../GlassButton';

interface ScriptPreviewProps {
  data: ScriptData;
  onShuffle: () => void;
  onGenerate: () => void;
  isLoading: boolean;
}

export default function ScriptPreview({ data, onShuffle, onGenerate, isLoading }: ScriptPreviewProps) {
  return (
    <div className="w-full max-w-4xl px-6 py-6">
      {/* Slang title */}
      <div className="text-center mb-6">
        <h2
          className="text-2xl italic font-accent"
          style={{ color: '#FFF3E0' }}
        >
          &ldquo;{data.slang}&rdquo;
        </h2>
        <p
          className="text-[10px] tracking-[0.15em] mt-2 font-display"
          style={{ color: 'rgba(255,183,77,0.3)' }}
        >
          {data.origin} · {data.explanation}
        </p>
      </div>

      {/* Panels — horizontal row */}
      <div className="flex gap-3 mb-8 overflow-x-auto snap-x snap-mandatory lg:overflow-visible">
        {data.panels.map((panel, i) => (
          <div
            key={i}
            className="flex-shrink-0 w-[200px] lg:flex-1 lg:w-auto snap-start glass-panel rounded-lg p-4 flex flex-col"
          >
            <p
              className="text-[9px] tracking-[0.1em] mb-2 font-display"
              style={{ color: 'rgba(255,183,77,0.4)' }}
            >
              PANEL {i + 1}
            </p>
            <p
              className="text-[11px] leading-relaxed flex-1"
              style={{ color: 'rgba(255,255,255,0.6)' }}
            >
              {panel.scene}
            </p>
            {panel.dialogue && (
              <p
                className="text-[10px] italic mt-2 font-accent"
                style={{ color: 'rgba(255,183,77,0.7)' }}
              >
                &ldquo;{panel.dialogue}&rdquo;
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 justify-center">
        <GlassButton variant="secondary" onClick={onShuffle} disabled={isLoading}>
          Shuffle
        </GlassButton>
        <GlassButton onClick={onGenerate} disabled={isLoading}>
          Generate Comic
        </GlassButton>
      </div>
    </div>
  );
}
