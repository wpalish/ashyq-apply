import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { Loading, SaveFeedback } from './primitives';
it('exposes the loading label as an atomic polite status and hides decorative motion from assistive technology', () => {
  render(<Loading label="Loading conversations…" />);
  expect(screen.getByRole('status')).toHaveTextContent('Loading conversations…');
  expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  expect(screen.getByRole('status')).toHaveAttribute('aria-atomic', 'true');
  expect(screen.getByRole('status').querySelector('.spinner')).toHaveAttribute('aria-hidden', 'true');
});
it('a failed operation takes priority over a previous saved acknowledgement', () => {
  render(<SaveFeedback saving={false} saved dirty={false} failed />);
  expect(screen.getByRole('status')).toHaveTextContent('Not saved');
  expect(screen.getByRole('status')).not.toHaveTextContent(/^Saved$/);
});
