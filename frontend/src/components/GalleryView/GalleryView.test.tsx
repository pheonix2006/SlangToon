import { render, screen, act } from '@testing-library/react';
import GalleryView from './GalleryView';
import type { HistoryItem } from '../../types';

const mockItems: HistoryItem[] = [
  { id:'1', slang:'Carpe Diem', origin:'Latin',
    explanation:'Seize the day.', panel_count:4,
    comic_url:'/c1.png', thumbnail_url:'/t1.png',
    comic_prompt:'', created_at:'2026-04-01T10:00:00Z' },
  { id:'2', slang:'Slay', origin:'AAVE',
    explanation:'Do well.', panel_count:5,
    comic_url:'/c2.png', thumbnail_url:'/t2.png',
    comic_prompt:'', created_at:'2026-04-02T12:00:00Z' },
];

describe('GalleryView', () => {
  it('V-05: shows brand screensaver when items empty', () => {
    render(<GalleryView items={[]} />);
    expect(screen.getByText('SLANGTOON')).toBeInTheDocument();
    expect(screen.getByText(/Wave to create your first comic/)).toBeInTheDocument();
  });

  it('V-01: renders left-text right-image layout with slang info', () => {
    render(<GalleryView items={mockItems} />);
    expect(screen.getByText(/Carpe Diem/)).toBeInTheDocument();
    expect(screen.getByText('Latin')).toBeInTheDocument();
    expect(screen.getByText(/Seize the day/)).toBeInTheDocument();
    const img = screen.getByAltText(/Comic for "Carpe Diem"/);
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', '/c1.png');
  });

  it('renders top hint "Wave to interact"', () => {
    render(<GalleryView items={mockItems} />);
    expect(screen.getByText(/Wave to interact/)).toBeInTheDocument();
  });

  it('V-02: auto-advances after interval', async () => {
    vi.useFakeTimers();
    render(<GalleryView items={mockItems} intervalMs={100} />);
    expect(screen.getByText(/Carpe Diem/)).toBeInTheDocument();
    await act(async () => { vi.advanceTimersByTime(700); });
    expect(screen.getByText(/Slay/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('V-03: dot indicators count matches items', () => {
    render(<GalleryView items={mockItems} />);
    const dots = screen.getByTestId('gallery-dots');
    expect(dots.children.length).toBe(2);
  });

  it('V-06: cleans up timer on unmount', () => {
    vi.useFakeTimers();
    const { unmount } = render(<GalleryView items={mockItems} intervalMs={100} />);
    unmount();
    expect(() => vi.advanceTimersByTime(500)).not.toThrow();
    vi.useRealTimers();
  });

  it('single item does not auto-advance', () => {
    vi.useFakeTimers();
    render(<GalleryView items={[mockItems[0]]} intervalMs={50} />);
    vi.advanceTimersByTime(200);
    expect(screen.getByText(/Carpe Diem/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it('wraps around from last to first', async () => {
    vi.useFakeTimers();
    render(<GalleryView items={mockItems} intervalMs={100} />);
    await act(async () => { vi.advanceTimersByTime(700); });
    expect(screen.getByText(/Slay/)).toBeInTheDocument();
    await act(async () => { vi.advanceTimersByTime(700); });
    expect(screen.getByText(/Carpe Diem/)).toBeInTheDocument();
    vi.useRealTimers();
  });
});
