import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { LegalScreen } from './LegalScreen';

describe('source-bound privacy notice', () => {
  it('does not imply that reading a policy records consent or verifies the operator', () => {
    render(<LegalScreen />);
    expect(screen.getByTestId('privacy-operator-gap')).toHaveTextContent('must be confirmed');
    expect(screen.getByTestId('privacy-consent-gap')).toHaveTextContent('does not currently record');
    expect(screen.getByText(/Notice version/)).toHaveTextContent('2026-10-09.draft1');
  });

  it('distinguishes sharing inside a workspace from account closure and full erasure', () => {
    render(<LegalScreen />);
    expect(screen.getByTestId('privacy-summary')).toHaveTextContent('Members of that workspace');
    const rights = screen.getByText(/What you can do with it/).closest('p');
    expect(rights).toHaveTextContent('shared workspace and its cases remain');
    expect(rights).toHaveTextContent('deletion error must not be reported as success');
    expect(rights).toHaveTextContent('not an export of every account');
    expect(rights).toHaveTextContent('backups require their own');
  });

  it('discloses configured mail, payment and infrastructure boundaries without promising a masked-only transfer', () => {
    render(<LegalScreen />);
    const transfers = screen.getByText(/What leaves the service/).closest('p');
    expect(transfers).toHaveTextContent('mail provider');
    expect(transfers).toHaveTextContent('does not mean the provider received only a masked phone');
    expect(transfers).toHaveTextContent('Hosting and network operators');
    expect(transfers).toHaveTextContent('not a verification of every deployed infrastructure log');
  });

  it('separates implemented local processing from a future AI contract and preserves mandatory rights', () => {
    render(<LegalScreen />);
    expect(screen.getByTestId('privacy-ai-boundary')).toHaveTextContent('optional TypeSafe decision capability');
    expect(screen.getByTestId('privacy-ai-boundary')).toHaveTextContent('active product call path was not established');
    const limits = screen.getByText(/Service limits and your rights/).closest('p');
    expect(limits).toHaveTextContent('does not remove any mandatory consumer or personal-data rights');
    expect(screen.queryByText(/A missed deadline or a misread requirement remains yours to bear/)).not.toBeInTheDocument();
  });
});
