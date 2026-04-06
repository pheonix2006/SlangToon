import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ErrorDisplay from './ErrorDisplay';

describe('ErrorDisplay', () => {
  it('displays the error message', () => {
    render(<ErrorDisplay message="网络连接失败" />);
    expect(screen.getByText('网络连接失败')).toBeInTheDocument();
  });

  it('shows retry button with default text when onRetry is provided', () => {
    render(<ErrorDisplay message="出错了" onRetry={() => {}} />);
    const button = screen.getByRole('button', { name: 'Retry' });
    expect(button).toBeInTheDocument();
  });

  it('hides retry button when onRetry is not provided', () => {
    render(<ErrorDisplay message="出错了" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<ErrorDisplay message="出错了" onRetry={onRetry} />);
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
