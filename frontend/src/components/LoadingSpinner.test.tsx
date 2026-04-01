import { render, screen } from '@testing-library/react';
import LoadingSpinner from './LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders with default size and animate-spin class', () => {
    const { container } = render(<LoadingSpinner />);

    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
    expect(spinner!.className).toContain('h-10');
    expect(spinner!.className).toContain('w-10');
  });

  it('applies sm size classes', () => {
    const { container } = render(<LoadingSpinner size="sm" />);

    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
    expect(spinner!.className).toContain('h-6');
    expect(spinner!.className).toContain('w-6');
  });

  it('applies lg size classes', () => {
    const { container } = render(<LoadingSpinner size="lg" />);

    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
    expect(spinner!.className).toContain('h-16');
    expect(spinner!.className).toContain('w-16');
  });

  it('displays optional text', () => {
    render(<LoadingSpinner text="加载中..." />);

    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('does not display text when not provided', () => {
    const { container } = render(<LoadingSpinner />);

    expect(container.querySelector('p')).not.toBeInTheDocument();
  });
});
