/**
 * The globe component: markers for the programmes on the near side, a click
 * that opens the programme, and a caption - the markers themselves stay out
 * of the keyboard and screen-reader path, because every one is a card below.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Globe } from './Globe';

const markers = [
  { id: 'groningen', lat: 53.22, lon: 6.57, label: 'Groningen · 1,848 USD a year' },
  { id: 'toronto', lat: 43.65, lon: -79.38, label: 'Toronto · cost not computed' },
];

describe('the globe', () => {
  it('shows markers only for cities on the near side', () => {
    // Seen from over Central Asia, Groningen is in view and Toronto is behind.
    render(
      <Globe markers={markers} focus={{ lat: 40, lon: 60 }} tone="day" layout="band" height={230} caption="c" />,
    );
    expect(screen.getByTestId('globe-marker-groningen')).toBeInTheDocument();
    expect(screen.queryByTestId('globe-marker-toronto')).toBeNull();
  });

  it('opens the programme a marker stands for, and labels the selected one', () => {
    const onSelect = vi.fn();
    render(
      <Globe markers={markers} focus={{ lat: 48, lon: 14 }} tone="day" layout="band" height={230}
             selected="groningen" onSelect={onSelect} caption="c" />,
    );
    fireEvent.click(screen.getByTestId('globe-marker-groningen'));
    expect(onSelect).toHaveBeenCalledWith('groningen');
    expect(screen.getByText('Groningen · 1,848 USD a year')).toBeInTheDocument();
  });

  it('keeps its markers out of the tab order and says what it shows', () => {
    const { container } = render(
      <Globe markers={markers} focus={{ lat: 48, lon: 14 }} tone="night" layout="horizon" height={220}
             caption="A globe with 2 programmes" />,
    );
    expect(screen.getByText('A globe with 2 programmes')).toBeInTheDocument();
    for (const button of container.querySelectorAll('button')) {
      expect(button).toHaveAttribute('tabindex', '-1');
    }
    expect(container.querySelector('.globe__markers')).toHaveAttribute('aria-hidden', 'true');
  });
});
