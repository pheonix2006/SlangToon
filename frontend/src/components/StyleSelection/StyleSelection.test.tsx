import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import StyleSelection from './StyleSelection';
import type { StyleOption } from '../../types';

const mockStyles: StyleOption[] = [
  { name: '赛博朋克', brief: '未来科技感' },
  { name: '水墨画', brief: '中国古典风格' },
  { name: '波普艺术', brief: '流行色彩' },
];

const defaultProps = {
  styles: mockStyles,
  selectedStyle: null as StyleOption | null,
  onSelectStyle: vi.fn(),
};

describe('StyleSelection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders style cards in grid', () => {
    render(<StyleSelection {...defaultProps} />);

    expect(screen.getByText('赛博朋克')).toBeInTheDocument();
    expect(screen.getByText('水墨画')).toBeInTheDocument();
    expect(screen.getByText('波普艺术')).toBeInTheDocument();
    expect(screen.getByText('选择你喜欢的风格')).toBeInTheDocument();
  });

  it('shows loading state with "正在分析照片..."', () => {
    render(<StyleSelection {...defaultProps} isLoading />);

    expect(screen.getByText('正在分析照片...')).toBeInTheDocument();
    expect(screen.queryByText('选择你喜欢的风格')).not.toBeInTheDocument();
  });

  it('shows error state', () => {
    const onRetry = vi.fn();
    render(
      <StyleSelection {...defaultProps} error="网络连接失败" onRetry={onRetry} />,
    );

    expect(screen.getByText('网络连接失败')).toBeInTheDocument();
    expect(screen.queryByText('选择你喜欢的风格')).not.toBeInTheDocument();
  });

  it('shows empty state "暂无可用风格"', () => {
    render(<StyleSelection {...defaultProps} styles={[]} />);

    expect(screen.getByText('暂无可用风格')).toBeInTheDocument();
    expect(screen.queryByText('选择你喜欢的风格')).not.toBeInTheDocument();
  });
});
