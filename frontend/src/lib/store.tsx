/**
 * Application state.
 *
 * One context holding the profile draft, the active run and the results.
 * Deliberately hand-rolled: the app has a single linear workflow and one
 * server, so a store library would add a dependency without removing any code.
 */

import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState,
  type ReactNode,
} from 'react';
import { ApiError, api } from '@/api/client';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import type {
  ApplicantCase, Capabilities, ProfileValidationReport, ProgramResult, RunView,
  ShortlistSummary, StoredProfile, UserDecision,
} from '@/types';

const POLL_MS = 1200;
//: Unsaved edits, kept apart from the saved profile on purpose. Restoring a
//: draft must never overwrite `savedProfile`: doing exactly that is how demo
//: data once landed on top of a real applicant's record.
const DRAFT_KEY = 'ashyq.unsavedDraft';
//: Backoff after consecutive polling failures, capped so a recovered backend
//: is noticed within fifteen seconds.
const POLL_BACKOFF_MS = [1200, 2400, 5000, 15000];
const RUN_KEY = 'ashyq.activeRun';
const PROFILE_KEY = 'ashyq.activeProfile';

/**
 * Keys were `unimatch.*` before the product was named. Renaming them without a
 * migration would have silently signed everyone out of their own case on the
 * next visit, so the old key is read once and rewritten under the new name.
 */
export function legacyKey(key: string): string {
  return key.replace(/^ashyq\./, 'unimatch.');
}

/** localStorage can throw in private windows; a missing value is never fatal. */
function readLocal(key: string): string | null {
  try {
    const current = window.localStorage.getItem(key);
    if (current !== null) return current;
    const legacy = window.localStorage.getItem(legacyKey(key));
    if (legacy === null) return null;
    window.localStorage.setItem(key, legacy);
    window.localStorage.removeItem(legacyKey(key));
    return legacy;
  } catch {
    return null;
  }
}
function writeLocal(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* storage unavailable — state still lives in memory for this session */
  }
}

export interface Store {
  capabilities: Capabilities | null;
  profileDraft: Record<string, unknown>;
  setProfileDraft: (updater: (d: Record<string, unknown>) => Record<string, unknown>) => void;
  savedProfile: StoredProfile | null;
  cases: ApplicantCase[];
  switchCase: (profileId: string) => Promise<void>;
  /** True when the draft differs from the profile it was loaded from. */
  dirty: boolean;
  /** An unsaved draft was restored from this browser after a reload. */
  draftRestored: boolean;
  discardDraft: () => void;
  newCase: () => void;
  /** True once a stored profile has been loaded back into the draft. */
  restored: boolean;
  /**
   * True once the initial restore has finished, whether or not there was
   * anything to restore. Anything that judges the app's state - a deep link
   * against the screen gates, say - must wait for this, or it judges an empty
   * store and concludes there are no results a moment before they arrive.
   */
  hydrated: boolean;
  loadDemoProfile: () => void;
  clearProfile: () => void;
  validation: ProfileValidationReport | null;
  run: RunView | null;
  results: ProgramResult[];
  summary: ShortlistSummary | null;
  loading: boolean;
  error: string | null;
  saveProfile: () => Promise<void>;
  startRun: (demoMode: boolean) => Promise<void>;
  cancelRun: () => Promise<void>;
  retryRun: (stage?: string) => Promise<void>;
  recheckNow: () => Promise<void>;
  collectDocuments: () => Promise<void>;
  decide: (resultId: string, decision: UserDecision, reason: string, notes: string) => Promise<void>;
  saveNotes: (resultId: string, notes: string) => Promise<void>;
  refreshResults: () => Promise<void>;
  deleteEverything: () => Promise<void>;
  clearError: () => void;
}

const StoreContext = createContext<Store | null>(null);

/**
 * A stored profile back into an editable draft.
 *
 * The server wraps the profile with id/created_at/updated_at; those are not
 * part of the editable document and the API rejects them on write.
 */
