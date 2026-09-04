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
