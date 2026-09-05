/**
 * A broken screen must not become a white page.
 */

import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ErrorBoundary } from './ErrorBoundary';

function Bomb(): never {
  throw new Error('render exploded');
}

beforeEach(() => {
  // React logs the caught error itself; silence it so the run stays readable.
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ErrorBoundary', () => {
  it('shows a fallback that says the data is safe, not a blank page', () => {
    render(
      <ErrorBoundary label="the shortlist screen">
        <Bomb />
      </ErrorBoundary>,
    );

    const fallback = screen.getByTestId('error-boundary');
    expect(fallback).toHaveTextContent('Something broke while rendering the shortlist screen');
    expect(fallback).toHaveTextContent('Your data is safe on the server');
    expect(screen.getByRole('button', { name: 'Reload' })).toBeInTheDocument();
  });

  it('names the error so a bug report can be written from it', () => {
    render(<ErrorBoundary><Bomb /></ErrorBoundary>);
    expect(screen.getByTestId('error-boundary')).toHaveTextContent('render exploded');
  });

  it('renders its children untouched when nothing throws', () => {
    render(<ErrorBoundary><p>all fine</p></ErrorBoundary>);
    expect(screen.getByText('all fine')).toBeInTheDocument();
    expect(screen.queryByTestId('error-boundary')).toBeNull();
  });
});
