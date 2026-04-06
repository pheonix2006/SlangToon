interface GlassButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
  className?: string;
}

export default function GlassButton({
  children,
  onClick,
  variant = 'primary',
  disabled = false,
  className = '',
}: GlassButtonProps) {
  const base =
    'rounded-full min-h-[44px] min-w-[44px] px-6 py-2.5 text-sm transition-all duration-200 font-display tracking-wider cursor-pointer select-none';

  const primary =
    'bg-[rgba(255,183,77,0.08)] border border-[rgba(255,183,77,0.6)] text-[#FFB74D] hover:bg-[rgba(255,183,77,0.12)] hover:-translate-y-0.5';

  const secondary =
    'bg-transparent border border-[rgba(255,183,77,0.2)] text-[rgba(255,183,77,0.5)] hover:border-[rgba(255,183,77,0.4)] hover:text-[rgba(255,183,77,0.7)] hover:-translate-y-0.5';

  const disabledClasses = 'opacity-30 cursor-not-allowed pointer-events-none';

  const variantClass = variant === 'primary' ? primary : secondary;
  const disabledClass = disabled ? disabledClasses : '';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variantClass} ${disabledClass} ${className}`}
    >
      {children}
    </button>
  );
}
