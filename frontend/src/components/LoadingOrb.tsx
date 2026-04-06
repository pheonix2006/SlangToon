interface LoadingOrbProps {
  label?: string;
  subtext?: string;
}

export default function LoadingOrb({ label, subtext }: LoadingOrbProps) {
  return (
    <div className="flex flex-col items-center gap-6">
      {/* Outer ring (decorative) */}
      <div className="relative">
        <div
          className="absolute inset-[-8px] rounded-full border"
          style={{ borderColor: 'rgba(255,183,77,0.1)' }}
        />
        {/* Spinning ring */}
        <div
          data-testid="orb-ring"
          className="w-20 h-20 rounded-full border-2"
          style={{
            borderColor: 'rgba(255,183,77,0.3)',
            borderTopColor: '#FFB74D',
            animation: 'spin-gold-ring 1.5s linear infinite',
          }}
        />
        {/* Center pulsing dot */}
        <div
          data-testid="orb-dot"
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full"
          style={{
            backgroundColor: '#FFB74D',
            boxShadow: '0 0 20px rgba(255,183,77,0.6)',
            animation: 'orb-pulse 2s ease-in-out infinite',
          }}
        />
      </div>
      {label && (
        <div className="text-center">
          <p
            className="text-xs tracking-[0.2em] font-display"
            style={{ color: 'rgba(255,183,77,0.5)' }}
          >
            {label}
          </p>
          {subtext && (
            <p className="text-[11px] mt-1" style={{ color: 'rgba(255,255,255,0.3)' }}>
              {subtext}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
