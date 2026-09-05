/**
 * Grade conversion must never damage the profile it failed to convert.
 *
 * The audited defect: a raw fetch().then(r => r.json()) with no status check
 * wrote the 400 body — {detail: "..."} — straight into academics.gpa, so a
 * refused conversion silently destroyed the applicant's grades.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ProfileScreen } from './ProfileScreen';
import { ApiError, api } from '@/api/client';

const GPA = { raw_value: 4.8, raw_scale_max: 5, raw_scale_label: 'KZ 5-point' };

let draft: Record<string, unknown>;
const setProfileDraft = vi.fn((update: (d: unknown) => unknown) => {
  draft = update(draft) as Record<string, unknown>;
});

vi.mock('@/lib/store', () => ({
  useStore: () => ({
    profileDraft: draft,
    setProfileDraft,
    saveProfile: vi.fn(),
    validation: null,
    capabilities: null,
    savedProfile: null,
    loading: false,
  }),
}));

beforeEach(() => {
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
