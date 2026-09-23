/**
 * Component-level guarantees.
 *
 * Two rules the UI must never break: a status chip always carries its full
 * meaning even when the label is shortened, and a fixture source is never
 * rendered as a clickable external link.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Chip, Notice, SourceLink, StatusChip, isSafeHref } from './primitives';
import { STATUS_MEANING, fundingClassTone } from '@/lib/format';

describe('StatusChip', () => {
  it('shows the shortened label but keeps the full meaning available', () => {
    render(<StatusChip status="FULL_RIDE_CONFIRMED" tone={fundingClassTone.FULL_RIDE_CONFIRMED} />);
    const chip = screen.getByText('Full ride');
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute('title', STATUS_MEANING.FULL_RIDE_CONFIRMED);
  });

  it('falls back to the humanised name for a status with no short label', () => {
    render(<StatusChip status="MET" tone="ok" />);
    expect(screen.getByText('Met')).toBeInTheDocument();
  });

  it('explains that a full ride is not a promise of an award', () => {
    render(<StatusChip status="CONFIRMED_OPPORTUNITY" tone="ok" />);
    expect(screen.getByText('Confirmed')).toHaveAttribute(
      'title',
      expect.stringContaining('decision still rests with the university'),
    );
  });
});

describe('SourceLink', () => {
  it('renders a real source as an external link that cannot hijack the opener', () => {
    render(<SourceLink url="https://www.rug.nl/education" />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', 'https://www.rug.nl/education');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('never renders a bundled demo page as a link', () => {
    render(<SourceLink url="fixture://u-groningen/costs.html" />);
    expect(screen.queryByRole('link')).toBeNull();
    expect(screen.getByText('demo fixture')).toBeInTheDocument();
  });

  /**
   * Every URL here was read off a third-party page by the crawler, and React
   * does not refuse a `javascript:` href - it warns in development and renders
   * it anyway. A source that is not a web address is shown as text.
   */
  it.each([
    'javascript:alert(document.cookie)',
    'JavaScript:alert(1)',
    'data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==',
    'vbscript:msgbox(1)',
  ])('never renders %s as a link', (url) => {
    render(<SourceLink url={url} />);
    expect(screen.queryByRole('link')).toBeNull();
    expect(screen.getByText('not a web link')).toBeInTheDocument();
  });
});

describe('isSafeHref', () => {
  it('accepts the two schemes a published source can have', () => {
    expect(isSafeHref('https://www.rug.nl/education')).toBe(true);
    expect(isSafeHref('http://www.rug.nl/education')).toBe(true);
  });

  it('rejects script-bearing and unparseable URLs', () => {
    expect(isSafeHref('javascript:alert(1)')).toBe(false);
    expect(isSafeHref('data:text/html,<script>alert(1)</script>')).toBe(false);
    expect(isSafeHref('fixture://demo/page.html')).toBe(false);
    expect(isSafeHref('')).toBe(false);
  });
});

describe('Chip', () => {
  it('applies the tone class so status colour is not decorative', () => {
    const { container } = render(<Chip tone="risk">Gap</Chip>);
    expect(container.firstChild).toHaveClass('chip--risk');
  });
});

describe('Notice', () => {
  it('is announced as a note to assistive technology', () => {
    render(<Notice kind="warn">Careful</Notice>);
    expect(screen.getByRole('note')).toHaveTextContent('Careful');
  });
});
