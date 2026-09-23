/**
 * Grade conversion must never damage the profile it failed to convert.
 *
 * The audited defect: a raw fetch().then(r => r.json()) with no status check
 * wrote the 400 body — {detail: "..."} — straight into academics.gpa, so a
 * refused conversion silently destroyed the applicant's grades.
 */

import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProfileScreen } from './ProfileScreen';
import { useState } from 'react';
import { ApiError, api } from '@/api/client';
import { setLocale } from '@/lib/i18n';
import { profileCopy } from '@/lib/profileCopy';

const GPA = { raw_value: 4.8, raw_scale_max: 5, raw_scale_label: 'KZ 5-point' };

let draft: Record<string, unknown>;
const setProfileDraft = vi.fn((update: (d: unknown) => unknown) => {
  draft = update(draft) as Record<string, unknown>;
});

vi.mock('@/lib/store', () => ({
  useStore: () => {
    const [profileStep, setProfileStep] = useState(0);
    return {
    activeCaseKey: null, profileStep, setProfileStep,
    profileDraft: draft,
    setProfileDraft,
    saveProfile: vi.fn(),
    validation: null,
    capabilities: null,
    savedProfile: null,
    loading: false,
  }; },
}));

beforeEach(() => {
  setLocale('en');
  draft = { academics: { gpa: { ...GPA } }, activities: [], achievements: [] };
  setProfileDraft.mockClear();
  vi.restoreAllMocks();
  vi.spyOn(api, 'conversionMethods').mockResolvedValue({
    methods: [
      {
        key: 'kz5_to_us4',
        description: 'KZ 5-point to US 4.0',
        source: 'documented',
        caveat: 'not official',
        to_scale: 'US 4.0',
      },
    ],
    note: '',
  });
});

it('provides non-empty copy in every supported locale', () => {
  for (const copy of Object.values(profileCopy)) {
    for (const locale of ['en', 'ru', 'kk'] as const) expect(copy[locale].trim()).not.toBe('');
  }
});

it('switches labels without translating stored enum values or resetting the current step', async () => {
  render(<ProfileScreen onNext={() => {}} />);
  await screen.findByTestId('convert-kz5_to_us4');
  fireEvent.change(screen.getByLabelText('Level', { exact: true }), { target: { value: 'master' } });
  fireEvent.change(screen.getByLabelText('Citizenship', { exact: true }), { target: { value: 'Kazakhstan' } });
  const snapshot = structuredClone(draft);
  act(() => setLocale('ru'));
  expect(screen.getByLabelText('Гражданство')).toHaveValue('Kazakhstan');
  expect(screen.getAllByLabelText('Уровень')[0]).toHaveValue('master');
  expect(draft).toEqual(snapshot);
  fireEvent.click(screen.getByTestId('profile-step-1'));
  act(() => setLocale('kk'));
  expect(screen.getByLabelText('GPA / орташа балл')).toBeVisible();
  expect(screen.getByTestId('profile-step-1')).toHaveAttribute('aria-current', 'step');
  expect(draft).toEqual(snapshot);
  act(() => setLocale('en'));
});

describe('applying a grade conversion', () => {
  it('leaves the grade untouched and explains itself when the API refuses', async () => {
    vi.spyOn(api, 'previewConversion').mockRejectedValue(
      new ApiError(400, 'This scale has no documented conversion method.'),
    );

    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.click(await screen.findByTestId('convert-kz5_to_us4'));

    await waitFor(() => expect(screen.getByTestId('conversion-error')).toBeInTheDocument());
    expect(screen.getByTestId('conversion-error')).toHaveTextContent('no documented conversion');
    expect((draft.academics as Record<string, unknown>).gpa).toEqual(GPA);
    expect(setProfileDraft).not.toHaveBeenCalled();
  });

  it('applies the converted value on success', async () => {
    const converted = { ...GPA, converted_value: 3.9, method_source: 'documented' };
    vi.spyOn(api, 'previewConversion').mockResolvedValue(converted);

    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.click(await screen.findByTestId('convert-kz5_to_us4'));

    await waitFor(() =>
      expect((draft.academics as Record<string, unknown>).gpa).toEqual(converted),
    );
  });

  it('does not call validateProfile just to convert one grade', async () => {
    const validate = vi.spyOn(api, 'validateProfile');
    vi.spyOn(api, 'previewConversion').mockResolvedValue({ ...GPA, converted_value: 3.9 });

    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.click(await screen.findByTestId('convert-kz5_to_us4'));

    await waitFor(() => expect(api.previewConversion).toHaveBeenCalled());
    expect(validate).not.toHaveBeenCalled();
  });
});

describe('six-section profile wizard', () => {
  it('shows application first and only reveals grades on the next step', () => {
    render(<ProfileScreen onNext={() => {}} />);
    expect(screen.getByLabelText('Citizenship')).toBeVisible();
    expect(screen.getByLabelText('GPA / average')).not.toBeVisible();
    fireEvent.click(screen.getByTestId('profile-next-step'));
    expect(screen.getByLabelText('GPA / average')).toBeVisible();
    expect(screen.getByLabelText('Citizenship')).not.toBeVisible();
    expect(screen.getByTestId('profile-step-1')).toHaveAttribute('aria-current', 'step');
  });
  it('keeps typed values when moving between sections', () => {
    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.change(screen.getByLabelText('Citizenship'), { target: { value: 'Kazakhstan' } });
    fireEvent.click(screen.getByTestId('profile-step-4'));
    fireEvent.click(screen.getByTestId('profile-step-0'));
    expect(screen.getByLabelText('Citizenship')).toHaveValue('Kazakhstan');
  });
  it('can expose every existing field without changing the draft', () => {
    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.click(screen.getByTestId('profile-show-all'));
    expect(screen.getByLabelText('GPA / average')).toBeVisible();
    expect(screen.getByLabelText('IELTS overall')).toBeVisible();
    expect(screen.getByLabelText('SAT total')).toBeVisible();
    expect(setProfileDraft).not.toHaveBeenCalled();
  });
});

