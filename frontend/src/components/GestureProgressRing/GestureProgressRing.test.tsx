import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import GestureProgressRing from './GestureProgressRing';

describe('GestureProgressRing', () => {
  it('renders nothing when gesture is null', () => {
    const { container } = render(
      <GestureProgressRing gesture={null} progress={0} label="" />,
    );
    expect(container.querySelector('svg')).toBeNull();
  });

  it('renders SVG ring when gesture is active', () => {
    const { container } = render(
      <GestureProgressRing gesture="ok" progress={0.5} label="Generate" />,
    );
    expect(container.querySelector('svg')).not.toBeNull();
  });

  it('displays the label text', () => {
    render(
      <GestureProgressRing gesture="ok" progress={0.5} label="Generate" />,
    );
    expect(screen.getByText('Generate')).toBeInTheDocument();
  });

  it('displays gesture emoji for ok', () => {
    render(
      <GestureProgressRing gesture="ok" progress={0.3} label="Test" />,
    );
    expect(screen.getByText('👌')).toBeInTheDocument();
  });

  it('displays gesture emoji for open_palm', () => {
    render(
      <GestureProgressRing gesture="open_palm" progress={0.3} label="Test" />,
    );
    expect(screen.getByText('🖐️')).toBeInTheDocument();
  });

  it('applies completion style at progress=1', () => {
    const { container } = render(
      <GestureProgressRing gesture="ok" progress={1} label="Done" />,
    );
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.className).toContain('scale-110');
  });

  it('sets correct stroke-dashoffset based on progress', () => {
    const { container } = render(
      <GestureProgressRing gesture="ok" progress={0.5} label="Test" />,
    );
    const circles = container.querySelectorAll('circle');
    const progressCircle = circles[1];
    const circumference = 2 * Math.PI * 52;
    const expectedOffset = circumference * (1 - 0.5);
    expect(progressCircle.style.strokeDashoffset).toBe(`${expectedOffset}`);
  });
});
