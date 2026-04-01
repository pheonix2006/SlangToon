import { render, screen } from '@testing-library/react';
import PosterDisplay from './PosterDisplay';

const defaultProps = {
  posterUrl: 'https://example.com/poster.png',
};

describe('PosterDisplay', () => {
  it('displays poster image with alt "生成的海报"', () => {
    render(<PosterDisplay {...defaultProps} />);

    const img = screen.getByAltText('生成的海报');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'https://example.com/poster.png');
  });

  it('shows download/save button "保存下载"', () => {
    render(<PosterDisplay {...defaultProps} />);

    expect(screen.getByText('保存下载')).toBeInTheDocument();
  });

  it('shows action buttons when callbacks provided', () => {
    render(
      <PosterDisplay
        {...defaultProps}
        onRegenerate={vi.fn()}
        onRetake={vi.fn()}
        onGoToHistory={vi.fn()}
      />,
    );

    expect(screen.getByText('重新生成')).toBeInTheDocument();
    expect(screen.getByText('重新拍照')).toBeInTheDocument();
    expect(screen.getByText('历史记录')).toBeInTheDocument();
  });

  it('shows style name', () => {
    render(<PosterDisplay {...defaultProps} styleName="赛博朋克" />);

    expect(screen.getByText('赛博朋克')).toBeInTheDocument();
  });

  it('shows loading overlay "正在生成海报..."', () => {
    render(<PosterDisplay {...defaultProps} isGenerating />);

    expect(screen.getByText('正在生成海报...')).toBeInTheDocument();
  });
});