const SERVER_ONLY_FIELDS = ['id', 'created_at', 'updated_at'] as const;

export function toDraft(stored: StoredProfile): Record<string, unknown> {
  const draft: Record<string, unknown> = { ...stored };
  for (const key of SERVER_ONLY_FIELDS) delete draft[key];
  return draft;
}

/** An empty profile: the shape of DEFAULT_PROFILE with nothing filled in. */
export function blankProfile(): Record<string, unknown> {
  const base = structuredClone(DEFAULT_PROFILE) as Record<string, unknown>;
  const context = base.context as Record<string, unknown>;
  return {
    ...base,
    display_name: "New applicant",
    context: {
      ...context,
      intended_fields: [],
      citizenship: '',
      country_of_residence: '',
      education_country: '',
      education_system: '',
      graduation_date: null,
      second_citizenship: null,
    },
    academics: {
      ...(base.academics as Record<string, unknown>),
      gpa: null,
      class_rank: null,
      class_size: null,
      sat: { total: null, math: null, reading_writing: null,
             dates: { taken_on: null, planned_retake_on: null },
             status: "applicant_confirmed" },
      ielts: { overall: null, listening: null, reading: null, writing: null, speaking: null,
               test_type: "academic", dates: { taken_on: null, planned_retake_on: null },
               status: "applicant_confirmed" },
      planned_retakes: [],
    },
    activities: [],
    achievements: [],
  };
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [profileDraft, setDraft] = useState<Record<string, unknown>>(
    () => structuredClone(DEFAULT_PROFILE) as Record<string, unknown>,
  );
  const [savedProfile, setSavedProfile] = useState<StoredProfile | null>(null);
  const [cases, setCases] = useState<ApplicantCase[]>([]);
  const [validation, setValidation] = useState<ProfileValidationReport | null>(null);
  const [run, setRun] = useState<RunView | null>(null);
  const [results, setResults] = useState<ProgramResult[]>([]);
  const [summary, setSummary] = useState<ShortlistSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restored, setRestored] = useState(false);
  const [draftRestored, setDraftRestored] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  //: What the draft looked like when it was last saved or loaded. Comparing
  //: against this is what makes "unsaved changes" a fact rather than a guess.
  const [baseline, setBaseline] = useState<string>('');
  const pollRef = useRef<number | null>(null);
  //: One request at a time: a slow answer used to overlap the next tick.
  const inFlightRef = useRef(false);
  const pollFailuresRef = useRef(0);
  const resultsCountRef = useRef(0);

  const fail = useCallback((e: unknown) => {
    setError(e instanceof ApiError ? e.message : String(e));
  }, []);

  useEffect(() => {
    api.capabilities().then(setCapabilities).catch(fail);
    api.cases().then(setCases).catch(fail);
  }, [fail]);

  const dirty = baseline !== '' && JSON.stringify(profileDraft) !== baseline;

  // Autosave the unsaved draft, debounced. Stored under its own key: the
  // saved profile is never touched by this, so restoring a draft cannot
  // overwrite the applicant's record the way loading demo data once did.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (dirty) writeLocal(DRAFT_KEY, JSON.stringify(profileDraft));
      else writeLocal(DRAFT_KEY, null);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [profileDraft, dirty]);

  const discardDraft = useCallback(() => {
    writeLocal(DRAFT_KEY, null);
    setDraftRestored(false);
    if (savedProfile) setDraft(toDraft(savedProfile));
  }, [savedProfile]);

  // Validation follows the draft, debounced so typing does not flood the API.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      api.validateProfile(profileDraft).then(setValidation).catch(() => setValidation(null));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [profileDraft]);

  const saveNotes = useCallback(async (resultId: string, notes: string) => {
    if (!run) return;
    try {
      const updated = await api.saveNotes(run.id, resultId, notes);
      setResults((rows) => rows.map((r) => (r.id === resultId ? updated : r)));
    } catch (e) {
      fail(e);
    }
  }, [run, fail]);

  const refreshResults = useCallback(async () => {
    if (!run) return;
    try {
      const [rows, sum] = await Promise.all([api.results(run.id), api.summary(run.id)]);
      setResults(rows);
      setSummary(sum);
    } catch (e) {
      fail(e);
    }
  }, [run, fail]);

  // Restore the saved profile and any in-flight run after a reload.
  //
  // The draft must be hydrated from the stored payload, not left as the
  // synthetic default. Leaving it meant the next save wrote demo data over the
  // applicant's real profile - silent data loss, and the worst defect found in
  // this build.
  useEffect(() => {
    const profileId = readLocal(PROFILE_KEY);
    if (profileId) {
      api.getProfile(profileId)
        .then((stored) => {
          setSavedProfile(stored);
          const fromServer = toDraft(stored);
          setBaseline(JSON.stringify(fromServer));
          // The saved profile is the baseline; an unsaved draft is layered on
          // top of it and never written back into savedProfile. That ordering
          // is what stops a restored draft overwriting the real record.
          const pending = readLocal(DRAFT_KEY);
          if (pending) {
            try {
              setDraft(JSON.parse(pending) as Record<string, unknown>);
              setDraftRestored(true);
            } catch {
              writeLocal(DRAFT_KEY, null);
              setDraft(fromServer);
            }
          } else {
            setDraft(fromServer);
          }
          setRestored(true);
        })
        .catch(() => {
          // The profile is gone; forget the pointer rather than keep a stale one.
          writeLocal(PROFILE_KEY, null);
          writeLocal(RUN_KEY, null);
        });
    }
    const storedRun = readLocal(RUN_KEY);
    const runLoaded = storedRun
      ? api.getRun(storedRun)
          .then((stored) => { setRun(stored); return api.results(stored.id); })
          .then(setResults)
          .catch(() => writeLocal(RUN_KEY, null))
      : Promise.resolve();
    void runLoaded.finally(() => setHydrated(true));
  }, []);

  // Poll while work is outstanding.
  //
  // A job that has been enqueued but not yet claimed is not "running", and the
  // run's stage does not move until a worker picks it up. Polling only on
  // `job_running` therefore stopped the moment work was requested.
  //
  // The loop is a chain of timeouts rather than an interval, and it depends on
  // the run *id* and whether work is outstanding — not on the run object. The
  // old effect listed `run` and `results.length` in its dependencies, so every
  // tick tore the interval down and built a new one, and a slow response could
  // overlap the next request.
  const jobOutstanding = run?.job_status === 'queued' || run?.job_status === 'running';
  const pollingActive = Boolean(
    run &&
      (run.job_running ||
        jobOutstanding ||
        ['queued', 'profile_validation', 'candidate_discovery', 'program_verification',
         'funding_discovery', 'assessment', 'document_collection'].includes(run.stage)),
  );
  const runId = run?.id ?? null;

  useEffect(() => {
    resultsCountRef.current = results.length;
  }, [results.length]);

  useEffect(() => {
    if (!runId || !pollingActive) return;
    let stopped = false;

    const schedule = (delay: number) => {
      if (stopped) return;
      pollRef.current = window.setTimeout(tick, delay);
    };

    const tick = async () => {
      // A hidden tab is not watching. Skipping the request rather than the
      // schedule means the loop resumes the moment it comes back.
      if (document.hidden || inFlightRef.current) {
        schedule(POLL_MS);
        return;
      }
      inFlightRef.current = true;
      try {
        const next = await api.getRun(runId);
        if (stopped) return;
        pollFailuresRef.current = 0;
        setRun(next);
        const settled = ['awaiting_user_decision', 'completed', 'failed', 'cancelled']
          .includes(next.stage);
        if (next.results_count !== resultsCountRef.current || settled) {
          const [rows, sum] = await Promise.all([api.results(next.id), api.summary(next.id)]);
          if (stopped) return;
          setResults(rows);
          setSummary(sum);
        }
        schedule(POLL_MS);
      } catch (e) {
        pollFailuresRef.current += 1;
        // One dropped poll is not worth a banner; a run of them is. Backing
        // off also stops a dead backend being hammered every 1.2 seconds.
        if (pollFailuresRef.current > 3) fail(e);
        const step = Math.min(pollFailuresRef.current - 1, POLL_BACKOFF_MS.length - 1);
        schedule(POLL_BACKOFF_MS[step] ?? POLL_MS);
      } finally {
        inFlightRef.current = false;
      }
    };

    const onVisible = () => {
      if (document.hidden) return;
      // Back in view: answer now rather than at the end of the current wait.
      if (pollRef.current) window.clearTimeout(pollRef.current);
      schedule(0);
    };

    document.addEventListener('visibilitychange', onVisible);
    schedule(POLL_MS);
    return () => {
      stopped = true;
      document.removeEventListener('visibilitychange', onVisible);
      if (pollRef.current) window.clearTimeout(pollRef.current);
      pollRef.current = null;
    };
  }, [runId, pollingActive, fail]);

  // Pull the final results once the pipeline settles.
  useEffect(() => {
    if (run && ['awaiting_user_decision', 'completed'].includes(run.stage) && !run.job_running) {
      refreshResults();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run?.stage, run?.job_running]);

  const setProfileDraft = useCallback(
    (updater: (d: Record<string, unknown>) => Record<string, unknown>) => setDraft((d) => updater(d)),
    [],
  );

  const saveProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const saved = savedProfile
        ? await api.updateProfile(savedProfile.id, profileDraft)
        : await api.createProfile(profileDraft);
      setSavedProfile(saved);
      setCases(await api.cases());
      writeLocal(PROFILE_KEY, saved.id);
      setBaseline(JSON.stringify(toDraft(saved)));
      setDraftRestored(false);
      writeLocal(DRAFT_KEY, null);
    } catch (e) {
      fail(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [profileDraft, savedProfile, fail]);

  const switchCase = useCallback(async (profileId: string) => {
    setLoading(true);
    setError(null);
    try {
      const [stored, runsForCase] = await Promise.all([
        api.getProfile(profileId),
        api.listRuns(profileId, 1),
      ]);
      const latest = runsForCase[0] ?? null;
      setSavedProfile(stored);
      setDraft(toDraft(stored));
      setBaseline(JSON.stringify(toDraft(stored)));
      setDraftRestored(false);
      writeLocal(DRAFT_KEY, null);
      setRun(latest);
      writeLocal(PROFILE_KEY, profileId);
      writeLocal(RUN_KEY, latest?.id ?? null);
      if (latest) {
        const [rows, sum] = await Promise.all([api.results(latest.id), api.summary(latest.id)]);
        setResults(rows);
        setSummary(sum);
      } else {
        setResults([]);
        setSummary(null);
      }
    } catch (e) {
      fail(e);
    } finally {
      setLoading(false);
    }
  }, [fail]);

  const newCase = useCallback(() => {
    setSavedProfile(null);
    const blank = blankProfile();
    setDraft(blank);
    setBaseline(JSON.stringify(blank));
    setDraftRestored(false);
    writeLocal(DRAFT_KEY, null);
    setRun(null);
    setResults([]);
    setSummary(null);
    setValidation(null);
    writeLocal(PROFILE_KEY, null);
    writeLocal(RUN_KEY, null);
  }, []);

  const startRun = useCallback(async (demoMode: boolean) => {
    setLoading(true);
    setError(null);
    try {
      let profile = savedProfile;
      if (!profile) {
        profile = await api.createProfile(profileDraft);
        setSavedProfile(profile);
        setCases(await api.cases());
        writeLocal(PROFILE_KEY, profile.id);
      } else {
        await api.updateProfile(profile.id, profileDraft);
      }
      const started = await api.startRun(profile.id, demoMode, crypto.randomUUID());
      setRun(started);
      setResults([]);
      setSummary(null);
      writeLocal(RUN_KEY, started.id);
    } catch (e) {
      // 409 means this applicant is already being researched. Joining that run
      // is what the user wanted; reporting an error would be pedantry.
      const active = e instanceof ApiError && e.status === 409
        ? /run ([0-9a-f]{32})/.exec(e.message)?.[1]
        : undefined;
      if (active) {
        try {
          setRun(await api.getRun(active));
          setResults([]);
          setSummary(null);
          writeLocal(RUN_KEY, active);
          return;
        } catch (joinError) {
          fail(joinError);
          return;
        }
      }
      fail(e);
    } finally {
      setLoading(false);
    }
  }, [profileDraft, savedProfile, fail]);

  const cancelRun = useCallback(async () => {
    if (!run) return;
    try {
      setRun(await api.cancelRun(run.id));
    } catch (e) {
      fail(e);
    }
  }, [run, fail]);

  const retryRun = useCallback(async (stage?: string) => {
    if (!run) return;
    try {
      // Results are no longer wiped: the server upserts rows and keeps the
      // user's decisions, so clearing them here would only make a healthy
      // shortlist blink out of existence until the next poll.
      setRun(await api.retryRun(run.id, stage));
    } catch (e) {
      fail(e);
    }
  }, [run, fail]);

  const recheckNow = useCallback(async () => {
    if (!run) return;
    try {
      setRun(await api.recheckNow(run.id));
    } catch (e) {
      fail(e);
    }
  }, [run, fail]);

  const collectDocuments = useCallback(async () => {
    if (!run) return;
    setError(null);
    try {
      setRun(await api.collectDocuments(run.id));
    } catch (e) {
      fail(e);
    }
  }, [run, fail]);

  const decide = useCallback(
    async (resultId: string, decision: UserDecision, reason: string, notes: string) => {
      if (!run) return;
      try {
        const updated = await api.decide(run.id, resultId, decision, reason, notes);
        setResults((rows) => rows.map((r) => (r.id === resultId ? updated : r)));
        setSummary(await api.summary(run.id));
      } catch (e) {
        fail(e);
      }
    },
    [run, fail],
  );

  const deleteEverything = useCallback(async () => {
    if (!savedProfile) return;
    try {
      await api.deleteProfile(savedProfile.id);
      setSavedProfile(null);
      setRun(null);
      setResults([]);
      setSummary(null);
      writeLocal(RUN_KEY, null);
      writeLocal(PROFILE_KEY, null);
      setCases(await api.cases());
    } catch (e) {
      fail(e);
    }
  }, [savedProfile, fail]);

  const loadDemoProfile = useCallback(() => {
    setDraft(structuredClone(DEFAULT_PROFILE) as Record<string, unknown>);
  }, []);

  const clearProfile = useCallback(() => {
    setDraft(blankProfile());
  }, []);

  const value = useMemo<Store>(
    () => ({
      capabilities, profileDraft, setProfileDraft, savedProfile, cases, switchCase, newCase, restored,
      dirty, draftRestored, discardDraft, hydrated,
      loadDemoProfile, clearProfile, validation, run, results,
      summary, loading, error, saveProfile, startRun, cancelRun, retryRun, recheckNow, collectDocuments,
      decide, saveNotes, refreshResults, deleteEverything, clearError: () => setError(null),
    }),
    [capabilities, profileDraft, setProfileDraft, savedProfile, cases, switchCase, newCase,
     restored, dirty, draftRestored, discardDraft, hydrated, loadDemoProfile,
     clearProfile, validation, run, results, summary, loading, error, saveProfile, startRun,
     cancelRun, retryRun, recheckNow, collectDocuments, decide, saveNotes, refreshResults,
     deleteEverything],
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): Store {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore must be used inside <StoreProvider>');
  return ctx;
}
