import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ScriptPreview from './ScriptPreview';
import type { ScriptData } from '../../types';

const mockData: ScriptData = {
  slang: 'No cap',
  origin: 'Gen Z slang',
  explanation: 'For real, not lying',
  panel_count: 2,
  panels: [
    { scene: 'A student in class', dialogue: 'No cap, this test is easy' },
    { scene: 'Gets the results', dialogue: '' },
  ],
};

describe('ScriptPreview (gesture-only)', () => {
  it('renders slang title', () => {
    render(<ScriptPreview data={mockData} />);
    expect(screen.getByRole('heading', { name: /No cap/ })).toBeInTheDocument();
  });

  it('renders origin and explanation', () => {
    render(<ScriptPreview data={mockData} />);
    expect(screen.getByText(/Gen Z slang/)).toBeInTheDocument();
  });

  it('renders all panels', () => {
    render(<ScriptPreview data={mockData} />);
    expect(screen.getByText('PANEL 1')).toBeInTheDocument();
    expect(screen.getByText('PANEL 2')).toBeInTheDocument();
  });

  it('renders panel scene text', () => {
    render(<ScriptPreview data={mockData} />);
    expect(screen.getByText('A student in class')).toBeInTheDocument();
  });

  it('renders panel dialogue when present', () => {
    render(<ScriptPreview data={mockData} />);
    expect(screen.getByText(/No cap, this test is easy/)).toBeInTheDocument();
  });

  it('has no buttons', () => {
    const { container } = render(<ScriptPreview data={mockData} />);
    expect(container.querySelectorAll('button')).toHaveLength(0);
  });
});
