/**
 * Optional form sections fold while empty, open when data arrives, and never
 * close on their own.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FoldPanel } from './primitives';

const details = () => screen.getByTestId('fold') as HTMLDetailsElement;

describe('a folded optional section', () => {
  it('is folded and says it is optional while empty', () => {
    render(<FoldPanel title="Achievements" hasData={false} testId="fold"><input aria-label="x" /></FoldPanel>);
    expect(details().open).toBe(false);
    expect(screen.getByText('optional')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Achievements' })).toBeInTheDocument();
  });

  it('opens by itself when data arrives, with the count', () => {
    const { rerender } = render(<FoldPanel title="Achievements" hasData={false} testId="fold">x</FoldPanel>);
    rerender(<FoldPanel title="Achievements" hasData count={2} testId="fold">x</FoldPanel>);
    expect(details().open).toBe(true);
    expect(screen.getByText('2 added')).toBeInTheDocument();
  });

  it('does not snatch the section away when the last entry is removed', () => {
    const { rerender } = render(<FoldPanel title="Achievements" hasData count={1} testId="fold">x</FoldPanel>);
    rerender(<FoldPanel title="Achievements" hasData={false} count={0} testId="fold">x</FoldPanel>);
    expect(details().open).toBe(true);
  });

  it('follows the person when they fold it', () => {
    render(<FoldPanel title="Achievements" hasData testId="fold">x</FoldPanel>);
    details().open = false;
    fireEvent(details(), new Event('toggle'));
    expect(details().open).toBe(false);
  });

  it('folds back when the whole profile is replaced by a blank one', () => {
    const { rerender } = render(
      <FoldPanel title="Achievements" hasData count={2} key="a:0" testId="fold">x</FoldPanel>,
    );
    rerender(<FoldPanel title="Achievements" hasData={false} count={0} key="a:1" testId="fold">x</FoldPanel>);
    expect(details().open).toBe(false);
    expect(screen.getByText('optional')).toBeInTheDocument();
  });

  it('stays open when the replacement also holds data', () => {
    const { rerender } = render(
      <FoldPanel title="Achievements" hasData={false} key="a:0" testId="fold">x</FoldPanel>,
    );
    rerender(<FoldPanel title="Achievements" hasData count={3} key="a:1" testId="fold">x</FoldPanel>);
    expect(details().open).toBe(true);
  });
});
