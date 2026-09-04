/**
 * The two documents the product shipped without.
 *
 * These tests exist to stop the page quietly turning into boilerplate. A
 * privacy policy that claims a review nobody performed, or that drops the
 * paragraph about applicants under 18, is worse than the empty screen it
 * replaced.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { LegalScreen } from './LegalScreen';

describe('privacy and terms', () => {
  it('says up front that a lawyer has not reviewed them', () => {
    render(<LegalScreen />);
    expect(screen.getByTestId('legal-draft')).toHaveTextContent('not reviewed by a lawyer');
  });

  it('does not hide that the product will be used by minors', () => {
    render(<LegalScreen />);
    const page = screen.getByText(/Applicants under 18/).closest('p');
    expect(page).toHaveTextContent('does not currently ask for age');
    expect(page).toHaveTextContent('a gap a legal review has to close');
  });

  it('repeats the promise the rest of the product is built on', () => {
    render(<LegalScreen />);
    expect(screen.getByText(/never predicts/)).toBeInTheDocument();
    expect(screen.getByText(/shown as\s+unknown/)).toBeInTheDocument();
  });

  it('names what is stored rather than gesturing at "your data"', () => {
    render(<LegalScreen />);
    const stored = screen.getByText(/What is stored/).closest('p');
    expect(stored).toHaveTextContent('citizenship');
    expect(stored).toHaveTextContent('the date it was read');
  });
});
