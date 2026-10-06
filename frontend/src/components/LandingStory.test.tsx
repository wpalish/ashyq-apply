/**
 * The landing story without a canvas (jsdom): the words still read, in
 * order, and say nothing the product does not stand behind.
 */

import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { LandingStory, STILL } from '@/components/LandingStory';

describe('LandingStory', () => {
  it('reads as one story, question first, in order', () => {
    render(<LandingStory />);
    const headings = screen.getAllByRole('heading').map((h) => h.textContent);
    expect(headings).toEqual([
      'Where can you study — and what will it cost?',
      'From Astana to 15 countries',
      "One card per programme, in its country's colour",
      'What is left to pay — and the word if stays',
      'Three answers, never one score',
    ]);
    expect(screen.getByRole('heading', { level: 1 })).toHaveAttribute('id', 'landing-title');
  });

  it('labels its example as demo data and keeps "if awarded" and the source', () => {
    const { container } = render(<LandingStory />);
    const story = screen.getByTestId('landing-story');
    expect(story).toHaveTextContent('Example · demo data');
    expect(story).toHaveTextContent('if the grant is awarded');
    expect(story).toHaveTextContent('rug.nl · demo fixture · read Oct 05');
    expect(story).toHaveTextContent('In the demo run, 20 programmes');
    // A grant awarded by selection is not a full ride, with money still left to pay.
    expect(story).not.toHaveTextContent(/full ride/i);
    expect(container.textContent).not.toMatch(/%|chance|probab/i);
    // The pass's own figure changes with the scroll; the lines under it are the ones read out.
    expect(container.querySelector('[data-ls="big"]')?.closest('[aria-hidden="true"]')).not.toBeNull();
  });

  it('hides the two passes behind from assistive tech, not the one opened', () => {
    const { container } = render(<LandingStory />);
    expect(container.querySelector('[data-ls="pass-jp"]')).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelector('[data-ls="pass-be"]')).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelector('[data-ls="pass-nl"]')).not.toHaveAttribute('aria-hidden');
  });

  it('opens sign-up from the way in', () => {
    render(<LandingStory />);
    const story = screen.getByTestId('landing-story');
    expect(within(story).getByRole('link', { name: /Start with your profile/ })).toHaveAttribute('href', '#/sign-in?create=1');
  });

  it('stands still under reduced motion', () => {
    expect(STILL).toContain('prefers-reduced-motion: reduce');
  });
});
