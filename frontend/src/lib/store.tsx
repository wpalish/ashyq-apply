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
const RUN_KEY = 'unimatch.activeRun';
const PROFILE_KEY = 'unimatch.activeProfile';

/** localStorage can throw in private windows; a missing value is never fatal. */
function readLocal(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
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
  newCase: () => void;
  /** True once a stored profile has been loaded back into the draft. */
  restored: boolean;
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
  retryRun: () => Promise<void>;
  collectDocuments: () => Promise<void>;
  decide: (resultId: string, decision: UserDecision, reason: string, notes: string) => Promise<void>;
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
  const pollRef = useRef<number | null>(null);

  const fail = useCallback((e: unknown) => {
    setError(e instanceof ApiError ? e.message : String(e));
  }, []);

  useEffect(() => {
    api.capabilities().then(setCapabilities).catch(fail);
    api.cases().then(setCases).catch(fail);
  }, [fail]);

  // Validation follows the draft, debounced so typing does not flood the API.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      api.validateProfile(profileDraft).then(setValidation).catch(() => setValidation(null));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [profileDraft]);

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
          setDraft(toDraft(stored));
          setRestored(true);
        })
        .catch(() => {
          // The profile is gone; forget the pointer rather than keep a stale one.
          writeLocal(PROFILE_KEY, null);
          writeLocal(RUN_KEY, null);
        });
    }
    const storedRun = readLocal(RUN_KEY);
    if (storedRun) {
      api.getRun(storedRun).then(setRun).catch(() => writeLocal(RUN_KEY, null));
    }
  }, []);

  // Poll while work is outstanding.
  //
  // A job that has been enqueued but not yet claimed is not "running", and the
  // run's stage does not move until a worker picks it up. Polling only on
  // `job_running` therefore stopped the moment work was requested — the UI sat
  // on a stale view while the worker was about to start.
  useEffect(() => {
    const jobOutstanding =
      run?.job_status === 'queued' || run?.job_status === 'running';
    const active =
      run &&
      (run.job_running ||
        jobOutstanding ||
        ['queued', 'profile_validation', 'candidate_discovery', 'program_verification',
         'funding_discovery', 'assessment', 'document_collection'].includes(run.stage));
    if (!active) {
      if (pollRef.current) window.clearInterval(pollRef.current);
      pollRef.current = null;
      return;
    }
    pollRef.current = window.setInterval(async () => {
      try {
        const next = await api.getRun(run.id);
        setRun(next);
        if (next.results_count !== results.length) {
          const [rows, sum] = await Promise.all([api.results(next.id), api.summary(next.id)]);
          setResults(rows);
          setSummary(sum);
        }
      } catch (e) {
        fail(e);
      }
    }, POLL_MS);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [run, results.length, fail]);

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
      const [stored, allRuns] = await Promise.all([api.getProfile(profileId), api.listRuns()]);
      const latest = allRuns.find((item) => item.profile_id === profileId) ?? null;
      setSavedProfile(stored);
      setDraft(toDraft(stored));
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
    setDraft(blankProfile());
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
      const started = await api.startRun(profile.id, demoMode);
      setRun(started);
      setResults([]);
      setSummary(null);
      writeLocal(RUN_KEY, started.id);
    } catch (e) {
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

  const retryRun = useCallback(async () => {
    if (!run) return;
    try {
      setRun(await api.retryRun(run.id));
      setResults([]);
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
      loadDemoProfile, clearProfile, validation, run, results,
      summary, loading, error, saveProfile, startRun, cancelRun, retryRun, collectDocuments,
      decide, refreshResults, deleteEverything, clearError: () => setError(null),
    }),
    [capabilities, profileDraft, setProfileDraft, savedProfile, cases, switchCase, newCase,
     restored, loadDemoProfile,
     clearProfile, validation, run, results, summary, loading, error, saveProfile, startRun,
     cancelRun, retryRun, collectDocuments, decide, refreshResults, deleteEverything],
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): Store {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore must be used inside <StoreProvider>');
  return ctx;
}