describe('activity and achievement evidence links', () => {
  beforeEach(() => {
    draft = {
      academics: { gpa: { ...GPA } },
      activities: [{
        name: 'Debate club', category: 'community', role: 'Captain',
        responsibility_level: 'leader', evidence_links: [
          'https://example.org/activity?a=one,two',
          'https://school.example/activity',
        ],
      }],
      achievements: [{
        name: 'Debate final', level: 'national', year: 2026,
        evidence_links: ['https://example.org/achievement'],
      }],
    };
  });

  it('keeps activity rows and API values intact across locale changes', async () => {
    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.click(screen.getByTestId('profile-step-4'));
    const activityLinks = within(screen.getByTestId('activity-0-evidence'));
    expect(activityLinks.getByLabelText('Evidence link 1')).toHaveValue('https://example.org/activity?a=one,two');

    act(() => setLocale('ru'));
    expect(activityLinks.getByLabelText('Ссылка на подтверждение 1')).toHaveValue('https://example.org/activity?a=one,two');
    expect((draft.activities as { evidence_links: string[] }[])[0]?.evidence_links).toEqual([
      'https://example.org/activity?a=one,two',
      'https://school.example/activity',
    ]);

    fireEvent.click(activityLinks.getByRole('button', { name: '+ Добавить ссылку' }));
    await waitFor(() => expect(activityLinks.getByLabelText('Ссылка на подтверждение 3')).toHaveFocus());
    expect(setProfileDraft).not.toHaveBeenCalled();
  });

  it('uses the same independent-row contract for achievements', () => {
    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.click(screen.getByTestId('profile-step-5'));
    const input = within(screen.getByTestId('achievement-0-evidence')).getByLabelText('Evidence link 1');

    fireEvent.change(input, { target: { value: 'https://example.org/achievement?result=gold,silver' } });

    expect((draft.achievements as { evidence_links: string[] }[])[0]?.evidence_links).toEqual([
      'https://example.org/achievement?result=gold,silver',
    ]);
  });
});

describe('reading a transcript', () => {
  const pdf = () => new File([new Uint8Array([37, 80, 68, 70])], 'attestat.pdf', {
    type: 'application/pdf',
  });

  const suggestion = {
    field: 'academics.gpa',
    label: 'Grade average',
    value: { raw_value: 4.82, raw_scale_max: 5, raw_scale_label: '' },
    excerpt: 'Grade point average: 4.82 out of 5',
  };

  it('shows what it read, quoting the line, and applies none of it on its own', async () => {
    vi.spyOn(api, 'readTranscript').mockResolvedValue({
      suggestions: [suggestion],
      note: 'Nothing has been saved.',
    });
    render(<ProfileScreen onNext={() => {}} />);

    fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } });

    const card = await screen.findByTestId('suggestion-academics.gpa');
    expect(card).toHaveTextContent('4.82 out of 5');
    expect(card).toHaveTextContent('Grade point average: 4.82 out of 5');
    // Read, not applied: the applicant's own value is still theirs.
    expect((draft.academics as { gpa: typeof GPA }).gpa.raw_value).toBe(4.8);
  });

  it('applies one suggestion when asked, and keeps the scale name already typed', async () => {
    vi.spyOn(api, 'readTranscript').mockResolvedValue({
      suggestions: [suggestion],
      note: '',
    });
    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } });

    fireEvent.click(await screen.findByTestId('apply-academics.gpa'));

    await waitFor(() => {
      const gpa = (draft.academics as { gpa: typeof GPA }).gpa;
      expect(gpa.raw_value).toBe(4.82);
      // The document says 4.82 out of 5; it does not know what the applicant
      // calls their grading system, and must not blank what they wrote.
      expect(gpa.raw_scale_label).toBe('KZ 5-point');
    });
  });

  it('says why nothing came back, instead of showing an empty box', async () => {
    vi.spyOn(api, 'readTranscript').mockResolvedValue({
      suggestions: [],
      note: 'No text could be read from that PDF.',
    });
    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } });

    expect(await screen.findByTestId('transcript-note')).toHaveTextContent('No text could be read');
  });

  it('leaves the profile untouched when the upload is refused', async () => {
    vi.spyOn(api, 'readTranscript').mockRejectedValue(new ApiError(400, 'Upload the transcript as a PDF.'));
    render(<ProfileScreen onNext={() => {}} />);
    fireEvent.change(screen.getByTestId('transcript-file'), { target: { files: [pdf()] } });

    expect(await screen.findByTestId('transcript-note')).toHaveTextContent('Upload the transcript as a PDF.');
    expect((draft.academics as { gpa: typeof GPA }).gpa.raw_value).toBe(4.8);
  });
});
