/**
 * Knowledge-base mode copy (KB smoke 2026-10-19, B2-B4).
 *
 * In kb mode no page is read during a run, so the detail tabs must not say a
 * page "could not be read", and a verified fact the comparison cannot use is
 * shown, not hidden behind "not found".
 */

import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { ResultDetail } from './ResultDetail';
import { setLocale } from '@/lib/i18n';
import type { ClaimOut, ProgramResult, UnresolvedQuestion } from '@/types';

const STALE_NOTES =
  'Verified knowledge base (expert-checked); quote found on the official page on 2026-10-19. '
  + "Stale, not current: academic year 2026/2027 is before the fall 2027 intake's 2027/28.";

function claim(overrides: Partial<ClaimOut>): ClaimOut {
  return {
    claim_type: 'tuition',
    normalized_value: { amount: 66720, currency: 'USD' },
    original_text_excerpt: 'Tuition 2026-2027: $66,720',
    source_url: 'https://example.edu/tuition',
    academic_year: '2026/2027',
    status: 'POSSIBLY_STALE',
    notes: STALE_NOTES,
    id: 'c1',
    is_stale: true,
    age_days: 0,
    ...overrides,
  } as ClaimOut;
}

function question(overrides: Partial<UnresolvedQuestion>): UnresolvedQuestion {
  return {
    topic: 'funding',
    question: 'Which scholarships does Example University offer?',
    why_it_matters: 'The verified knowledge base names no award for this programme.',
    university: 'Example University',
    program: 'BSc Computer Science',
    suggested_contact: null,
    blocking: false,
    ...overrides,
  };
}

function result(overrides: Record<string, unknown> = {}): ProgramResult {
  return {
    id: 'result-1',
    university: 'Example University',
    program: 'BSc Computer Science',
    country: 'Germany',
    city: 'Berlin',
    degree: 'bachelor',
    program_url: null,
    eligibility: 'NEEDS_OFFICIAL_CLARIFICATION',
    admissions_fit: 'INSUFFICIENT_DATA',
    best_funding_classification: 'UNKNOWN',
    funding_gap: null,
    admission_deadline: null,
    requirement_checks: [],
    hard_filter_failures: [],
    claims: [],
    costs: { items: {}, total: null, academic_year: '2027/28', source_urls: [] },
    conflicts: [],
    unresolved: [],
    scholarships: [],
    source_urls: [],
    rankings: [],
    ...overrides,
  } as unknown as ProgramResult;
}

