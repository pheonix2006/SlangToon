interface ComicDisplayProps {
  comicUrl: string;
  slang: string;
}

export default function ComicDisplay({ comicUrl, slang }: ComicDisplayProps) {
  return (
    <div className="w-full max-w-4xl px-6 py-6">
      <h2
        className="text-xl italic font-accent text-center mb-5"
        style={{ color: '#FFF3E0' }}
      >
        &ldquo;{slang}&rdquo;
      </h2>

      <div className="rounded-xl overflow-hidden gold-border gold-glow">
        <img
          src={comicUrl}
          alt={`Comic strip for "${slang}"`}
          className="w-full h-auto"
        />
      </div>
    </div>
  );
}
