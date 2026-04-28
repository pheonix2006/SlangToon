import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import ComicDisplay from './ComicDisplay';

describe('ComicDisplay (immersive)', () => {
  it('renders comic image with correct src', () => {
    render(<ComicDisplay comicUrl="/test.png" slang="No cap" />);
    const img = screen.getByAltText(/Comic strip for "No cap"/);
    expect(img).toHaveAttribute('src', '/test.png');
  });

  it('renders slang label', () => {
    render(<ComicDisplay comicUrl="/test.png" slang="No cap" />);
    expect(screen.getByText(/No cap/)).toBeInTheDocument();
  });

  it('renders explanation when provided', () => {
    render(<ComicDisplay comicUrl="/test.png" slang="No cap" explanation="This means for real" />);
    expect(screen.getByText('This means for real')).toBeInTheDocument();
  });

  it('hides explanation when not provided', () => {
    render(<ComicDisplay comicUrl="/test.png" slang="No cap" />);
    expect(screen.queryByText(/means/)).not.toBeInTheDocument();
  });

  it('has no buttons', () => {
    const { container } = render(<ComicDisplay comicUrl="/test.png" slang="No cap" />);
    expect(container.querySelectorAll('button')).toHaveLength(0);
  });

  it('label fades out after delay', () => {
    vi.useFakeTimers();
    render(<ComicDisplay comicUrl="/test.png" slang="No cap" />);
    const label = screen.getByTestId('comic-label');
    expect(label).toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(6000); });
    expect(label).toHaveStyle({ opacity: '0' });
    vi.useRealTimers();
  });
});
