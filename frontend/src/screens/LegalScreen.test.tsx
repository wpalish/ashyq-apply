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

  it('says which part of the product is public, and what it publishes', () => {
    // The policy enumerated tenant-private storage only. A reader would have
    // concluded their data never leaves their workspace, while the community
    // shows a name, a city and every post to every other signed-in applicant.
    render(<LegalScreen />);
    const community = screen.getByText(/The community is public/).closest('p');
    expect(community).toHaveTextContent('every other signed-in applicant');
    expect(community).toHaveTextContent('including people in other workspaces');
    expect(community).toHaveTextContent('registering an account does not make it for you');
    expect(community).toHaveTextContent('Nothing from your applicant case');
  });

  it('does not forbid the feature the product ships', () => {
    // "Do not collect data about other people" read as a ban on Discover,
    // whose whole purpose is looking at other applicants' profiles.
    render(<LegalScreen />);
    const use = screen.getByText(/Acceptable use/).closest('p');
    expect(use).toHaveTextContent('Reading the community and its profiles is what they are there for');
    expect(use).toHaveTextContent('harvest');
  });

  it('says what moderation there is, and what it still cannot do', () => {
    render(<LegalScreen />);
    const posting = screen.getByText(/What you write in the community/).closest('p');
    expect(posting).toHaveTextContent('reporting button');
    // The limits stay named: no filtering, no alert, so no promise of speed.
    expect(posting).toHaveTextContent('no automated filtering');
    expect(posting).toHaveTextContent('no alert when a report arrives');
    expect(posting).toHaveTextContent('blocking is the tool that works without waiting');
  });

  it('names the picture and what is stripped from it', () => {
    render(<LegalScreen />);
    const picture = screen.getByText(/A picture, if you add one/).closest('p');
    expect(picture).toHaveTextContent('metadata is stripped');
    expect(picture).toHaveTextContent('where it was taken');
    expect(picture).toHaveTextContent('not scanned');
  });

  it('says private messages are private, and names the one exception', () => {
    render(<LegalScreen />);
    const messages = screen.getByText(/Private messages/).closest('p');
    expect(messages).toHaveTextContent('visible to nobody else');
    expect(messages).toHaveTextContent('reporting it shows that message to a moderator');
  });

  it('names what is stored rather than gesturing at "your data"', () => {
    render(<LegalScreen />);
    const stored = screen.getByText(/What is stored/).closest('p');
    expect(stored).toHaveTextContent('citizenship');
    expect(stored).toHaveTextContent('the date it was read');
  });
});
