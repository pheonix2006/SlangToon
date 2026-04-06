import { render, screen } from '@testing-library/react';
import LoadingOrb from './LoadingOrb';

describe('LoadingOrb', () => {
  it('renders the gold ring element', () => {
    const { container } = render(<LoadingOrb />);
    const ring = container.querySelector('[data-testid="orb-ring"]');
    expect(ring).toBeInTheDocument();
  });

  it('renders the center dot', () => {
    const { container } = render(<LoadingOrb />);
    const dot = container.querySelector('[data-testid="orb-dot"]');
    expect(dot).toBeInTheDocument();
  });

  it('renders label text when provided', () => {
    render(<LoadingOrb label="CREATING" subtext="寻找一个有趣的俚语..." />);
    expect(screen.getByText('CREATING')).toBeInTheDocument();
    expect(screen.getByText('寻找一个有趣的俚语...')).toBeInTheDocument();
  });

  it('does not render text when not provided', () => {
    const { container } = render(<LoadingOrb />);
    expect(container.querySelector('p')).not.toBeInTheDocument();
  });
});
