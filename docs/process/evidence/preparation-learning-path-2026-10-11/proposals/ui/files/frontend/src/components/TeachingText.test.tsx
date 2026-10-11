import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { TeachingText } from './TeachingText';
afterEach(cleanup);
describe('finite escaped original teaching text', () => {
  it('renders headings, paragraphs, numbered/bullet lists, emphasis and code without discarding the teaching words', () => {
    render(<TeachingText text={'### Find the main idea\n\nRead **every paragraph**. Keep *supporting evidence* distinct.\nCheck `x * y`.\n\n1. Identify the topic.\n2. Compare the whole paragraph.\n\n- Reject a detail-only heading.\n- Retain the stated evidence.'} />);
    expect(screen.getByRole('heading', { name: 'Find the main idea' })).toHaveProperty('tagName', 'H3');
    expect(screen.getByText('every paragraph').tagName).toBe('STRONG');
    expect(screen.getByText('supporting evidence').tagName).toBe('EM');
    expect(screen.getByText('x * y').tagName).toBe('CODE');
    const lists = screen.getAllByRole('list'); expect(lists.map(list => list.tagName)).toEqual(['OL', 'UL']);
    expect(within(lists[0]!).getAllByRole('listitem').map(item => item.textContent)).toEqual(['Identify the topic.', 'Compare the whole paragraph.']);
    expect(within(lists[1]!).getAllByRole('listitem')).toHaveLength(2);
  });
  it('contains semantic table headers and every original cell with keyboard access to its scroll region', () => {
    render(<TeachingText text={'| Quantity | Meaning |\n| --- | --- |\n| `n` | **Number** of items |\n| 36 | Recorded limit |'} />);
    const region = screen.getByRole('region', { name: 'Lesson table 1' }); expect(region).toHaveAttribute('tabindex', '0');
    expect(within(region).getAllByRole('columnheader').map(cell => cell.textContent)).toEqual(['Quantity', 'Meaning']);
    expect(within(region).getAllByRole('cell').map(cell => cell.textContent)).toEqual(['n', 'Number of items', '36', 'Recorded limit']);
    expect(within(region).getAllByRole('columnheader').every(cell => cell.getAttribute('scope') === 'col')).toBe(true);
  });
  it('never interprets HTML, URLs, links or malformed Markdown as executable markup', () => {
    const text = '<script>throw new Error("not executable")</script>\n\n<img src=x onerror=alert(1)> [external](javascript:alert(1))\n\nUnmatched **marker and `code.\n\n3 * 4 * 5';
    const { container } = render(<TeachingText text={text} />);
    expect(container.querySelectorAll('script,img,a')).toHaveLength(0);
    expect(container).toHaveTextContent('<script>throw new Error("not executable")</script>');
    expect(container).toHaveTextContent('[external](javascript:alert(1))');
    expect(container).toHaveTextContent('Unmatched **marker and `code.'); expect(container).toHaveTextContent('3 * 4 * 5');
  });
  it('keeps ordinary old introductions as paragraphs and a non-table pipe paragraph intact', () => {
    const { container } = render(<TeachingText text={'Original synthetic introduction\ncontinued line\n\nUse A | B only where the original text says so.'} />);
    expect(container.querySelectorAll('p')).toHaveLength(2); expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(container).toHaveTextContent('Original synthetic introduction'); expect(container).toHaveTextContent('continued line');
    expect(container).toHaveTextContent('Use A | B only where the original text says so.');
  });
});