describe('the Costs tab', () => {
  it('names a verified fee for another academic year instead of saying none was found', () => {
    render(<ResultDetail result={result({ claims: [claim({})] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));

    expect(screen.getByTestId('unused-tuition')).toHaveTextContent(
      "66,720 USD a year, academic year 2026/2027 (not current: academic year 2026/2027 is before the fall 2027 intake's 2027/28)",
    );
    expect(screen.queryByText(/No official cost of attendance was found/)).not.toBeInTheDocument();
  });

  it('keeps the plain notice when no fee was found at all', () => {
    render(<ResultDetail result={result()} />);
    fireEvent.click(screen.getByTestId('tab-costs'));

    expect(
      screen.getByText('No official cost of attendance was found for this programme and intake.'),
    ).toBeInTheDocument();
  });
});

describe('the two honest fee shapes (round 11): a per-credit rate and a printed range', () => {
  afterEach(() => act(() => setLocale('en')));
  const RANGE_URL = 'https://www.sheffield.ac.uk/fees';
  const range = claim({
    id: 'range', academic_year: '2027/28', status: 'VERIFIED_CURRENT', is_stale: false, source_url: RANGE_URL,
    normalized_value: { amount: 34670, currency: 'GBP', range_low: 27650, range_high: 34670 },
    notes: 'Verified knowledge base. Published as a range, not a single figure.',
  });
  const rangeCosts = {
    items: { tuition: { amount: 34670, currency: 'GBP', academic_year: '2027/28', is_estimate: false, range_low: 27650, range_high: 34670, source_url: RANGE_URL } },
    total: null, academic_year: '2027/28', source_urls: [RANGE_URL], is_range: true,
  };
  const warning = 'Tuition is published only as a range, 27,650–34,670 GBP; the cost uses its upper bound, so it is not understated.';
  const rangeGap = {
    computable: false, gap: null, gap_low: null, gap_high: null, total_cost: null, confirmed_aid: null,
    stackable_aid: null, year_mismatch: false, currency_mismatch: false, category_mismatch: false,
    cost_basis: 'itemised_partial', missing_categories: [], reason: 'x', warnings: [warning],
    warning_messages: [{ key: 'gap.kbTuitionRange', params: { range: '27,650–34,670 GBP' }, parts: {} }],
  };
  const perCredit = claim({
    id: 'ubc', academic_year: '2026/27', status: 'VERIFIED_CURRENT', is_stale: false,
    normalized_value: { amount: 1789.18, currency: 'CAD' },
    notes: 'Verified knowledge base. Amount per credit, as published; not a yearly figure.',
  });

  it('shows a printed range in the cost table as that range, never as one figure', () => {
    render(<ResultDetail result={result({ claims: [range], costs: rangeCosts, funding_gap: rangeGap })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));

    expect(document.body).toHaveTextContent('published range 27,650–34,670 GBP · 2027/28');
    expect(document.body).toHaveTextContent(warning);
  });

  it('lists a per-credit rate as published per credit, with no yearly figure', () => {
    render(<ResultDetail result={result({ claims: [perCredit] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));

    expect(screen.getByTestId('unused-tuition')).toHaveTextContent(
      '1,789.18 CAD per credit, academic year 2026/27 (published per credit (no yearly figure printed))',
    );
  });

  it('says both shapes in Russian and Kazakh', () => {
    act(() => setLocale('ru'));
    const { unmount } = render(<ResultDetail result={result({ claims: [perCredit] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));
    expect(screen.getByTestId('unused-tuition')).toHaveTextContent(
      '1,789.18 CAD за кредит, учебный год 2026/27 (опубликовано за кредит (годовая сумма не указана))',
    );
    unmount();

    const { unmount: unmountRange } = render(
      <ResultDetail result={result({ claims: [range], costs: rangeCosts, funding_gap: rangeGap })} knowledgeMode="kb" />,
    );
    fireEvent.click(screen.getByTestId('tab-costs'));
    expect(document.body).toHaveTextContent('опубликованный диапазон 27,650–34,670 GBP · 2027/28');
    expect(document.body).toHaveTextContent('Плата за обучение опубликована только диапазоном, 27,650–34,670 GBP');
    unmountRange();

    act(() => setLocale('kk'));
    render(<ResultDetail result={result({ claims: [perCredit] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));
    expect(screen.getByTestId('unused-tuition')).toHaveTextContent(
      'кредит үшін 1,789.18 CAD, 2026/27 оқу жылы (кредит үшін жарияланған (жылдық сома көрсетілмеген))',
    );
  });
});

describe('the Funding tab with no award', () => {
  it('says in kb mode that no page was read, and shows the open question', () => {
    render(<ResultDetail result={result({ unresolved: [question({})] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-funding'));

    expect(screen.getByText(/names no scholarship for this programme/)).toBeInTheDocument();
    expect(screen.queryByText(/could be read/)).not.toBeInTheDocument();
    expect(screen.getByText('Which scholarships does Example University offer?')).toBeInTheDocument();
  });

  it('states a verified "none offered" as the outcome', () => {
    const none = 'No institutional scholarship: Example University states that it offers none.';
    render(
      <ResultDetail
        result={result({ funding_gap: { computable: false, reason: '', warnings: [none] } })}
        knowledgeMode="kb"
      />,
    );
    fireEvent.click(screen.getByTestId('tab-funding'));

    expect(screen.getByText(none)).toBeInTheDocument();
  });

  it('keeps the live copy outside kb mode', () => {
    render(<ResultDetail result={result()} knowledgeMode="live" />);
    fireEvent.click(screen.getByTestId('tab-funding'));

    expect(screen.getByText(/No official scholarship page could be read/)).toBeInTheDocument();
  });
});

describe('the Requirements tab of a row that needs clarification', () => {
  it('shows the verified statement behind it', () => {
    const language = question({
      topic: 'language requirement',
      question: 'Not an English requirement: the language requirement is German (DSH 2). Which language certificate does Example University require instead, and do you hold it?',
      why_it_matters: 'Verified on the official page https://example.edu/de: "DSH 2".',
    });
    render(<ResultDetail result={result({ unresolved: [language] })} knowledgeMode="kb" />);

    expect(screen.getByTestId('requirement-questions')).toHaveTextContent(
      'the language requirement is German (DSH 2)',
    );
    expect(screen.getByText(/holds no requirement for this programme/)).toBeInTheDocument();
  });
});

describe('a current fact with a caveat (owner flags: inferred year, standing fee policy)', () => {
  const YEAR = 'year not printed on the page; assumed current application cycle';
  const deadline = claim({
    id: 'd1',
    claim_type: 'admission_deadline',
    normalized_value: '2027-01-15',
    original_text_excerpt: 'Apply by January 15',
    academic_year: null,
    status: 'VERIFIED_CURRENT',
    is_stale: false,
    notes: 'Verified knowledge base (expert-checked, quote verified); quote found on the official page '
      + `on 2026-10-19. Caveat: ${YEAR}.`,
    caveat_message: { key: 'caveat.yearInferred', params: {}, parts: {} },
  });
  const check = {
    requirement: 'IELTS overall', status: 'MET', published_value: 7, applicant_value: 7.5,
    explanation: 'Meets the minimum.',
  };

  afterEach(() => act(() => setLocale('en')));

  it('is never labelled "Verified" and says why', () => {
    render(<ResultDetail result={result({ claims: [deadline] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-sources'));

    expect(screen.getByText('Current, with caveat')).toBeInTheDocument();
    expect(screen.queryByText('Verified')).not.toBeInTheDocument();
    expect(screen.getByTestId('claim-caveat')).toHaveTextContent(`Caveat: ${YEAR}.`);
  });

  it('carries the caveat beside the headline deadline', () => {
    render(
      <ResultDetail
        result={result({
          claims: [deadline],
          requirement_checks: [check],
          hard_filter_failures: [],
          admission_deadline: '2027-01-15',
          admission_deadline_raw: '2027-01-15',
        })}
        knowledgeMode="kb"
      />,
    );

    expect(screen.getByTestId('deadline-caveat')).toHaveTextContent(`Caveat: ${YEAR}.`);
  });

  it('speaks Russian when the caveat is keyed', () => {
    act(() => setLocale('ru'));
    render(<ResultDetail result={result({ claims: [deadline] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-sources'));

    expect(screen.getByTestId('claim-caveat')).toHaveTextContent(
      'Оговорка: год на странице не указан; принят текущий цикл приёма.',
    );
  });

  it('lists a current per-semester policy fee as not a yearly figure', () => {
    const fee = claim({
      academic_year: null,
      status: 'VERIFIED_CURRENT',
      is_stale: false,
      normalized_value: { amount: 2190, currency: 'CHF' },
      notes: 'Verified knowledge base. Amount per semester, as published; not a yearly figure. '
        + 'Caveat: fee policy page; no academic year printed.',
    });
    render(<ResultDetail result={result({ claims: [fee] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));

    expect(screen.getByTestId('unused-tuition')).toHaveTextContent(
      '2,190 CHF per semester, no academic year stated (published per semester, not as a yearly figure)',
    );
  });
});

describe('the Documents tab (KB v10 smoke)', () => {
  const UBC = 'https://you.ubc.ca/applying-ubc/applied/submit-documents/';
  const STALE_DOC_NOTES =
    'Verified knowledge base (expert-checked, quote verified); quote found on the official page on 2026-10-19. '
    + "Stale, not current: academic year 2027/2028 is before the fall 2028 intake's 2028/29.";

  function item(name: string, owner: string, required: boolean) {
    return {
      name, purpose: 'admission', owner, required, format_notes: '', max_pages: null,
      max_file_size_mb: null, naming_convention: null, needs_translation: false,
      needs_notarization: false, needs_apostille: false, needs_credential_evaluation: false,
      word_limit: null, character_limit: null, prompt_text: null, deadline: null,
      deadline_timezone: null, depends_on: [], lead_time_days: null, source_url: UBC, claim_ids: [UBC],
    };
  }

  const transcript = item('Full academic transcript', 'school', true);
  const english = item('English language test report', 'third_party', false);
  const essay = item('Personal Essay', 'applicant', true);
  const stale = question({
    topic: 'required documents',
    question: 'Is the document list for Computer Science at UBC still the one for the fall 2028 intake?',
    why_it_matters: 'The verified knowledge base holds these documents, but not as current.',
  });
  const checklist = {
    result_id: 'result-1', university: 'UBC', program: 'Computer Science',
    admission_documents: [transcript, english, essay], scholarship_documents: [],
    applicant_actions: [essay], school_actions: [transcript], recommender_actions: [],
    certification_actions: [english],
    ordered_steps: ['1. Your school: Full academic transcript (allow ~21 days)'],
    unresolved: [stale], generated_at: '2026-10-19T20:45:00Z', completeness: 'partial',
  };
  const claims = [
    claim({
      id: 't', claim_type: 'required_document', normalized_value: 'Full academic transcript',
      academic_year: '2027/2028', notes: STALE_DOC_NOTES, source_url: UBC,
    }),
    claim({
      id: 'e', claim_type: 'required_document', status: 'VERIFIED_CURRENT', is_stale: false,
      normalized_value: {
        document: 'English language test report', requirement: 'conditional',
        condition: 'unless an ELAS waiver is requested instead',
      },
      notes: 'Verified knowledge base.', source_url: UBC,
    }),
    claim({
      id: 's', claim_type: 'required_document', status: 'VERIFIED_CURRENT', is_stale: false,
      normalized_value: 'Personal Essay', notes: 'Verified knowledge base.', source_url: UBC,
    }),
  ];

  it('lists each item with its requirement, owner, condition, stale reason and source', () => {
    render(<ResultDetail result={result({ checklist, claims })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-documents'));

    const rows = screen.getAllByTestId('document-item');
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent('Full academic transcript');
    expect(rows[0]).toHaveTextContent('Required');
    expect(rows[0]).toHaveTextContent('Your school');
    expect(rows[0]).toHaveTextContent(
      "Not current: academic year 2027/2028 is before the fall 2028 intake's 2028/29.",
    );
    expect(rows[1]).toHaveTextContent('Conditional');
    expect(rows[1]).toHaveTextContent('Condition, as published: unless an ELAS waiver is requested instead.');
    expect(rows[1]).not.toHaveTextContent('Not current');
    expect(rows[2]).toHaveTextContent('Personal Essay');
    expect(rows[2]).toHaveTextContent('You prepare it');
    expect(rows[2]?.querySelector('a')).toHaveAttribute('href', UBC);
    expect(screen.getByTestId('document-questions')).toHaveTextContent(
      'Is the document list for Computer Science at UBC still the one for the fall 2028 intake?',
    );
  });

  it('shows why an approved row has no checklist instead of asking to approve it', () => {
    const none = question({
      topic: 'documents',
      question: 'What documents does Example University require for BSc Computer Science?',
      why_it_matters: 'The verified knowledge base does not hold document lists yet, and live research is switched off, so nothing was read or assumed.',
    });
    render(<ResultDetail result={result({ unresolved: [none] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-documents'));

    expect(screen.getByTestId('document-questions')).toHaveTextContent(
      'The verified knowledge base does not hold document lists yet',
    );
    expect(screen.queryByText(/Approve this row/)).not.toBeInTheDocument();
  });

  it('still asks to approve a row the document stage has not reached', () => {
    render(<ResultDetail result={result()} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-documents'));

    expect(screen.getByText(/Approve this row/)).toBeInTheDocument();
  });

  describe('follow-ups D3, D4, D6', () => {
    afterEach(() => act(() => setLocale('en')));

    it('labels a stale kb checklist as verified with items not current, not "partially read" (D3)', () => {
      render(<ResultDetail result={result({ checklist, claims })} knowledgeMode="kb" />);
      fireEvent.click(screen.getByTestId('tab-documents'));

      expect(screen.getByText('verified, some items not current')).toBeInTheDocument();
      expect(screen.queryByText('partially read')).not.toBeInTheDocument();
    });

    it('keeps "partially read" for a live checklist (D3)', () => {
      render(<ResultDetail result={result({ checklist, claims })} knowledgeMode="live" />);
      fireEvent.click(screen.getByTestId('tab-documents'));

      expect(screen.getByText('partially read')).toBeInTheDocument();
    });

    it('says a kb checklist in Russian and Kazakh comes from the verified knowledge base (D3)', () => {
      act(() => setLocale('ru'));
      const { unmount } = render(
        <ResultDetail result={result({ checklist: { ...checklist, completeness: 'official' }, claims })} knowledgeMode="kb" />,
      );
      fireEvent.click(screen.getByTestId('tab-documents'));
      expect(screen.getByText('из проверенной базы знаний')).toBeInTheDocument();
      unmount();

      act(() => setLocale('kk'));
      render(<ResultDetail result={result({ checklist, claims })} knowledgeMode="kb" />);
      fireEvent.click(screen.getByTestId('tab-documents'));
      expect(screen.getByText('тексерілген, кейбір тармақтар өзекті емес')).toBeInTheDocument();
    });

    const steps = {
      ...checklist,
      ordered_steps: [
        '1. Your school: Full academic transcript (allow ~21 days)',
        '2. You: Personal Essay (allow ~1 days)',
        '3. A third party: English language test report (allow ~5 days)',
      ],
    };

    it('says one day in the singular, including a step saved as "~1 days" (D4)', () => {
      render(<ResultDetail result={result({ checklist: steps, claims })} knowledgeMode="kb" />);
      fireEvent.click(screen.getByTestId('tab-documents'));

      expect(screen.getByText('You: Personal Essay (allow ~1 day)')).toBeInTheDocument();
      expect(screen.getByText('Your school: Full academic transcript (allow ~21 days)')).toBeInTheDocument();
    });

    it('declines the day count in Russian and keeps Kazakh uninflected (D4)', () => {
      act(() => setLocale('ru'));
      const { unmount } = render(<ResultDetail result={result({ checklist: steps, claims })} knowledgeMode="kb" />);
      fireEvent.click(screen.getByTestId('tab-documents'));
      expect(screen.getByText(/Personal Essay \(заложите ~1 день\)/)).toBeInTheDocument();
      expect(screen.getByText(/Full academic transcript \(заложите ~21 день\)/)).toBeInTheDocument();
      expect(screen.getByText(/English language test report \(заложите ~5 дней\)/)).toBeInTheDocument();
      unmount();

      act(() => setLocale('kk'));
      render(<ResultDetail result={result({ checklist: steps, claims })} knowledgeMode="kb" />);
      fireEvent.click(screen.getByTestId('tab-documents'));
      expect(screen.getByText(/Personal Essay \(~1 күн уақыт бөліңіз\)/)).toBeInTheDocument();
    });

    it('counts the checklist\'s own questions among the open questions (D6)', () => {
      const own = question({ topic: 'documents' });
      render(<ResultDetail result={result({ checklist, claims, unresolved: [own] })} knowledgeMode="kb" />);

      expect(screen.getByText(/2 open questions/)).toBeInTheDocument();
    });
  });

  describe('a document list published for another cycle, in en, ru and kk', () => {
    afterEach(() => act(() => setLocale('en')));

    const reason = 'document list published for "2027 Spring Admissions Guide", not the fall 2028 intake';
    const reasonRef = {
      key: 'stale.documentsForCycle',
      params: { cycle: '2027 Spring Admissions Guide', intake: 'fall 2028' },
    };
    const listed = `Full academic transcript (${reason})`;
    const otherCycle = {
      ...checklist,
      unresolved: [
        question({
          topic: 'required documents',
          question: 'Is the document list for Computer Science at UBC still the one for the fall 2028 intake?',
          question_message: {
            key: 'question.documentListCurrent',
            params: { programme: 'Computer Science', university: 'UBC', intake: 'fall 2028' },
          },
          why_it_matters:
            `The verified knowledge base holds these documents, but not as current: ${listed}. `
            + 'They are listed so you can prepare, not as confirmed.',
          why_message: {
            key: 'why.documentsNotCurrent',
            params: { documents: listed },
            parts: {
              documents: [{
                key: 'stale.documentItem',
                params: { document: 'Full academic transcript', reasons: reason },
                parts: { reasons: [reasonRef] },
              }],
            },
          },
        }),
      ],
    };
    const staleClaims = [
      claim({
        id: 't', claim_type: 'required_document', normalized_value: 'Full academic transcript',
        academic_year: null, source_url: UBC,
        notes: `Verified knowledge base (expert-checked). Stale, not current: ${reason}.`,
        stale_messages: [reasonRef],
      }),
      ...claims.slice(1),
    ];

    function open() {
      const view = render(<ResultDetail result={result({ checklist: otherCycle, claims: staleClaims })} knowledgeMode="kb" />);
      fireEvent.click(screen.getByTestId('tab-documents'));
      return view;
    }

    it('keeps the English as the backend wrote it', () => {
      open();
      expect(screen.getAllByTestId('document-item')[0]).toHaveTextContent(`Not current: ${reason}.`);
      expect(screen.getByTestId('document-questions')).toHaveTextContent(`not as current: ${listed}.`);
    });

    it('says the item and the question in Russian, with the cycle as printed', () => {
      act(() => setLocale('ru'));
      open();
      expect(screen.getAllByTestId('document-item')[0]).toHaveTextContent(
        'Не актуально: список документов опубликован для «2027 Spring Admissions Guide», а не для набора fall 2028.',
      );
      const questions = screen.getByTestId('document-questions');
      expect(questions).toHaveTextContent('Действует ли список документов для программы Computer Science в UBC для набора fall 2028?');
      expect(questions).toHaveTextContent(
        '«Full academic transcript» (список документов опубликован для «2027 Spring Admissions Guide», а не для набора fall 2028)',
      );
      expect(questions).not.toHaveTextContent('not the fall 2028 intake');
    });

    it('says the item and the question in Kazakh', () => {
      act(() => setLocale('kk'));
      open();
      expect(screen.getAllByTestId('document-item')[0]).toHaveTextContent(
        'Өзекті емес: құжаттар тізімі fall 2028 қабылдауына емес, «2027 Spring Admissions Guide» үшін жарияланған.',
      );
      const questions = screen.getByTestId('document-questions');
      expect(questions).toHaveTextContent('UBC Computer Science бағдарламасының құжаттар тізімі fall 2028 қабылдауына әлі де жарамды ма?');
      expect(questions).toHaveTextContent('Тексерілген білім базасында бұл құжаттар бар');
      expect(questions).not.toHaveTextContent('not the fall 2028 intake');
    });
  });
});

describe('caveated, stale and passed facts on the v18 KB (KB v18 smoke)', () => {
  afterEach(() => act(() => setLocale('en')));

  const DOC_NOTES = 'Verified knowledge base (expert-checked, quote verified); quote found on the official page on 2026-10-19. '
    + 'Stale, not current: document list published for "2026 Admission Information", not the fall 2027 intake.';

  function checklistOf(steps: string[], items: unknown[] = []) {
    return {
      result_id: 'result-1', university: 'Example University', program: 'BSc Computer Science',
      admission_documents: items, scholarship_documents: [], applicant_actions: items, school_actions: [],
      recommender_actions: [], certification_actions: [], ordered_steps: steps,
      unresolved: [], generated_at: '2026-10-20T03:06:21Z', completeness: 'partial',
    };
  }

  it('U1: a fact stale for a stated reason says "not current", not its age', () => {
    render(<ResultDetail result={result({ claims: [claim({ age_days: 1 })] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-sources'));
    expect(screen.queryByText('1d old')).not.toBeInTheDocument();
    expect(screen.getByText('not current')).toBeInTheDocument();
  });

  it('U1 and U5: a stale document item and the suggested order, in Russian', () => {
    act(() => setLocale('ru'));
    const doc = claim({
      claim_type: 'required_document', normalized_value: 'Personal statement', academic_year: null,
      notes: DOC_NOTES, age_days: 1, source_url: 'https://example.edu/docs',
    });
    const item = {
      name: 'Personal statement', purpose: 'admission', owner: 'applicant', required: true, format_notes: '',
      max_pages: null, max_file_size_mb: null, naming_convention: null, needs_translation: false,
      needs_notarization: false, needs_apostille: false, needs_credential_evaluation: false, word_limit: null,
      character_limit: null, prompt_text: null, deadline: null, deadline_timezone: null, depends_on: [],
      lead_time_days: 14, source_url: 'https://example.edu/docs', claim_ids: ['https://example.edu/docs'],
    };
    const checklist = checklistOf([
      '1. Your referee: Letter of recommendation (allow ~30 days)',
      '2. You: Personal statement (allow ~14 days) — after Offer letter',
      '3. A third party: Admission test result',
    ], [item]);
    render(<ResultDetail result={result({ claims: [doc], checklist })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-documents'));
    const listed = screen.getByTestId('document-item');
    expect(listed).toHaveTextContent('не актуально');
    expect(listed).not.toHaveTextContent('1 дн. назад');
    expect(screen.getByText('Ваш рекомендатель: Letter of recommendation (заложите ~30 дней)')).toBeInTheDocument();
    expect(screen.getByText('Вы: Personal statement (заложите ~14 дней) — после: Offer letter')).toBeInTheDocument();
    expect(screen.getByText('Третья сторона: Admission test result')).toBeInTheDocument();
  });

  it('U5: the English steps are unchanged', () => {
    const checklist = checklistOf(['1. You: Passport identity page (copy) (allow ~1 day) — after Offer letter']);
    render(<ResultDetail result={result({ checklist })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-documents'));
    expect(screen.getByText('You: Passport identity page (copy) (allow ~1 day) — after Offer letter')).toBeInTheDocument();
  });

  it('U2: a passed deadline is said to have passed in the headline', () => {
    render(<ResultDetail result={result({ admission_deadline: '2026-10-15', deadline_passed: true })} knowledgeMode="kb" />);
    expect(screen.getByTestId('deadline-passed')).toHaveTextContent('deadline passed');
  });

  it('U2: an open deadline carries no such mark', () => {
    render(<ResultDetail result={result({ admission_deadline: '2027-01-05', deadline_passed: false })} knowledgeMode="kb" />);
    expect(screen.queryByTestId('deadline-passed')).not.toBeInTheDocument();
  });

  function costsOf(url: string, amount: number, currency: string) {
    return {
      items: { tuition: { amount, currency, academic_year: '2027/28', is_estimate: false, range_low: null, range_high: null, source_url: url } },
      total: null, academic_year: '2027/28', source_urls: [url],
    };
  }

  it('U3: a caveated yearly fee in the cost table keeps its caveat', () => {
    const url = 'https://www.iup.kyoto-u.ac.jp/guidelines.pdf';
    const fee = claim({
      academic_year: null, status: 'VERIFIED_CURRENT', is_stale: false, source_url: url,
      normalized_value: { amount: 535800, currency: 'JPY' },
      notes: 'Verified knowledge base. Caveat: fee policy page; no academic year printed.',
      caveat_message: { key: 'caveat.feePolicy', params: {}, parts: {} },
    });
    render(<ResultDetail result={result({ claims: [fee], costs: costsOf(url, 535800, 'JPY') })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));
    expect(screen.getByTestId('cost-caveat')).toHaveTextContent(
      'Tuition is current with a caveat: fee policy page; no academic year printed.',
    );
  });

  it('U3: a fee with no caveat gets no caveat line', () => {
    const url = 'https://example.edu/fees';
    const fee = claim({ academic_year: '2027/2028', status: 'VERIFIED_CURRENT', is_stale: false, source_url: url, notes: 'Verified knowledge base.' });
    render(<ResultDetail result={result({ claims: [fee], costs: costsOf(url, 66720, 'USD') })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));
    expect(screen.queryByTestId('cost-caveat')).not.toBeInTheDocument();
  });

  it('U4: a per-semester and a per-programme fee are listed in Russian and Kazakh', () => {
    const semester = claim({
      id: 'eth', academic_year: null, status: 'VERIFIED_CURRENT', is_stale: false,
      normalized_value: { amount: 2190, currency: 'CHF' },
      notes: 'Verified knowledge base. Amount per semester, as published; not a yearly figure. '
        + 'Caveat: fee policy page; no academic year printed.',
    });
    const programme = claim({
      id: 'kth', academic_year: null, status: 'VERIFIED_CURRENT', is_stale: false,
      normalized_value: { amount: 453000, currency: 'SEK' },
      notes: 'Verified knowledge base. Amount per full programme (3 years), as published; not a yearly figure.',
    });
    const english = '2,190 CHF per semester, no academic year stated (published per semester, not as a yearly figure)';
    const gap = {
      computable: false, gap: null, gap_low: null, gap_high: null, total_cost: null, confirmed_aid: null,
      stackable_aid: null, year_mismatch: false, currency_mismatch: false, category_mismatch: false,
      cost_basis: null, missing_categories: [], warnings: [],
      reason: `An official tuition fee was found, but not as a current yearly figure for the fall 2027 intake: ${english}. `
        + "It is not used as this intake's cost, so the remaining cost is not computed.",
      reason_message: { key: 'gap.feeNotYearly', params: { intake: 'fall 2027', fees: english }, parts: {} },
    };
    act(() => setLocale('ru'));
    const { unmount } = render(
      <ResultDetail result={result({ claims: [semester, programme], funding_gap: gap })} knowledgeMode="kb" />,
    );
    fireEvent.click(screen.getByTestId('tab-costs'));
    const ruLine = '2,190 CHF за семестр, учебный год не указан (опубликовано за семестр, а не как годовая сумма)';
    expect(screen.getByTestId('unused-tuition')).toHaveTextContent(ruLine);
    expect(screen.getByTestId('unused-tuition')).toHaveTextContent('453,000 SEK за всю программу (лет: 3), учебный год не указан');
    expect(document.body).not.toHaveTextContent('per semester');
    expect(document.body).toHaveTextContent(`для набора fall 2027: ${ruLine}`);
    unmount();

    act(() => setLocale('kk'));
    render(<ResultDetail result={result({ claims: [semester], funding_gap: gap })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));
    expect(screen.getByTestId('unused-tuition')).toHaveTextContent(
      'семестр үшін 2,190 CHF, оқу жылы көрсетілмеген (семестр үшін жарияланған, жылдық сома ретінде емес)',
    );
    expect(document.body).not.toHaveTextContent('per semester');
  });

  it('U4: a stale fee in Russian keeps its localised reason', () => {
    act(() => setLocale('ru'));
    const fee = claim({
      stale_messages: [{ key: 'stale.yearBeforeIntake', params: { year: '2026/2027', intake: 'fall 2027', wanted: '2027/28' }, parts: {} }],
    });
    render(<ResultDetail result={result({ claims: [fee] })} knowledgeMode="kb" />);
    fireEvent.click(screen.getByTestId('tab-costs'));
    expect(screen.getByTestId('unused-tuition')).toHaveTextContent(
      '66,720 USD в год, учебный год 2026/2027 (не актуально: учебный год 2026/2027 раньше нужного для набора fall 2027 (2027/28))',
    );
  });
});

describe('U6 and U8 on the v18 KB (KB v18 smoke)', () => {
  afterEach(() => act(() => setLocale('en')));

  const KB_NO_FEE =
    'The verified knowledge base holds no tuition fee for this programme yet, so the remaining cost is not computed.';
  const CONFIRM = 'Confirm the fall 2027 fee with the university before relying on a cost figure.';
  const noFee = {
    computable: false,
    reason: KB_NO_FEE,
    reason_message: { key: 'gap.kbNoFee', params: {}, parts: {} },
    warnings: [CONFIRM],
    warning_messages: [{ key: 'gap.confirmIntakeFee', params: { intake: 'fall 2027' }, parts: {} }],
  };

  function openCosts(knowledgeMode: string) {
    const view = render(<ResultDetail result={result({ funding_gap: noFee })} knowledgeMode={knowledgeMode} />);
    fireEvent.click(screen.getByTestId('tab-costs'));
    return view;
  }

  it('U8: with no fee in the KB, the Costs tab says so in kb words', () => {
    openCosts('kb');
    expect(
      screen.getByText('No verified tuition fee in the knowledge base yet for this programme and intake.'),
    ).toBeInTheDocument();
    expect(document.body).toHaveTextContent(KB_NO_FEE);
    expect(document.body).toHaveTextContent(CONFIRM);
    expect(document.body).not.toHaveTextContent('could not be verified');
    expect(document.body).not.toHaveTextContent('No official cost of attendance was found');
  });

  it('U8: says it in Russian and Kazakh', () => {
    act(() => setLocale('ru'));
    const { unmount } = openCosts('kb');
    expect(document.body).toHaveTextContent('В проверенной базе знаний пока нет подтверждённой платы за обучение');
    expect(document.body).toHaveTextContent('В проверенной базе знаний пока нет платы за обучение для этой программы');
    expect(document.body).not.toHaveTextContent('knowledge base');
    unmount();

    act(() => setLocale('kk'));
    openCosts('kb');
    expect(document.body).toHaveTextContent(
      'Тексерілген білім базасында бұл бағдарлама мен қабылдау үшін расталған оқу ақысы әзірге жоқ.',
    );
    expect(document.body).toHaveTextContent('Тексерілген білім базасында бұл бағдарламаның оқу ақысы әзірге жоқ');
    expect(document.body).not.toHaveTextContent('knowledge base');
  });

  it('U8: keeps the live notice outside kb mode', () => {
    openCosts('live');
    expect(
      screen.getByText('No official cost of attendance was found for this programme and intake.'),
    ).toBeInTheDocument();
  });

  const STATEMENT = 'No English language test result is required for this route.';
  const none = question({
    topic: 'language requirement',
    question: `${STATEMENT} Does Stanford University ask for any other language evidence? The verified knowledge base names none.`,
    question_message: {
      key: 'question.languageNoneRecorded',
      params: { statement: STATEMENT, university: 'Stanford University' },
    },
    why_it_matters: 'Verified on the official page https://example.edu/faq: "No, we do not require any English proficiency exams."',
  });

  it('U6: no other language named, so nothing is asked "instead"', () => {
    render(<ResultDetail result={result({ unresolved: [none] })} knowledgeMode="kb" />);
    const questions = screen.getByTestId('requirement-questions');
    expect(questions).toHaveTextContent('Does Stanford University ask for any other language evidence?');
    expect(questions).not.toHaveTextContent('instead');
  });

  it('U6: asks it in Russian and Kazakh', () => {
    act(() => setLocale('ru'));
    const { unmount } = render(<ResultDetail result={result({ unresolved: [none] })} knowledgeMode="kb" />);
    expect(screen.getByTestId('requirement-questions')).toHaveTextContent(
      'Требует ли Stanford University какое-либо другое подтверждение знания языка?',
    );
    unmount();

    act(() => setLocale('kk'));
    render(<ResultDetail result={result({ unresolved: [none] })} knowledgeMode="kb" />);
    expect(screen.getByTestId('requirement-questions')).toHaveTextContent(
      'Stanford University басқа тіл білімін растайтын құжатты талап ете ме?',
    );
  });
});

describe('REL-1: no standalone CS bachelor is said, not asked', () => {
  afterEach(() => act(() => setLocale('en')));
  const URL_DS = 'https://www.lse.ac.uk/study-at-lse/undergraduate/bsc-data-science';
  const related = question({
    topic: 'official source',
    question: `No standalone bachelor's in Computer Science is published; the closest official route is BSc Data Science (N3UD) (official page: ${URL_DS}). Does that route suit you?`,
    question_message: { key: 'question.programmeRelatedOnly', params: { route: 'BSc Data Science (N3UD)', url: URL_DS } },
    why_it_matters: 'The verified knowledge base records no standalone bachelor\'s in Computer Science at Example University (expert check 2026-10-19). Whether the closest route suits you is your decision.',
    why_message: { key: 'why.programmeRelatedOnly', params: { university: 'Example University', date: '2026-10-19' } },
    suggested_contact: URL_DS,
  });
  const notOffered = question({
    topic: 'official source',
    question: 'Example University publishes no bachelor\'s in Computer Science (checked 2026-10-19).',
    question_message: { key: 'question.programmeNotOffered', params: { university: 'Example University', date: '2026-10-19' } },
    why_it_matters: `The closest official programme is BSc Data Science (N3UD) (official page: ${URL_DS}).`,
    why_message: { key: 'why.programmeNotOffered', params: { route: 'BSc Data Science (N3UD)', url: URL_DS } },
  });

  it('shows the related route and the "not offered" statement on the Requirements tab', () => {
    render(<ResultDetail result={result({ unresolved: [related, notOffered] })} knowledgeMode="kb" />);
    const block = screen.getByTestId('requirement-questions');
    expect(block).toHaveTextContent('the closest official route is BSc Data Science (N3UD)');
    expect(block).toHaveTextContent(URL_DS);
    expect(block).toHaveTextContent('Example University publishes no bachelor\'s in Computer Science (checked 2026-10-19).');
    expect(block).not.toHaveTextContent('Which official page publishes');
  });

  it('says both in Russian and Kazakh', () => {
    act(() => setLocale('ru'));
    const { unmount } = render(<ResultDetail result={result({ unresolved: [related, notOffered] })} knowledgeMode="kb" />);
    let block = screen.getByTestId('requirement-questions');
    expect(block).toHaveTextContent('ближайший официальный путь — BSc Data Science (N3UD)');
    expect(block).toHaveTextContent('Example University не публикует бакалавриат по Computer Science (проверено 2026-10-19).');
    unmount();

    act(() => setLocale('kk'));
    render(<ResultDetail result={result({ unresolved: [related, notOffered] })} knowledgeMode="kb" />);
    block = screen.getByTestId('requirement-questions');
    expect(block).toHaveTextContent('ең жақын ресми жол — BSc Data Science (N3UD)');
    expect(block).toHaveTextContent('Example University Computer Science бакалавриатын жарияламайды');
  });
});
