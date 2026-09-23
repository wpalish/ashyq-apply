import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { EvidenceLinksField, isEvidenceUrl, type EvidenceLinksCopy } from './EvidenceLinksField';

const copy: EvidenceLinksCopy = {
  label: 'Evidence links',
  hint: 'Add up to five HTTP or HTTPS links. Links are not verified.',
  rowLabel: 'Evidence link',
  add: 'Add evidence link',
  remove: 'Remove link',
  invalid: 'Enter a full HTTP or HTTPS URL.',
  limit: 'Five link limit reached.',
};

const renderField = (value: string[], onChange = vi.fn()) => ({
  onChange,
  ...render(
    <EvidenceLinksField
      idPrefix="evidence"
      scopeKey="case:activity:0"
      value={value}
      onChange={onChange}
      copy={copy}
    />,
  ),
});

describe('EvidenceLinksField', () => {
  it('renders a saved array verbatim without splitting commas or emitting a rewrite', () => {
    const links = ['https://example.org/proof?a=one,two', 'https://school.example/award#result'];
    const { onChange } = renderField(links);

    expect(screen.getByLabelText('Evidence link 1')).toHaveValue(links[0]);
    expect(screen.getByLabelText('Evidence link 2')).toHaveValue(links[1]);
    expect(onChange).not.toHaveBeenCalled();
  });

  it('keeps a newly added blank row out of the array and focuses it', async () => {
    const { onChange } = renderField(['https://example.org/first']);

    fireEvent.click(screen.getByRole('button', { name: 'Add evidence link' }));
    const blank = screen.getByLabelText('Evidence link 2');
    await waitFor(() => expect(blank).toHaveFocus());
    expect(onChange).not.toHaveBeenCalled();

    fireEvent.change(blank, { target: { value: 'https://example.org/second?x=1,2' } });
    expect(onChange).toHaveBeenLastCalledWith([
      'https://example.org/first',
      'https://example.org/second?x=1,2',
    ]);
  });

  it('removes only the selected row and moves focus to its next sibling', async () => {
    const { onChange } = renderField([
      'https://example.org/first',
      'https://example.org/second',
      'https://example.org/third',
    ]);

    fireEvent.click(screen.getByRole('button', { name: 'Remove link: Evidence link 2' }));

    expect(onChange).toHaveBeenLastCalledWith([
      'https://example.org/first',
      'https://example.org/third',
    ]);
    await waitFor(() => expect(screen.getByLabelText('Evidence link 2')).toHaveFocus());
    expect(screen.getByLabelText('Evidence link 1')).toHaveValue('https://example.org/first');
    expect(screen.getByLabelText('Evidence link 2')).toHaveValue('https://example.org/third');
  });

  it('reports URL shape locally without fetching or changing the typed value', () => {
    const request = vi.spyOn(globalThis, 'fetch');
    renderField([]);
    fireEvent.click(screen.getByRole('button', { name: 'Add evidence link' }));
    const input = screen.getByLabelText('Evidence link 1');

    fireEvent.change(input, { target: { value: 'example.org/proof' } });

    expect(input).toHaveValue('example.org/proof');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Enter a full HTTP or HTTPS URL.')).toBeInTheDocument();
    expect(request).not.toHaveBeenCalled();
    request.mockRestore();
  });

  it('stops at the backend five-link limit', () => {
    renderField(Array.from({ length: 5 }, (_, index) => `https://example.org/${index}`));
    expect(screen.getByRole('button', { name: 'Add evidence link' })).toBeDisabled();
    expect(screen.getByText('Five link limit reached.')).toBeInTheDocument();
  });
});

describe('isEvidenceUrl', () => {
  it.each([
    ['https://example.org/proof', true],
    ['http://school.example/award', true],
    ['example.org/proof', false],
    ['ftp://example.org/proof', false],
    [' https://example.org/proof', false],
    ['', true],
  ])('checks %s without network access', (value, expected) => {
    expect(isEvidenceUrl(value)).toBe(expected);
  });
});
