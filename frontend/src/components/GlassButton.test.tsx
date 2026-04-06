import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GlassButton from './GlassButton';

describe('GlassButton', () => {
  it('renders with primary variant styles', () => {
    render(<GlassButton>Click</GlassButton>);
    const btn = screen.getByRole('button', { name: 'Click' });
    expect(btn).toBeInTheDocument();
    expect(btn.className).toContain('rounded-full');
  });

  it('calls onClick when clicked', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<GlassButton onClick={onClick}>Go</GlassButton>);
    await user.click(screen.getByRole('button', { name: 'Go' }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('applies disabled styles when disabled', () => {
    render(<GlassButton disabled>Disabled</GlassButton>);
    const btn = screen.getByRole('button', { name: 'Disabled' });
    expect(btn).toBeDisabled();
    expect(btn.className).toContain('opacity-30');
  });

  it('applies secondary variant styles', () => {
    render(<GlassButton variant="secondary">Secondary</GlassButton>);
    const btn = screen.getByRole('button', { name: 'Secondary' });
    expect(btn).toBeInTheDocument();
  });
});
