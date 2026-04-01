import type { StyleOption } from '../../types';
import StyleCard from '../StyleCard/StyleCard';
import LoadingSpinner from '../LoadingSpinner';
import ErrorDisplay from '../ErrorDisplay';

interface StyleSelectionProps {
  styles: StyleOption[];
  selectedStyle: StyleOption | null;
  onSelectStyle: (style: StyleOption) => void;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  photoThumbnail?: string;
}

export default function StyleSelection({
  styles,
  selectedStyle,
  onSelectStyle,
  isLoading = false,
  error = null,
  onRetry,
  photoThumbnail,
}: StyleSelectionProps) {

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <LoadingSpinner size="lg" text="正在分析照片..." />
        {photoThumbnail && (
          <img
            src={`data:image/jpeg;base64,${photoThumbnail}`}
            alt="已拍摄照片"
            className="w-32 h-32 rounded-lg object-cover opacity-60"
          />
        )}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <ErrorDisplay message={error} onRetry={onRetry} />
      </div>
    );
  }

  if (styles.length === 0) {
    return (
      <div className="flex items-center justify-center py-16">
        <p className="text-gray-500">暂无可用风格</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Heading */}
      <h2 className="text-2xl font-bold text-white text-center">
        选择你喜欢的风格
      </h2>

      {/* Optional photo thumbnail */}
      {photoThumbnail && (
        <div className="flex justify-center">
          <img
            src={`data:image/jpeg;base64,${photoThumbnail}`}
            alt="已拍摄照片"
            className="w-24 h-24 rounded-lg object-cover border-2 border-gray-600"
          />
        </div>
      )}

      {/* Style cards grid - 3 columns */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {styles.map((style) => (
          <StyleCard
            key={style.name}
            style={style}
            isSelected={selectedStyle?.name === style.name}
            onSelect={onSelectStyle}
          />
        ))}
      </div>

    </div>
  );
}
