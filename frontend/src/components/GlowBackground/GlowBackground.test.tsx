import { render } from '@testing-library/react';
import GlowBackground from './GlowBackground';

describe('GlowBackground', () => {
  it('renders the main glow element', () => {
    const { container } = render(<GlowBackground />);
    const mainGlow = container.querySelector('[data-testid="glow-main"]');
    expect(mainGlow).toBeInTheDocument();
  });

  it('renders three floating orbs', () => {
    const { container } = render(<GlowBackground />);
    const orbs = container.querySelectorAll('[data-testid^="glow-float"]');
    expect(orbs).toHaveLength(3);
  });

  it('main glow has pulse animation', () => {
    const { container } = render(<GlowBackground />);
    const mainGlow = container.querySelector('[data-testid="glow-main"]') as HTMLElement;
    expect(mainGlow.style.animation).toContain('glow-pulse');
  });
});
