export default function GlowBackground() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      {/* Main center glow */}
      <div
        data-testid="glow-main"
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full"
        style={{
          background: 'radial-gradient(circle, rgba(255,183,77,0.15) 0%, rgba(255,152,0,0.05) 35%, transparent 70%)',
          animation: 'glow-pulse 4s ease-in-out infinite',
        }}
      />
      {/* Floating orb 1 */}
      <div
        data-testid="glow-float-1"
        className="absolute w-[200px] h-[200px] rounded-full hidden lg:block"
        style={{
          top: '15%',
          right: '20%',
          background: 'radial-gradient(circle, rgba(255,183,77,0.06) 0%, transparent 70%)',
          animation: 'glow-float-1 25s linear infinite',
        }}
      />
      {/* Floating orb 2 */}
      <div
        data-testid="glow-float-2"
        className="absolute w-[250px] h-[250px] rounded-full hidden lg:block"
        style={{
          bottom: '20%',
          left: '10%',
          background: 'radial-gradient(circle, rgba(255,183,77,0.05) 0%, transparent 70%)',
          animation: 'glow-float-2 30s linear infinite',
        }}
      />
      {/* Floating orb 3 — only on 2xl */}
      <div
        data-testid="glow-float-3"
        className="absolute w-[180px] h-[180px] rounded-full hidden 2xl:block"
        style={{
          top: '60%',
          right: '35%',
          background: 'radial-gradient(circle, rgba(255,152,0,0.04) 0%, transparent 70%)',
          animation: 'glow-float-3 20s linear infinite',
        }}
      />
      {/* Ambient light — edge gradients for spatial depth */}
      <div
        data-testid="glow-ambient"
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(180deg, rgba(255,183,77,0.03) 0%, transparent 30%, transparent 70%, rgba(255,152,0,0.02) 100%)',
        }}
      />
    </div>
  );
}
