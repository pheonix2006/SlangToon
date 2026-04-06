import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HistoryList from './HistoryList';
import type { HistoryItem } from '../../types';

const mockItems: HistoryItem[] = [
  {
    id: '1',
    slang: 'Slay',
    origin: 'African American Vernacular English',
    explanation: 'To do something exceptionally well',
    panel_count: 4,
    comic_url: 'https://example.com/comic1.png',
    thumbnail_url: 'https://example.com/thumb1.png',
    comic_prompt: 'A comic about slaying...',
    created_at: '2026-03-28T10:00:00Z',
  },
  {
    id: '2',
    slang: 'No cap',
    origin: 'Atlanta hip-hop scene',
    explanation: 'No lie, telling the truth',
    panel_count: 3,
    comic_url: 'https://example.com/comic2.png',
    thumbnail_url: 'https://example.com/thumb2.png',
    comic_prompt: 'A comic about no cap...',
    created_at: '2026-03-27T08:00:00Z',
  },
];

describe('HistoryList', () => {
  it('shows empty state "No history yet"', () => {
    render(<HistoryList items={[]} />);
    expect(screen.getByText('No history yet')).toBeInTheDocument();
  });

  it('renders history items with slang names', () => {
    render(<HistoryList items={mockItems} />);
    expect(screen.getByText(/\u201CSlay\u201D/)).toBeInTheDocument();
    expect(screen.getByText(/\u201CNo cap\u201D/)).toBeInTheDocument();
  });

  it('shows detail view on item click with back button', async () => {
    const user = userEvent.setup();
    render(<HistoryList items={mockItems} />);

    await user.click(screen.getByAltText('Slay'));
    expect(screen.getByText(/Back to list/)).toBeInTheDocument();
    expect(screen.getByAltText(/Comic for/)).toBeInTheDocument();
  });

  it('returns to list on back button click', async () => {
    const user = userEvent.setup();
    render(<HistoryList items={mockItems} />);

    await user.click(screen.getByAltText('Slay'));
    expect(screen.getByText(/Back to list/)).toBeInTheDocument();

    await user.click(screen.getByText(/Back to list/));
    expect(screen.queryByText(/Back to list/)).not.toBeInTheDocument();
  });
});
