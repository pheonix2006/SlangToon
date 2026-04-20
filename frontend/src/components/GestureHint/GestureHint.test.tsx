import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import GestureHint from './GestureHint';
import { AppState } from '../../types';

describe('GestureHint', () => {
  it('shows ok hint for CAMERA_READY', () => {
    render(<GestureHint appState={AppState.CAMERA_READY} />);
    expect(screen.getByText(/👌/)).toBeInTheDocument();
    expect(screen.getByText(/Generate/)).toBeInTheDocument();
  });

  it('shows ok and palm hints for SCRIPT_PREVIEW', () => {
    render(<GestureHint appState={AppState.SCRIPT_PREVIEW} />);
    expect(screen.getByText(/👌/)).toBeInTheDocument();
    expect(screen.getByText(/🖐️/)).toBeInTheDocument();
  });

  it('shows ok hint for COMIC_READY', () => {
    render(<GestureHint appState={AppState.COMIC_READY} />);
    expect(screen.getByText(/👌/)).toBeInTheDocument();
    expect(screen.getByText(/New Slang/)).toBeInTheDocument();
  });

  it('renders nothing for locked states', () => {
    const { container } = render(<GestureHint appState={AppState.SCRIPT_LOADING} />);
    expect(container.textContent).toBe('');
  });

  it('renders nothing for GALLERY', () => {
    const { container } = render(<GestureHint appState={AppState.GALLERY} />);
    expect(container.textContent).toBe('');
  });
});
