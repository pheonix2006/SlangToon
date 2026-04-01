import { render, screen } from '@testing-library/react';
import Countdown from './Countdown';

describe('Countdown', () => {
  it('displays the remaining number', () => {
    render(<Countdown remaining={3} />);

    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders nothing when remaining is 0', () => {
    const { container } = render(<Countdown remaining={0} />);

    expect(container.innerHTML).toBe('');
  });

  it('renders nothing when remaining is negative', () => {
    const { container } = render(<Countdown remaining={-1} />);

    expect(container.innerHTML).toBe('');
  });
});
