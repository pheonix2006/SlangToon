import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StyleCard from './StyleCard';
import type { StyleOption } from '../../types';

const mockStyle: StyleOption = {
  name: '赛博朋克',
  brief: '未来科技感风格',
};

describe('StyleCard', () => {
  it('displays style name and brief', () => {
    render(
      <StyleCard style={mockStyle} isSelected={false} onSelect={() => {}} />,
    );

    expect(screen.getByText('赛博朋克')).toBeInTheDocument();
    expect(screen.getByText('未来科技感风格')).toBeInTheDocument();
  });

  it('shows cyan border when selected', () => {
    const { container } = render(
      <StyleCard style={mockStyle} isSelected={true} onSelect={() => {}} />,
    );

    const button = container.querySelector('button');
    expect(button!.className).toContain('border-cyan-400');
    expect(button!.className).toContain('bg-cyan-500/10');
  });

  it('does not show cyan border when not selected', () => {
    const { container } = render(
      <StyleCard style={mockStyle} isSelected={false} onSelect={() => {}} />,
    );

    const button = container.querySelector('button');
    expect(button!.className).not.toContain('border-cyan-400');
    expect(button!.className).toContain('border-gray-700');
  });

  it('calls onSelect with style when clicked', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <StyleCard style={mockStyle} isSelected={false} onSelect={onSelect} />,
    );

    await user.click(screen.getByRole('button'));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(mockStyle);
  });
});
