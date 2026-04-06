import GlassButton from '../GlassButton';

interface ComicDisplayProps {
  comicUrl: string;
  slang: string;
  onNew: () => void;
}

export default function ComicDisplay({ comicUrl, slang, onNew }: ComicDisplayProps) {
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = comicUrl;
    link.download = `slangtoon-${slang.replace(/\s+/g, '-').toLowerCase()}.png`;
    link.click();
  };

  return (
    <div className="w-full max-w-4xl px-6 py-6">
      {/* Slang title */}
      <h2
        className="text-xl italic font-accent text-center mb-5"
        style={{ color: '#FFF3E0' }}
      >
        &ldquo;{slang}&rdquo;
      </h2>

      {/* Comic image */}
      <div className="rounded-xl overflow-hidden gold-border gold-glow">
        <img
          src={comicUrl}
          alt={`Comic strip for "${slang}"`}
          className="w-full h-auto"
        />
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 justify-center mt-6">
        <GlassButton onClick={handleDownload}>
          Download
        </GlassButton>
        <GlassButton variant="secondary" onClick={onNew}>
          New Slang
        </GlassButton>
      </div>
    </div>
  );
}
