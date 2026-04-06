import GlassButton from './GlassButton';

interface ErrorDisplayProps {
  message: string;
  onRetry?: () => void;
  retryText?: string;
}

export default function ErrorDisplay({
  message,
  onRetry,
  retryText = 'Retry',
}: ErrorDisplayProps) {
  return (
    <div className="flex flex-col items-center gap-5 text-center px-4" style={{ animation: 'fade-scale-in 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards' }}>
      {/* Gold ring with exclamation */}
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center"
        style={{ border: '1.5px solid rgba(255,183,77,0.3)' }}
      >
        <span className="text-lg" style={{ color: 'rgba(255,183,77,0.6)' }}>!</span>
      </div>
      <p className="text-sm max-w-md" style={{ color: 'rgba(255,255,255,0.6)' }}>
        {message}
      </p>
      {onRetry && (
        <GlassButton onClick={onRetry}>
          {retryText}
        </GlassButton>
      )}
    </div>
  );
}
