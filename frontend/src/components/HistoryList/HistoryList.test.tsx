import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HistoryList from './HistoryList';
import type { HistoryItem } from '../../types';

const mockItems: HistoryItem[] = [
  {
    id: '1',
    style_name: '赛博朋克',
    prompt: 'cyberpunk style',
    poster_url: 'https://example.com/poster1.png',
    thumbnail_url: 'https://example.com/thumb1.png',
    photo_url: 'https://example.com/photo1.jpg',
    created_at: '2026-03-28T10:00:00Z',
  },
  {
    id: '2',
    style_name: '水墨画',
    prompt: 'ink painting style',
    poster_url: 'https://example.com/poster2.png',
    thumbnail_url: 'https://example.com/thumb2.png',
    photo_url: 'https://example.com/photo2.jpg',
    created_at: '2026-03-27T08:00:00Z',
  },
];

const defaultProps = {
  items: mockItems,
};

describe('HistoryList', () => {
  it('shows empty state "暂无历史记录"', () => {
    render(<HistoryList items={[]} />);

    expect(screen.getByText('暂无历史记录')).toBeInTheDocument();
  });

  it('renders history items with style names', () => {
    render(<HistoryList {...defaultProps} />);

    expect(screen.getByText('赛博朋克')).toBeInTheDocument();
    expect(screen.getByText('水墨画')).toBeInTheDocument();
  });

  it('shows detail view on item click with "返回列表" button', async () => {
    const user = userEvent.setup();
    render(<HistoryList {...defaultProps} />);

    await user.click(screen.getByAltText('赛博朋克'));

    expect(screen.getByText('返回列表')).toBeInTheDocument();
    expect(screen.getByAltText('海报')).toBeInTheDocument();
  });

  it('returns to list on back button click', async () => {
    const user = userEvent.setup();
    render(<HistoryList {...defaultProps} />);

    await user.click(screen.getByAltText('赛博朋克'));
    expect(screen.getByText('返回列表')).toBeInTheDocument();

    await user.click(screen.getByText('返回列表'));
    expect(screen.queryByText('返回列表')).not.toBeInTheDocument();
    expect(screen.getByText('赛博朋克')).toBeInTheDocument();
  });
});
