/**
 * What the two moderation controls must not stop saying.
 *
 * A person being harassed reaches for whichever button is in front of them.
 * Reporting is a request to a human and takes as long as a human takes;
 * blocking is a decision and works at once. If the report dialog stops saying
 * which is which, the slower tool silently becomes the advertised answer.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BlockButton, ReportButton } from './moderation';

describe('ReportButton', () => {
  it('says that a report is read by a person, and names the fast alternative', () => {
    render(<ReportButton subjectType="post" subjectId="p1" />);
    fireEvent.click(screen.getByRole('button', { name: 'Report' }));

    const explanation = screen.getByText(/Reports are read by a person/);
    expect(explanation).toHaveTextContent('not instant');
    expect(explanation).toHaveTextContent('block them');
  });

  it('offers the reasons the product defines and no free-text category', () => {
    render(<ReportButton subjectType="post" subjectId="p2" />);
    fireEvent.click(screen.getByRole('button', { name: 'Report' }));

    const reasons = screen.getByLabelText('What is wrong with it');
    expect(reasons).toHaveDisplayValue('Harassment or abuse');
    expect(screen.getByRole('option', { name: /rumour about a university/ })).toBeInTheDocument();
  });
});

describe('BlockButton', () => {
  it('explains what a block does before doing it, including the silence', () => {
    render(<BlockButton userId="u1" blocked={false} onChanged={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: 'Block' }));

    const explanation = screen.getByText(/They will not be able to write to you/);
    expect(explanation).toHaveTextContent('neither of you will see the other');
    // The blocked person is not told. Saying so is part of the decision.
    expect(explanation).toHaveTextContent('They are not told');
  });

  it('offers to undo when the person is already blocked', () => {
    render(<BlockButton userId="u1" blocked onChanged={() => {}} />);
    expect(screen.getByRole('button', { name: 'Unblock' })).toBeInTheDocument();
  });
});
