interface ErrorDisplayProps {
  message: string;
  onRetry?: () => void;
  retryText?: string;
}

export default function ErrorDisplay({
  message,
  onRetry,
  retryText = '重试',
}: ErrorDisplayProps) {
  return (
    <div className="flex flex-col items-center gap-4 text-center px-4">
      <svg
        className="h-12 w-12 text-red-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
        />
      </svg>
      <p className="text-red-400 max-w-md">{message}</p>
      {onRetry && (
        <button
          className="px-6 py-2 bg-indigo-600 rounded hover:bg-indigo-500 transition-colors"
          onClick={onRetry}
        >
          {retryText}
        </button>
      )}
    </div>
  );
}
