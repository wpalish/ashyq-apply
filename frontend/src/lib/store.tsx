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
import { ApiError, api, isPaymentRequired } from '@/api/client';
import { DEFAULT_PROFILE } from '@/lib/defaultProfile';
import { useProfileValidation, type ValidationStatus } from '@/lib/useProfileValidation';
import {
  adoptPointer, clearDraftSlot, isLocalCaseKey, migrateLegacyDraft, newLocalCaseKey,
  readDraftEnvelope, writeDraftEnvelope, writePointer,
} from '@/lib/caseDrafts';
import type {
  ApplicantCase, BalancedShortlist, Capabilities, ProfileValidationReport, ProgramResult,
  RerankIn, RunView, ShortlistSummary, StoredProfile, UserDecision,
} from '@/types';

const POLL_MS = 1200;
//: Backoff after consecutive polling failures, capped so a recovered backend
//: is noticed within fifteen seconds.
const POLL_BACKOFF_MS = [1200, 2400, 5000, 15000];

/**
 * Unsaved edits are persisted per case and the active case/run pointers are
 * per-tab; both live in `./caseDrafts`. Restoring a draft must never overwrite
 * `savedProfile`: doing exactly that is how demo data once landed on top of a
 * real applicant's record.
 */
export { legacyKey } from '@/lib/caseDrafts';

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
  validationStatus: ValidationStatus;
  retryValidation: () => void;
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
  /** Downloads through the client, so a 402 raises the paywall like any call. */
  exportShortlist: (fmt: 'csv' | 'json' | 'xlsx', decision?: string) => Promise<void>;
  decide: (resultId: string, decision: UserDecision, reason: string, notes: string) => Promise<void>;
  saveNotes: (resultId: string, notes: string) => Promise<void>;
  refreshResults: () => Promise<void>;
  /** Re-order the finished run against changed priorities. Fetches no pages. */
  rerank: (body: RerankIn) => Promise<void>;
  /** The balanced list, refreshed with the results. */
  shortlist: BalancedShortlist | null;
  deleteEverything: () => Promise<void>;
  clearError: () => void;
  /** Set when a gated route answered 402. Null when nothing is locked. */
  paywall: { profileId: string; priceKzt: number; casesLeft: number | null } | null;
  clearPaywall: () => void;
  /** Open one case out of the organization's subscription quota. */
  unlockFromSubscription: (profileId: string) => Promise<void>;
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
  const [run, setRun] = useState<RunView | null>(null);
  const [results, setResults] = useState<ProgramResult[]>([]);
  const [shortlist, setShortlist] = useState<BalancedShortlist | null>(null);
  const [summary, setSummary] = useState<ShortlistSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restored, setRestored] = useState(false);
  const [paywall, setPaywall] = useState<
    { profileId: string; priceKzt: number; casesLeft: number | null } | null
  >(null);
  const [draftRestored, setDraftRestored] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const { validation, validationStatus, retryValidation } = useProfileValidation(profileDraft, hydrated);
  //: What the draft looked like when it was last saved or loaded. Comparing
  //: against this is what makes "unsaved changes" a fact rather than a guess.
  const [baseline, setBaseline] = useState<string>('');
  //: Key of a case that exists only in this browser until its first save. Null
  //: while no such case is open; a saved case is keyed by its profile id.
  const [localCaseKey, setLocalCaseKey] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);
  //: One request at a time: a slow answer used to overlap the next tick.
  const inFlightRef = useRef(false);
  const pollFailuresRef = useRef(0);
  const resultsCountRef = useRef(0);
  //: Monotonic generation for async case actions (initial hydration,
  //: switchCase, saveProfile, startRun). An action that started before a newer
  //: one must discard its answer whole - state, pointers and draft slots - or
  //: a late response for case A would land on top of case B.
  const opGenRef = useRef(0);
  //: Monotonic counter of initial-hydration passes (StrictMode mounts twice).
  //: Kept apart from opGenRef so a pass superseded by a user action still
  //: releases the `hydrated` gate once its own requests have settled.
  const hydrationPassRef = useRef(0);
  const activeCaseKey: string | null = savedProfile?.id ?? localCaseKey;

  const fail = useCallback((e: unknown) => {
    // A 401 is not something the user can act on from this screen. AuthGate
    // asks /api/auth/status once, at mount, so a session that expires mid-use
    // otherwise became "Something went wrong. Authentication required." on a
    // page with no way back to signing in. Reloading remounts AuthGate, which
    // re-asks and renders the sign-in form. The guard lives here because all
    // thirteen error paths already route through `fail`; putting it at the
    // call sites would leave whichever one was added next still broken.
    if (e instanceof ApiError && e.status === 401) {
      window.location.reload();
      return;
    }
    // A 402 is not a failure to report — it is an offer to make. Checked after
    // 401 for the same reason: an expired session cannot be sold anything.
    if (isPaymentRequired(e)) {
      setPaywall({
        profileId: e.profileId,
        priceKzt: e.priceKzt,
        casesLeft: e.subscriptionCasesLeft ?? null,
      });
      return;
    }
    setError(e instanceof ApiError ? e.message : String(e));
  }, []);

  useEffect(() => {
    api.capabilities().then(setCapabilities).catch(fail);
    api.cases().then(setCases).catch(fail);
  }, [fail]);

  const dirty = baseline !== '' && JSON.stringify(profileDraft) !== baseline;

  // Autosave the unsaved draft, debounced, into the active case's own slot.
  // The saved profile is never touched by this, so restoring a draft cannot
  // overwrite the applicant's record the way loading demo data once did.
  //
  // Gated on hydration: until the initial restore has settled, this effect
  // must not write OR clear any draft slot. On mount the draft is clean, so a
  // tick that fired while a slow getProfile was still pending used to wipe
  // the very slot the restore was about to read (FE02).
  useEffect(() => {
    if (!hydrated || activeCaseKey === null) return;
    const timer = window.setTimeout(() => {
      if (dirty) writeDraftEnvelope(activeCaseKey, profileDraft, savedProfile?.updated_at ?? null);
      // A restored draft's baseline IS its envelope, so a clean restored draft
      // looks "nothing to keep". On a local case the slot is the only copy of
      // those edits, so clearing it here would lose them on the next reload;
      // the slot retires on a successful save or an explicit discard instead.
      else if (!(isLocalCaseKey(activeCaseKey) && draftRestored)) clearDraftSlot(activeCaseKey);
    }, 600);
    return () => window.clearTimeout(timer);
  }, [profileDraft, dirty, hydrated, activeCaseKey, savedProfile, draftRestored]);

  const discardDraft = useCallback(() => {
    if (activeCaseKey !== null) clearDraftSlot(activeCaseKey);
    setDraftRestored(false);
    if (savedProfile) setDraft(toDraft(savedProfile));
  }, [activeCaseKey, savedProfile]);


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

  const rerank = useCallback(
    async (body: RerankIn) => {
      if (!run) return;
      try {
        await api.rerank(run.id, body);
        setResults(await api.results(run.id));
      } catch (e) {
        fail(e);
      }
    },
    [run, fail],
  );

  // Restore the active case and any in-flight run after a reload.
  //
  // The draft must be hydrated from the stored payload, not left as the
  // synthetic default. Leaving it meant the next save wrote demo data over the
  // applicant's real profile - silent data loss, and the worst defect found in
  // this build.
  //
  // The active case is resolved per tab: a server profile id, or a local key
  // for a case this browser has not saved yet. A per-case draft envelope is
  // applied only when its case_key names the case being hydrated, and `hydrated`
  // waits for BOTH initial requests (profile and run) to settle. A 404 proves
  // the case is gone and forgets it; any other failure is treated as transient:
  // the pointers stay so a retry can find the case again.
  useEffect(() => {
    const gen = ++opGenRef.current;
    const stale = () => gen !== opGenRef.current;
    const pass = ++hydrationPassRef.current;

    const profilePointer = adoptPointer('profile');
    const runPointer = adoptPointer('run');
    // The pre-upgrade bare draft slot is re-wrapped under the case it was
    // written for; the legacy keys are removed in the same pass.
    migrateLegacyDraft(
      profilePointer !== null && !isLocalCaseKey(profilePointer) ? profilePointer : null,
    );

    let profileLoaded: Promise<void>;
    if (profilePointer === null) {
      profileLoaded = Promise.resolve();
    } else if (isLocalCaseKey(profilePointer)) {
      // A case this browser has not saved yet: its unsaved edits are the only
      // thing to restore, and no server round-trip is involved.
      profileLoaded = Promise.resolve().then(() => {
        if (stale()) return;
        setLocalCaseKey(profilePointer);
        const envelope = readDraftEnvelope(profilePointer);
        if (envelope) {
          setDraft(envelope.draft);
          setBaseline(JSON.stringify(envelope.draft));
          setDraftRestored(true);
        } else {
          const blank = blankProfile();
          setDraft(blank);
          setBaseline(JSON.stringify(blank));
        }
      });
    } else {
      profileLoaded = api.getProfile(profilePointer)
        .then((stored) => {
          if (stale()) return;
          setSavedProfile(stored);
          const fromServer = toDraft(stored);
          // The saved profile is the baseline; an unsaved draft is layered on
          // top of it and never written back into savedProfile. That ordering
          // is what stops a restored draft overwriting the real record.
          setBaseline(JSON.stringify(fromServer));
          const envelope = readDraftEnvelope(profilePointer);
          if (envelope) {
            setDraft(envelope.draft);
            setDraftRestored(true);
          } else {
            setDraft(fromServer);
          }
          setRestored(true);
        })
        .catch((e: unknown) => {
          if (stale()) return;
          if (e instanceof ApiError && e.status === 404) {
            // Proven absence, not a failure to report: forget the case, its
            // pointer and its draft slot rather than keep a stale one.
            writePointer('profile', null);
            writePointer('run', null);
            clearDraftSlot(profilePointer);
          } else {
            // Transient (network, 5xx) — or 401/402, which `fail` routes to
            // the reload/paywall paths. The pointers survive so a retry - the
            // next reload - can find the case again.
            fail(e);
          }
        });
    }

    const runLoaded = runPointer === null
      ? Promise.resolve()
      : api.getRun(runPointer)
          .then((stored) => {
            if (stale()) return;
            setRun(stored);
            return api.results(stored.id).then((rows) => {
              if (stale()) return;
              setResults(rows);
            });
          })
          .catch((e: unknown) => {
            if (stale()) return;
            if (e instanceof ApiError && e.status === 404) {
              writePointer('run', null);
            } else {
              fail(e);
            }
          });

    void Promise.all([profileLoaded, runLoaded]).finally(() => {
      if (pass === hydrationPassRef.current) setHydrated(true);
    });
  }, [fail]);

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
    const gen = ++opGenRef.current;
    // The draft moves from its previous case key (a local case key on the very
    // first save) to the saved profile id, so the old slot is retired with it.
    const previousCaseKey = savedProfile?.id ?? localCaseKey;
    setLoading(true);
    setError(null);
    try {
      const saved = savedProfile
        ? await api.updateProfile(savedProfile.id, profileDraft)
        : await api.createProfile(profileDraft);
      const nextCases = await api.cases();
      if (gen !== opGenRef.current) return;
      setSavedProfile(saved);
      setCases(nextCases);
      setLocalCaseKey(null);
      writePointer('profile', saved.id);
      setBaseline(JSON.stringify(toDraft(saved)));
      setDraftRestored(false);
      if (previousCaseKey !== null) clearDraftSlot(previousCaseKey);
    } catch (e) {
      if (gen === opGenRef.current) fail(e);
      throw e;
    } finally {
      if (gen === opGenRef.current) setLoading(false);
    }
  }, [profileDraft, savedProfile, localCaseKey, fail]);

  const switchCase = useCallback(async (profileId: string) => {
    const gen = ++opGenRef.current;
    setLoading(true);
    setError(null);
    try {
      const [stored, runsForCase] = await Promise.all([
        api.getProfile(profileId),
        api.listRuns(profileId, 1),
      ]);
      // A newer case action (another switch, a save, a run) has started since
      // this one: discard the answer whole rather than land case A on top of B.
      if (gen !== opGenRef.current) return;
      const latest = runsForCase[0] ?? null;
      setSavedProfile(stored);
      setLocalCaseKey(null);
      const fromServer = toDraft(stored);
      setBaseline(JSON.stringify(fromServer));
      // The case being opened gets its own unsaved edits back; the case being
      // left keeps them in its own slot for the same reason.
      const envelope = readDraftEnvelope(profileId);
      if (envelope) {
        setDraft(envelope.draft);
        setDraftRestored(true);
      } else {
        setDraft(fromServer);
        setDraftRestored(false);
      }
      setRun(latest);
      writePointer('profile', profileId);
      writePointer('run', latest?.id ?? null);
      if (latest) {
        const [rows, sum] = await Promise.all([api.results(latest.id), api.summary(latest.id)]);
        if (gen !== opGenRef.current) return;
        setResults(rows);
        setSummary(sum);
      } else {
        setResults([]);
        setSummary(null);
      }
    } catch (e) {
      if (gen === opGenRef.current) fail(e);
    } finally {
      if (gen === opGenRef.current) setLoading(false);
    }
  }, [fail]);

  const newCase = useCallback(() => {
    // Invalidate an in-flight switch/save/run: the later user intent wins, and
    // a slow response must not land an old case on top of the fresh blank one.
    ++opGenRef.current;
    // The new case exists only in this browser until its first save; its key
    // is local so its unsaved edits get their own draft slot (FE01).
    const localId = newLocalCaseKey();
    setSavedProfile(null);
    setLocalCaseKey(localId);
    const blank = blankProfile();
    setDraft(blank);
    setBaseline(JSON.stringify(blank));
    setDraftRestored(false);
    setRun(null);
    setResults([]);
    setSummary(null);
    writePointer('profile', localId);
    writePointer('run', null);
  }, []);

  const startRun = useCallback(async (demoMode: boolean) => {
    const gen = ++opGenRef.current;
    setLoading(true);
    setError(null);
    try {
      let profile = savedProfile;
      if (!profile) {
        const previousCaseKey = localCaseKey;
        profile = await api.createProfile(profileDraft);
        const nextCases = await api.cases();
        if (gen !== opGenRef.current) return;
        setSavedProfile(profile);
        setCases(nextCases);
        setLocalCaseKey(null);
        writePointer('profile', profile.id);
        if (previousCaseKey !== null) clearDraftSlot(previousCaseKey);
      } else {
        await api.updateProfile(profile.id, profileDraft);
        if (gen !== opGenRef.current) return;
      }
      const started = await api.startRun(profile.id, demoMode, crypto.randomUUID());
      if (gen !== opGenRef.current) return;
      setRun(started);
      setResults([]);
      setSummary(null);
      writePointer('run', started.id);
    } catch (e) {
      // 409 means this applicant is already being researched. Joining that run
      // is what the user wanted; reporting an error would be pedantry.
      const active = e instanceof ApiError && e.status === 409
        ? /run ([0-9a-f]{32})/.exec(e.message)?.[1]
        : undefined;
      if (active) {
        try {
          const joined = await api.getRun(active);
          if (gen !== opGenRef.current) return;
          setRun(joined);
          setResults([]);
          setSummary(null);
          writePointer('run', active);
          return;
        } catch (joinError) {
          if (gen === opGenRef.current) fail(joinError);
          return;
        }
      }
      if (gen === opGenRef.current) fail(e);
    } finally {
      if (gen === opGenRef.current) setLoading(false);
    }
  }, [profileDraft, savedProfile, localCaseKey, fail]);

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

  const exportShortlist = useCallback(
    async (fmt: 'csv' | 'json' | 'xlsx', decision?: string) => {
      if (!run) return;
      setError(null);
      try {
        await api.downloadExport(run.id, fmt, decision);
      } catch (e) {
        fail(e);
      }
    },
    [run, fail],
  );

  // Takes the case rather than reading the paywall state, so the caller that
  // rendered the button and the action that spends the unit cannot disagree.
  const unlockFromSubscription = useCallback(
    async (profileId: string) => {
      setError(null);
      try {
        await api.unlockFromSubscription(profileId);
        setPaywall(null);
        await refreshResults();
      } catch (e) {
        fail(e);
      }
    },
    [fail, refreshResults],
  );

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

  // The balanced list is derived from the rows, so it follows them rather than
  // every call site that loads results having to remember to ask for it too.
  useEffect(() => {
    if (!run || results.length === 0) {
      setShortlist(null);
      return;
    }
    let cancelled = false;
    api.shortlist(run.id)
      .then((list) => { if (!cancelled) setShortlist(list); })
      .catch(fail);
    return () => { cancelled = true; };
  }, [run, results, fail]);

  const deleteEverything = useCallback(async () => {
    if (!savedProfile) return;
    try {
      const caseKey = savedProfile.id;
      await api.deleteProfile(caseKey);
      setSavedProfile(null);
      setLocalCaseKey(null);
      setRun(null);
      setResults([]);
      setSummary(null);
      writePointer('run', null);
      writePointer('profile', null);
      clearDraftSlot(caseKey);
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
      loadDemoProfile, clearProfile, validation, validationStatus, retryValidation, run, results,
      summary, loading, error, saveProfile, startRun, cancelRun, retryRun, recheckNow, collectDocuments,
      exportShortlist, decide, saveNotes, refreshResults, rerank, shortlist, deleteEverything,
      clearError: () => setError(null),
      paywall, clearPaywall: () => setPaywall(null), unlockFromSubscription,
    }),
    [capabilities, profileDraft, setProfileDraft, savedProfile, cases, switchCase, newCase,
     restored, dirty, draftRestored, discardDraft, hydrated, loadDemoProfile,
     clearProfile, validation, validationStatus, retryValidation, run, results, summary, loading, error, saveProfile, startRun,
     cancelRun, retryRun, recheckNow, collectDocuments, exportShortlist, decide, saveNotes,
     refreshResults, rerank, shortlist, deleteEverything, paywall, unlockFromSubscription],
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): Store {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore must be used inside <StoreProvider>');
  return ctx;
}
