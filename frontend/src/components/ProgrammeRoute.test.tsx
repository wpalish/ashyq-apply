/**
 * A programme's route from home: drawn only between two known places, and
 * saying which one is missing otherwise.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ProgrammeRoute } from './ProgrammeRoute';
import type { ProgramResult } from '@/types';

const result = (city: string, country: string) => ({
  id: 'p1', city, country, funding_gap: { computable: true, gap: { amount: 1848, currency: 'USD' } },
}) as unknown as ProgramResult;

const astana = { lat: 51.17, lon: 71.45, city: 'Astana' };

describe('the route on a programme', () => {
  it('runs from home to the city, naming both', () => {
    render(<ProgrammeRoute result={result('Groningen', 'Netherlands')} home={astana} tone="day" height={180} testId="route" />);
    expect(screen.getByTestId('route')).toBeInTheDocument();
    expect(screen.getByText('The route from Astana to Groningen.')).toBeInTheDocument();
    expect(screen.getByText('Groningen')).toBeInTheDocument();
    expect(screen.getByText('Astana')).toBeInTheDocument();
    expect(screen.queryByTestId('route-no-home')).toBeNull();
  });

  it('shows the city alone, and says what would draw the route, without a home', () => {
    render(<ProgrammeRoute result={result('Groningen', 'Netherlands')} home={null} tone="day" height={180} testId="route" />);
    expect(screen.getByTestId('route-no-home')).toHaveTextContent('country of residence');
    expect(screen.getByText('Groningen on the globe.')).toBeInTheDocument();
  });

  it('draws no globe for a city the table does not have, and says so', () => {
    render(<ProgrammeRoute result={result('Atlantis', 'Greece')} home={astana} tone="day" height={180} testId="route" />);
    expect(screen.queryByTestId('route')).toBeNull();
    expect(screen.getByTestId('route-none')).toHaveTextContent('Atlantis is not in its table of cities yet');
  });
});
