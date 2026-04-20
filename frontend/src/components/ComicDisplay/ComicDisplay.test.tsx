import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ComicDisplay from './ComicDisplay';

describe('ComicDisplay (gesture-only)', () => {
  it('renders slang title', () => {
    render(<ComicDisplay comicUrl="/test.png" slang="No cap" />);
    expect(screen.getByText(/No cap/)).toBeInTheDocument();
  });

  it('renders comic image with correct src', () => {
    render(<ComicDisplay comicUrl="/test.png" slang="No cap" />);
    const img = screen.getByAltText(/Comic strip for "No cap"/);
    expect(img).toHaveAttribute('src', '/test.png');
  });

  it('has no buttons', () => {
    const { container } = render(<ComicDisplay comicUrl="/test.png" slang="No cap" />);
    expect(container.querySelectorAll('button')).toHaveLength(0);
  });
});
