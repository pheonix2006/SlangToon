interface PageTransitionProps {
  children: React.ReactNode;
}

export default function PageTransition({ children }: PageTransitionProps) {
  return (
    <div
      style={{
        animation: 'fade-scale-in 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      }}
    >
      {children}
    </div>
  );
}
