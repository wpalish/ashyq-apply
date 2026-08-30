/**
 * Component-level guarantees.
 *
 * Two rules the UI must never break: a status chip always carries its full
 * meaning even when the label is shortened, and a fixture source is never
 * rendered as a clickable external link.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Chip, Notice, Panel, SourceLink, StatusChip } from './primitives';
import { STATUS_MEANING, fundingClassTone } from '@/lib/format';

describe('StatusChip', () => {
  it('shows the shortened label but keeps the full meaning available', () => {
    render(<StatusChip status="FULL_RIDE_CONFIRMED" tone={fundingClassTone.FULL_RIDE_CONFIRMED} />);
    // "Core costs covered", not "Full ride": the award covers the four core
    // categories, and a university that also publishes insurance, books or
    // travel leaves a real amount to pay. The old label claimed more than the
    // award did, which is the half a student remembers.
    const chip = screen.getByText('Core costs covered');
    expect(chip).toBeInTheDocument();
    expect(chip).toHaveAttribute('title', STATUS_MEANING.FULL_RIDE_CONFIRMED);
    // The meaning must say what is *not* covered, not only what is.
    expect(STATUS_MEANING.FULL_RIDE_CONFIRMED).toMatch(/still yours to pay/);
    expect(STATUS_MEANING.FULL_RIDE_CONFIRMED).toMatch(/not the same as being awarded/);
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

describe('a collapsible Panel', () => {
  /**
   * The applicant form is ten panels and about forty fields. Most of them —
   * subject grades, curriculum results, activities, achievements — are lists
   * that are empty for a first-time applicant, and showing them all open makes
   * the required fields hard to find. They fold, and say what they hold.
   */
  it('folds away when it has nothing in it', () => {
    render(<Panel title="Achievements" collapsible summary="none added">{'x'}</Panel>);
    const disclosure = screen.getByRole('group');
    expect(disclosure).not.toHaveAttribute('open');
    expect(screen.getByText(/none added/)).toBeInTheDocument();
  });

  it('starts open when it already holds something', () => {
    render(
      <Panel title="Achievements" collapsible defaultOpen summary="2 added">{'x'}</Panel>,
    );
    expect(screen.getByRole('group')).toHaveAttribute('open');
  });

  it('is still a plain section when it is not collapsible', () => {
    render(<Panel title="Grades">{'x'}</Panel>);
    expect(screen.queryByRole('group')).not.toBeInTheDocument();
    expect(screen.getByText('Grades')).toBeInTheDocument();
  });
});
