import { render, screen } from '@testing-library/react';
import GestureOverlay from './GestureOverlay';
import type { GestureType } from '../../types';

describe('GestureOverlay', () => {
  it('shows "等待手势..." for none gesture', () => {
    render(<GestureOverlay gesture="none" />);

    expect(screen.getByText('等待手势...')).toBeInTheDocument();
  });

  it('shows "OK 手势已识别" for ok gesture', () => {
    render(<GestureOverlay gesture="ok" />);

    expect(screen.getByText('OK 手势已识别')).toBeInTheDocument();
  });

  it('shows "张开手掌已识别" for open_palm gesture', () => {
    render(<GestureOverlay gesture="open_palm" />);

    expect(screen.getByText('张开手掌已识别')).toBeInTheDocument();
  });

  it('displays confidence percentage for detected gestures', () => {
    render(<GestureOverlay gesture="ok" confidence={0.856} />);

    expect(screen.getByText('86%')).toBeInTheDocument();
  });

  it('hides confidence percentage for none gesture', () => {
    render(<GestureOverlay gesture="none" confidence={0.5} />);

    expect(screen.queryByText('50%')).not.toBeInTheDocument();
  });

  it('applies green styles for detected gestures', () => {
    const { container } = render(<GestureOverlay gesture="ok" />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain('bg-green-500/20');
    expect(wrapper.className).toContain('border-green-400/50');
  });

  it('applies gray styles for none gesture', () => {
    const { container } = render(<GestureOverlay gesture="none" />);

    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toContain('bg-gray-800/60');
    expect(wrapper.className).toContain('border-gray-600/50');
  });
});
