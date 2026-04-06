import { render } from '@testing-library/react';
import PageTransition from './PageTransition';

describe('PageTransition', () => {
  it('renders children', () => {
    const { getByText } = render(
      <PageTransition><div>Hello</div></PageTransition>
    );
    expect(getByText('Hello')).toBeInTheDocument();
  });

  it('applies fade-scale-in animation', () => {
    const { container } = render(
      <PageTransition><div>Content</div></PageTransition>
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.style.animation).toContain('fade-scale-in');
  });
});
