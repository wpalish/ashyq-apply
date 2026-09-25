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

  it('turns a crowd into one cluster to zoom into, and keeps pairs near their cities', () => {
    const dutch = [
      { id: 'groningen', lat: 53.22, lon: 6.57, label: 'Groningen' },
      { id: 'amsterdam', lat: 52.37, lon: 4.9, label: 'Amsterdam' },
      { id: 'delft', lat: 52.01, lon: 4.36, label: 'Delft' },
      { id: 'eindhoven', lat: 51.44, lon: 5.48, label: 'Eindhoven' },
      { id: 'leuven', lat: 50.88, lon: 4.7, label: 'Leuven' },
    ];
    const onCluster = vi.fn();
    const { container } = render(
      <Globe markers={dutch} focus={{ lat: 52, lon: 5 }} tone="day" layout="band" height={230}
             onCluster={onCluster} caption="c" />,
    );
    const cluster = screen.getByTestId('globe-cluster');
    expect(cluster).toHaveTextContent('5');
    expect(container.querySelectorAll('.globe__marker')).toHaveLength(0);
    fireEvent.click(cluster);
    expect(onCluster.mock.calls[0]![0].map((m: { id: string }) => m.id).sort()).toEqual(
      ['amsterdam', 'delft', 'eindhoven', 'groningen', 'leuven'],
    );
  });

  it('sets two touching markers apart, each within one step of its place', () => {
    const pair = [
      { id: 'toronto', lat: 43.65, lon: -79.38, label: 'Toronto' },
      { id: 'montreal', lat: 45.5, lon: -73.57, label: 'Montreal' },
    ];
    const { container } = render(
      <Globe markers={pair} focus={{ lat: 44, lon: -76 }} tone="day" layout="band" height={230} caption="c" />,
    );
    const spots = [...container.querySelectorAll<HTMLElement>('.globe__marker')]
      .map((b) => [parseFloat(b.style.left), parseFloat(b.style.top)] as const);
    expect(spots).toHaveLength(2);
    expect(Math.hypot(spots[0]![0] - spots[1]![0], spots[0]![1] - spots[1]![1])).toBeGreaterThanOrEqual(25.9);
  });
});
