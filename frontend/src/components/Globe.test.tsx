/**
 * The globe component: markers for the programmes on the near side, a click
 * that opens the programme, and a caption - the markers themselves stay out
 * of the keyboard and screen-reader path, because every one is a card below.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { useLayoutEffect } from 'react';
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

  it('names what it hides at the edge it lies towards, by region', () => {
    // Seen from over Europe: Toronto and Montreal are behind, to the west.
    const spread = [
      { id: 'groningen', lat: 53.22, lon: 6.57, label: 'Groningen', name: 'Groningen', group: 'Europe' },
      { id: 'toronto', lat: 43.65, lon: -79.38, label: 'Toronto', name: 'Toronto', group: 'Americas' },
      { id: 'montreal', lat: 45.5, lon: -73.57, label: 'Montreal', name: 'Montreal', group: 'Americas' },
      { id: 'tokyo', lat: 35.68, lon: 139.69, label: 'Tokyo', name: 'Tokyo', group: 'Asia & Oceania' },
    ];
    const onEdge = vi.fn();
    render(
      <Globe markers={spread} focus={{ lat: 50, lon: 12 }} zoom={2.1} tone="day" layout="band" height={230}
             onEdge={onEdge} caption="c" />,
    );
    const chips = screen.getAllByTestId('globe-edge').map((c) => c.textContent);
    expect(chips).toContain('← Americas · 2');
    expect(chips).toContain('→ Tokyo');
    fireEvent.click(screen.getByText('← Americas · 2'));
    expect(onEdge.mock.calls[0]![0].map((m: { id: string }) => m.id).sort()).toEqual(['montreal', 'toronto']);
  });

  it('says it is turning from the render that asks for the turn, not a frame later', () => {
    // Read before any effect runs: a test that waits for "not turning" right
    // after a tap must not find the globe still, with the turn not begun.
    const seen: (string | undefined)[] = [];
    function Probe({ lon }: { lon: number }) {
      useLayoutEffect(() => {
        seen.push(document.querySelector<HTMLElement>('[data-testid="probe"]')?.dataset.turning);
      });
      return <Globe markers={markers} focus={{ lat: 48, lon }} tone="day" layout="band" height={230} caption="c" testId="probe" />;
    }
    const { rerender } = render(<Probe lon={14} />);
    rerender(<Probe lon={-80} />);
    expect(seen[0]).toBeUndefined();
    expect(seen[1]).toBe('true');
  });

  it('says nothing at the edge when every place is in view', () => {
    render(
      <Globe markers={markers.slice(0, 1)} focus={{ lat: 48, lon: 14 }} tone="day" layout="band" height={230} caption="c" />,
    );
    expect(screen.queryByTestId('globe-edge')).toBeNull();
  });

  it('fits a route: both ends in the frame, both named', () => {
    const astana = { lat: 51.17, lon: 71.45, city: 'Astana' };
    const groningen = { id: 'g', lat: 53.22, lon: 6.57, label: 'Groningen · 1,848 USD a year', name: 'Groningen' };
    const { container } = render(
      <Globe markers={[groningen]} home={astana} fit={[astana, groningen]} focus={{ lat: 0, lon: 0 }}
             routes names tone="day" layout="band" height={180} caption="c" />,
    );
    const marker = screen.getByTestId('globe-marker-g');
    const x = parseFloat(marker.style.left);
    // jsdom has no layout, so the globe keeps its default 360 px width.
    expect(x).toBeGreaterThan(40);
    expect(x).toBeLessThan(320);
    const names = [...container.querySelectorAll('.globe__name')].map((n) => n.textContent);
    expect(names).toEqual(['Groningen', 'Astana']);
    expect(screen.queryByTestId('globe-edge')).toBeNull();
  });

  it('comes close enough on a short route that its ends stand apart', () => {
    const astana = { lat: 51.17, lon: 71.45, city: 'Astana' };
    const near = { id: 'n', lat: 43.24, lon: 76.89, label: 'Almaty', name: 'Almaty' };
    const far = { id: 'f', lat: 43.65, lon: -79.38, label: 'Toronto', name: 'Toronto' };
    const gap = (m: typeof near) => {
      const { unmount } = render(
        <Globe markers={[m]} home={astana} fit={[astana, m]} focus={{ lat: 0, lon: 0 }}
               routes names tone="day" layout="band" height={180} caption="c" />,
      );
      const marker = screen.getByTestId(`globe-marker-${m.id}`);
      const home = document.querySelector<HTMLElement>('.globe__name--home')!;
      const d = Math.hypot(
        parseFloat(marker.style.left) - parseFloat(home.style.left),
        parseFloat(marker.style.top) - parseFloat(home.style.top),
      );
      unmount();
      return d;
    };
    // Almaty is 1,000 km from Astana, Toronto 9,000: the short route is
    // drawn closer in, so its ends are not a few pixels apart.
    expect(gap(near)).toBeGreaterThan(60);
    expect(gap(far)).toBeGreaterThan(60);
  });
});
