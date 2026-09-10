import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ExamPicker, examHasData } from './ExamPicker';

vi.mock('@/lib/useTranslation', () => ({ useTranslation: () => ({ locale: 'en' }) }));

function Harness({ initial = {}, group = 'english', showAll = false }: {
  initial?: Record<string, unknown>; group?: 'english' | 'standard'; showAll?: boolean;
}) {
  const [draft, update] = useState(initial);
  return <><ExamPicker group={group} draft={draft} update={update} showAll={showAll} />
    <output data-testid="draft-json">{JSON.stringify(draft)}</output></>;
}

describe('exam progressive disclosure', () => {
  it('ignores default metadata but recognizes zero, subscores and planned dates', () => {
    expect(examHasData({ academics: { duolingo: { max_score: 160, name: 'Duolingo English Test' } } }, 'duolingo')).toBe(false);
    expect(examHasData({ academics: { ielts: { test_type: 'academic', status: 'applicant_confirmed' } } }, 'ielts')).toBe(false);
    expect(examHasData({ academics: { sat: { math: 0 } } }, 'sat')).toBe(true);
    expect(examHasData({ academics: { toefl: { reading: 22 } } }, 'toefl')).toBe(true);
    expect(examHasData({ academics: { act: { dates: { planned_retake_on: '2027-04-01' } } } }, 'act')).toBe(true);
  });

  it('starts with no blank score grids visible and reveals the requested exam', () => {
    render(<Harness />);
    expect(screen.getByLabelText('TOEFL total')).not.toBeVisible();
    expect(screen.getByLabelText('IELTS overall')).not.toBeVisible();
    fireEvent.click(screen.getByTestId('exam-toggle-toefl'));
    expect(screen.getByLabelText('TOEFL total')).toBeVisible();
    expect(screen.getByLabelText('IELTS overall')).not.toBeVisible();
  });

  it('automatically reveals scores arriving after hydration', () => {
    const update = vi.fn();
    const view = render(<ExamPicker group="standard" draft={{}} update={update} />);
    view.rerender(<ExamPicker group="standard" draft={{ academics: { sat: { total: 1400 } } }} update={update} />);
    expect(screen.getByLabelText('SAT total')).toBeVisible();
    expect(update).not.toHaveBeenCalled();
  });

  it('collapses and reopens SAT without deleting its score or dates', () => {
    const initial = { academics: { sat: { total: 1400, dates: { taken_on: '2026-05-01' } } } };
    render(<Harness group="standard" initial={initial} />);
    fireEvent.click(screen.getByTestId('exam-toggle-sat'));
    expect(screen.getByLabelText('SAT total')).not.toBeVisible();
    expect(screen.getByText(/Data remains/)).toBeVisible();
    expect(JSON.parse(screen.getByTestId('draft-json').textContent!)).toEqual(initial);
    fireEvent.click(screen.getByTestId('exam-toggle-sat'));
    expect(screen.getByLabelText('SAT total')).toHaveValue(1400);
  });

  it('retains a newly entered score after hide/show', () => {
    render(<Harness group="standard" />);
    fireEvent.click(screen.getByTestId('exam-toggle-act'));
    fireEvent.change(screen.getByLabelText('ACT composite'), { target: { value: '31' } });
    fireEvent.click(screen.getByTestId('exam-toggle-act'));
    fireEvent.click(screen.getByTestId('exam-toggle-act'));
    expect(screen.getByLabelText('ACT composite')).toHaveValue(31);
  });

  it('does not collapse when the last existing score is cleared', () => {
    render(<Harness initial={{ academics: { ielts: { overall: 7 } } }} />);
    fireEvent.change(screen.getByLabelText('IELTS overall'), { target: { value: '' } });
    expect(screen.getByLabelText('IELTS overall')).toBeVisible();
    expect(screen.getByTestId('exam-toggle-ielts')).toHaveAttribute('aria-expanded', 'true');
  });

  it('clears only the Duolingo score and retains dates and scale', () => {
    render(<Harness initial={{ academics: { duolingo: { name: 'Duolingo English Test', score: 130, max_score: 160, dates: { planned_retake_on: '2027-03-01' } } } }} />);
    fireEvent.change(screen.getByLabelText('Duolingo English Test'), { target: { value: '' } });
    const value = JSON.parse(screen.getByTestId('draft-json').textContent!).academics.duolingo;
    expect(value).toEqual({ name: 'Duolingo English Test', score: null, max_score: 160, dates: { planned_retake_on: '2027-03-01' } });
  });

  it('initializes Duolingo metadata on explicit date entry and clears a date to null', () => {
    render(<Harness />);
    fireEvent.click(screen.getByTestId('exam-toggle-duolingo'));
    fireEvent.change(screen.getByLabelText('Duolingo planned retake'), { target: { value: '2027-03-01' } });
    expect(JSON.parse(screen.getByTestId('draft-json').textContent!).academics.duolingo.name).toBe('Duolingo English Test');
    fireEvent.change(screen.getByLabelText('Duolingo planned retake'), { target: { value: '' } });
    expect(JSON.parse(screen.getByTestId('draft-json').textContent!).academics.duolingo.dates.planned_retake_on).toBeNull();
  });

  it('shows every exam in review mode without mutating data', () => {
    render(<Harness showAll />);
    expect(screen.getByLabelText('IELTS overall')).toBeVisible();
    expect(screen.getByLabelText('TOEFL total')).toBeVisible();
    expect(screen.getByLabelText('Duolingo English Test')).toBeVisible();
    expect(screen.getByTestId('exam-toggle-ielts')).toBeDisabled();
    expect(screen.getByTestId('draft-json')).toHaveTextContent('{}');
  });

  it('requires confirmation to remove the complete Duolingo result', () => {
    const initial = { academics: { duolingo: { name: 'Duolingo English Test', score: 130, dates: { taken_on: '2026-03-01' } } } };
    render(<Harness initial={initial} />);
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    fireEvent.click(screen.getByTestId('remove-duolingo'));
    expect(JSON.parse(screen.getByTestId('draft-json').textContent!)).toEqual(initial);
    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByTestId('remove-duolingo'));
    expect(JSON.parse(screen.getByTestId('draft-json').textContent!).academics.duolingo).toBeNull();
    confirm.mockRestore();
  });
});
