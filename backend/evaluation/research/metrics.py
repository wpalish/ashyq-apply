"""Conservative exact scoring; unavailable adjudication stays unmeasured."""

import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.adapters.search.ontology import titles_name_same_programme
from app.domain.claim_verifier import registrable_domain
from app.domain.programme_identity import Verdict

from .schema import Capture, Case, Dataset, Label, Observation, Prediction, Scope


def canonical_url(url: object) -> str:
    parts = urlsplit(str(url))
    # Preserve query parameters: they can identify a programme or language.
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, "")
    )


#: The longest quote of ours that may contain the reviewer's words and still
#: count as quoting them. Owner decision 2026-09-23: reviewers quote the least
#: that proves a fact ("6.5"), the pipeline a sentence around it, so requiring
#: ours to lie *inside* theirs made every correct claim unsupported. The cap
#: keeps "the reviewer's words are somewhere in half a page" from counting.
SUPPORTING_QUOTE_MAX = 300


def _domain(url: object) -> str:
    return registrable_domain(urlsplit(str(url)).hostname or "")


def quote_supports(ours: str, theirs: str) -> bool:
    """Whether our quote and the reviewer's are the same evidence.

    Either ours lies inside theirs (the original rule), or theirs lies inside
    ours and ours is short enough to still be a quotation. Whitespace is
    compared collapsed on both sides: a table's cells joined differently are
    the same words.
    """
    ours_flat, theirs_flat = " ".join(ours.split()), " ".join(theirs.split())
    if not ours_flat or not theirs_flat:
        return False
    if ours_flat in theirs_flat:
        return True
    return len(ours_flat) <= SUPPORTING_QUOTE_MAX and theirs_flat in ours_flat


#: The populations a page reading can record (app.adapters.scope_reader), as
#: plain data: evaluation reads no production module at scoring time.
CONTROLLED_POPULATIONS = frozenset(
    {"eu/eea", "domestic", "first-year", "international", "non-eu/eea", "transfer"}
)


def _plain(text: object) -> str:
    """Case-blind, and a leading "The" is not part of a name ("The University
    of Hong Kong" is the University of Hong Kong; run 77)."""
    folded = str(text).casefold().strip()
    return folded[4:] if folded.startswith("the ") else folded


def _name_parts(text: object) -> set[str]:
    """The whole name and each part a comma, bracket, " - " or " | " separates."""
    whole = _plain(text)
    parts = {whole}
    for piece in re.split(r",|\(|\)| - | – | \| ", whole):
        piece = _plain(piece)
        if piece:
            parts.add(piece)
    return parts


def dimension_matches(key: str, value: object, recorded: object) -> bool:
    """One scope dimension: whether ``recorded`` answers the label's ``value``.

    Shared with ``scope_report`` so the report never explains a miss the score
    does not count (run 77 found the two had drifted apart).
    """
    if key == "programme":
        return bool(recorded) and (
            titles_name_same_programme(str(value), str(recorded)) is Verdict.YES
        )
    if key == "population" and str(value).casefold() not in CONTROLLED_POPULATIONS:
        # A descriptive corpus population ("Vancouver applicants using IELTS
        # Academic") is a note on who the source addresses, not a value any
        # page reading can emit. Owner delegated silence on 2026-09-26; on
        # 2026-10-05 (D2) another description is compatible too: NTU's bond
        # read "Singapore PRs and international students" against "full-time
        # undergraduate scholarship applicants", both true of the page. A
        # recorded controlled population ("transfer") is a stated group the
        # note cannot be compared with, so it still does not match.
        return recorded is None or str(recorded).casefold() not in CONTROLLED_POPULATIONS
    if key == "university":
        # A page names its institution with its acronym or campus beside it
        # ("KIT, Karlsruhe Institute of Technology"; dev4 run 39134956132):
        # the same name as one comma/bracket/dash-separated part is the same
        # institution. A longer different name is not ("Oslo Metropolitan
        # University" never matches "University of Oslo").
        return recorded is not None and bool(_name_parts(value) & _name_parts(recorded))
    if key == "academic_year":
        # Spelling is not meaning (D3, owner 2026-10-05): the corpus quotes
        # "2027-2028" as the page writes it, the pipeline writes "2027/28".
        return recorded is not None and _academic_year(recorded) == _academic_year(value)
    # Case is not meaning: the pipeline writes "Fall 2027", the corpus
    # "fall 2027" (definition fixed 2026-09-23, recorded in VERSIONS.md).
    return recorded is not None and _plain(recorded) == _plain(value)


_YEAR_SPAN = re.compile(r"(\d{4})\s*[-/–]\s*(\d{2,4})")


def _academic_year(text: object) -> str:
    """One spelling for an academic year: "2027-2028", "2027/2028", "2027/28" -> "2027/28"."""
    found = _YEAR_SPAN.search(str(text))
    return f"{found[1]}/{found[2][-2:]}" if found else _plain(text)


def names_another_subject(expected: Scope, actual: Scope) -> bool:
    """Whether a claim's own scope says it is about somebody else (D1).

    Owner decision 2026-10-05: a claim whose page reading names another
    controlled population ("EU/EEA" against a "non-EU/EEA" label) or another
    programme is not an answer to the label's question, so it is neither right
    nor wrong; the product shows it under its own scope. Silence is not this:
    a claim that names no population is still judged, and still wrong-scope.
    """
    if expected.population and actual.population:
        label, ours = expected.population.casefold(), actual.population.casefold()
        if label in CONTROLLED_POPULATIONS and ours in CONTROLLED_POPULATIONS and label != ours:
            return True
    return bool(
        expected.programme
        and actual.programme
        and titles_name_same_programme(expected.programme, actual.programme) is not Verdict.YES
    )


#: Keys whose corpus value can be a finer reading of the pipeline's value (D4,
#: owner 2026-10-05). The pipeline's ``separate`` is true of NTU's "separate,
#: after the admission application", only less exact; a coarser right value is
#: partial, never a hit and never a wrong claim. Deliberately a short list:
#: each entry is a stated vocabulary difference, not a fuzzy match.
def _coarser(key: str, ours: object, label: object) -> bool:
    if key.endswith(".applicability.application_mode"):
        return isinstance(ours, str) and isinstance(label, str) and label.startswith(ours + "_")
    if key.endswith(".applicability.degree"):
        return (
            isinstance(ours, dict)
            and ours.get("applies") == "yes"
            and isinstance(label, str)
            and label.split("_", 1)[0] == ours.get("degree")
        )
    return False


def scope_matches(expected: Scope, actual: Scope) -> bool:
    """Whether a recorded scope answers the scope a label asked about.

    Every dimension compares literally except ``programme``, which compares
    **identity**: a page publishes "Bachelor of Computing (Hons) in Computer
    Science" where a label reads "Computer Science", and counting that as a
    wrong-scope claim measured our naming rather than our research. The
    owner settled this on 2026-09-22.

    Only ``YES`` is a match. ``UNKNOWN`` — two titles the ontology cannot
    reconcile — stays a miss, because a benchmark that scores "we could not
    tell" as a hit is measuring nothing.
    """
    for key, value in expected.model_dump().items():
        if value is not None and not dimension_matches(key, value, getattr(actual, key)):
            return False
    return True


@dataclass(frozen=True)
class PredictionVerdict:
    """How the scorer judged one prediction against the label for its key.

    ``score`` counts these; the scorecard lists them. Both read this one
    function, so a per-label explanation can never disagree with a metric.
    """

    #: A label with status ``known`` exists for the key.
    labelled: bool
    value_matches: bool
    provenance: bool
    exact_evidence: bool
    supported: bool
    supported_same_page: bool
    support_known: bool
    #: Only judged for a labelled prediction; False otherwise.
    valid_scope: bool
    #: D1: the claim's own scope names another population or programme.
    other_scope: bool = False
    #: D4: a coarser reading of the label's value, in scope.
    partial: bool = False

    @property
    def adjudicated(self) -> bool:
        """Counted in precision: labelled, about the label's subject, not partial."""
        return self.labelled and not self.other_scope and not self.partial

    @property
    def correct(self) -> bool:
        return self.adjudicated and self.value_matches and self.valid_scope and self.supported


#: ID-1 / D2 (core-gap analysis 2026-10-18 change 3): a key the corpus files a
#: fact under for some cases only. NTU's SAT is an English-proficiency
#: alternative, and its signed label is ``english_evidence.sat.minimum`` (its
#: ``sat.minimum`` is ``unknown``); every other case uses ``sat.minimum``. A
#: prediction is scored under the alias only when the case knows the alias
#: and does not know the key itself.
GOLD_KEY_ALIASES: dict[str, str] = {"sat.minimum": "english_evidence.sat.minimum"}


def scored_key(key: str, labels: dict[str, Label]) -> str:
    """The key a prediction is scored under for this case's labels."""
    alias = GOLD_KEY_ALIASES.get(key)
    if alias is None:
        return key
    own, other = labels.get(key), labels.get(alias)
    if other is not None and other.status == "known" and (own is None or own.status != "known"):
        return alias
    return key


def scored_predictions(predictions: list[Prediction], labels: dict[str, Label]) -> list[Prediction]:
    """``predictions`` with each key replaced by :func:`scored_key`."""
    return [
        p if (key := scored_key(p.key, labels)) == p.key else p.model_copy(update={"key": key})
        for p in predictions
    ]


def adjudicate(p: Prediction, label: Label | None) -> PredictionVerdict:
    """Judge one prediction against the label for its key, or against none."""
    value_matches = label is not None and json.dumps(p.value, sort_keys=True) == json.dumps(
        label.value, sort_keys=True
    )
    evidence = p.evidence
    provenance = bool(evidence and evidence.source_type in {"official", "government"})
    exact_evidence = bool(
        label
        and evidence
        and not evidence.excerpt_truncated
        and any(
            canonical_url(e.url) == canonical_url(evidence.url)
            and quote_supports(evidence.excerpt, e.excerpt)
            for e in label.evidence
        )
    )
    # Owner decision 2026-09-23: another official page of the same
    # university may support a label. The reviewer cites one page;
    # universities publish the same deadline or fee on several, and a
    # right value quoted from the fees page instead of the programme
    # page was scored as unsupported. The strict reading stays beside
    # it as ``claim_recall_same_page``.
    sibling_evidence = bool(
        label
        and evidence
        and not evidence.excerpt_truncated
        and evidence.excerpt.strip()
        and _domain(evidence.url) in {_domain(e.url) for e in label.evidence}
    )
    supported_same_page = provenance and (
        p.supported is True
        or (p.supported is None and exact_evidence and label is not None and value_matches)
    )
    supported = supported_same_page or (
        provenance
        and p.supported is None
        and sibling_evidence
        and label is not None
        and value_matches
    )
    support_known = not provenance or p.supported is not None or exact_evidence
    labelled = bool(label and label.status == "known")
    valid_scope = bool(
        labelled
        and label
        and evidence
        and any(scope_matches(e.scope, evidence.scope) for e in label.evidence)
    )
    other_scope = bool(
        labelled
        and label
        and evidence
        and label.evidence
        and all(names_another_subject(e.scope, evidence.scope) for e in label.evidence)
    )
    partial = bool(
        labelled
        and label
        and not other_scope
        and valid_scope
        and not value_matches
        and _coarser(p.key, p.value, label.value)
    )
    return PredictionVerdict(
        labelled=labelled,
        value_matches=value_matches,
        provenance=provenance,
        exact_evidence=exact_evidence,
        supported=supported,
        supported_same_page=supported_same_page,
        support_known=support_known,
        valid_scope=valid_scope,
        other_scope=other_scope,
        partial=partial,
    )


#: A path segment that is an intake year ("/2027/computing-beng").
_INTAKE_YEAR = re.compile(r"20\d{2}")
#: A trailing ``.htm`` / ``.html`` on a URL's last segment (not ``index.html``,
#: which names the directory and is removed whole).
_HTML_EXTENSION = re.compile(r"(?<=[^/])\.html?$", re.IGNORECASE)


def _page_forms(url: object, language: str | None) -> tuple[set[str], set[str]]:
    """One URL's canonical forms, as written and with its intake year removed.

    Ticket 03 Q2 (owner, 2026-10-18): a trailing ``index.html``, a trailing
    ``.htm`` / ``.html`` extension (loss stages v3 §7) and a trailing slash are
    not part of the page; a ``lang`` query parameter is not either, but only
    when ``language`` (the page's own ``<html lang>``, as read) confirms it.
    Any other query parameter stays: it can identify a programme
    (``?p7_code=``).
    """
    parts = urlsplit(canonical_url(url))
    path = parts.path
    if path.endswith("/index.html"):
        path = path[: -len("/index.html")]
    # v3 loss stages 2026-10-18 §7: a trailing ``.htm`` / ``.html`` is not part
    # of the page either (KU Leuven's gold ``…/SC_51016742.htm`` is the page
    # search returned as ``…/SC_51016742``).
    path = _HTML_EXTENSION.sub("", path)
    queries = {parts.query}
    if language and parts.query:
        primary = language.casefold().split("-")[0]
        kept = [
            piece
            for piece in parts.query.split("&")
            if not (
                piece.partition("=")[0] == "lang"
                and piece.partition("=")[2].casefold().split("-")[0] == primary
            )
        ]
        queries.add("&".join(kept))
    segments = path.split("/")
    yearless = "/".join(s for s in segments if not _INTAKE_YEAR.fullmatch(s))

    def form(path_: str, query: str) -> str:
        return urlunsplit((parts.scheme, parts.netloc, path_.rstrip("/"), query, ""))

    written = {form(path, q) for q in queries}
    without_year = {form(yearless, q) for q in queries} if yearless != path else set()
    return written, without_year


def same_programme_page(returned: object, gold: object, language: str | None = None) -> bool:
    """Whether a returned URL and a gold URL are canonical variants of one page.

    Ticket 03 Q2: the same path with or without an intake-year segment, a
    trailing slash, ``index.html`` or a ``.htm`` / ``.html`` extension;
    ``?lang=`` only when the returned page's ``<html lang>`` (``language``)
    names that language. "With or without" is one side holding the year: two
    different years are two intakes' pages.
    """
    ours, ours_yearless = _page_forms(returned, language)
    theirs, theirs_yearless = _page_forms(gold, language)
    return bool(ours & theirs or ours & theirs_yearless or ours_yearless & theirs)


def _language_of(observation: Observation, url: str) -> str | None:
    for recorded, language in observation.programme_page_languages.items():
        if canonical_url(recorded) == url:
            return language
    return None


def returned_matching_gold(observation: Observation, expected: set[str]) -> set[str]:
    """The returned programme pages (canonical) that are a gold page or its twin.

    WF-17 (ticket 03 Q1, recommended answer): a page the returned page
    declares as its own ``hreflang`` alternate *is* the same programme page,
    so a returned page counts when it or any recorded twin is in the gold.
    v3-M2 (ticket 03 Q2): "in the gold" is up to a canonical variant
    (``same_programme_page``). A capture that records no twins, and returns no
    variant of a gold URL, scores exactly as before.
    """
    twins: dict[str, set[str]] = defaultdict(set)
    for url, aliases in observation.programme_url_aliases.items():
        twins[canonical_url(url)].update(canonical_url(a) for a in aliases)
    matched = set()
    for url in map(canonical_url, observation.programme_urls):
        # The recorded language is the returned page's own; a twin is read
        # as written (it is, by declaration, another language's page).
        language = _language_of(observation, url)
        forms = [(url, language), *((twin, None) for twin in twins.get(url, set()))]
        if any(same_programme_page(form, gold, lang) for form, lang in forms for gold in expected):
            matched.add(url)
    return matched


#: How one case's programme-page outcome reads, best first (ticket 03 Q3).
PROGRAMME_OUTCOMES = ("hit", "wrong", "related", "missed", "unadjudicated")


@dataclass(frozen=True)
class ProgrammePageVerdict:
    """How the scorer judged one case's returned programme pages (v3-M2).

    ``matched`` are a gold page, its twin or a canonical variant; ``related``
    are a related programme (ticket 03 Q3: a sibling specialisation, a major
    page, the field's bachelor in another faculty), neither a hit nor wrong;
    ``wrong`` are every other returned page, the wrong-page count. A related
    programme is either labelled in the corpus (``Case.related_programme_urls``)
    or one discovery read and recorded as related instead of returning it
    (``Observation.related_programme_urls``, ticket 16 Q6).
    """

    outcome: str
    matched: frozenset[str]
    related: frozenset[str]
    wrong: frozenset[str]


def adjudicate_programme_pages(case: Case, observation: Observation) -> ProgrammePageVerdict:
    """Judge one case's programme pages: hit, wrong, related, missed or unadjudicated.

    ``hit`` when any returned page matches the gold; else ``wrong`` when a
    returned page is neither gold nor related; else ``related`` when a related
    programme was returned or recorded; else ``missed``. A case whose
    programme is ``unknown`` to the corpus is ``unadjudicated``.
    """
    expected = {canonical_url(url) for url in case.programme_urls}
    returned = set(map(canonical_url, observation.programme_urls))
    matched = returned_matching_gold(observation, expected)
    labelled_related = {canonical_url(url) for url in case.related_programme_urls}
    related = {
        url
        for url in returned - matched
        if any(
            same_programme_page(url, other, _language_of(observation, url))
            for other in labelled_related
        )
    }
    wrong = returned - matched - related
    recorded_related = {canonical_url(url) for url in observation.related_programme_urls}
    if case.programme_status == "unknown":
        outcome = "unadjudicated"
    elif matched:
        outcome = "hit"
    elif wrong:
        outcome = "wrong"
    elif related or recorded_related:
        outcome = "related"
    else:
        outcome = "missed"
    return ProgrammePageVerdict(
        outcome=outcome,
        matched=frozenset(matched),
        related=frozenset(related | (recorded_related - matched)),
        wrong=frozenset(wrong),
    )


def ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def score(dataset: Dataset, capture: Capture, *, allow_drafts: bool = False) -> dict[str, Any]:
    if not allow_drafts and any(c.review.status != "human_verified" for c in dataset.cases):
        raise ValueError(
            "Dataset contains cases without human verification; use --allow-drafts for provisional results"
        )
    ids = {case.id for case in dataset.cases}
    observed = {o.case_id: o for o in capture.observations}
    if len(observed) != len(capture.observations) or set(observed) - ids:
        raise ValueError("Duplicate or foreign observation case IDs")
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    fields: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    per_case = []

    def add(name: str, n: int, d: int) -> None:
        counts[name][0] += n
        counts[name][1] += d

    for case in dataset.cases:
        observation = observed.get(
            case.id, Observation(case_id=case.id, error="MISSING_OBSERVATION")
        )
        expected = {canonical_url(url) for url in case.programme_urls}
        pages = adjudicate_programme_pages(case, observation)
        hit = bool(pages.matched)
        if case.programme_status == "known":
            add("programme_page_recall", int(hit), 1)
        if case.programme_status != "unknown":
            # v3-M2: a related programme is neither a hit nor a wrong page,
            # so it leaves the precision denominator.
            add("programme_page_precision", len(pages.matched), len(pages.matched | pages.wrong))
        for k in (5, 10, 20):
            if case.programme_status == "known" and observation.ranked_urls is not None:
                ranked = list(dict.fromkeys(map(canonical_url, observation.ranked_urls)))
                add(
                    f"recall_at_{k}",
                    int(
                        any(
                            same_programme_page(url, gold)
                            for url in ranked[:k]
                            for gold in expected
                        )
                    ),
                    1,
                )
        labels = {label.key: label for label in case.labels}
        predictions = {}
        # Exact repeats cannot increase credit or denominator; conflicting values remain distinct.
        for prediction in scored_predictions(observation.predictions, labels):
            if prediction.value is not None and prediction.value != "UNKNOWN":
                predictions[prediction.model_dump_json()] = prediction
        correct_keys: set[str] = set()
        correct_same_page_keys: set[str] = set()
        answered = {p.key for p in predictions.values()}
        correct_predictions = 0
        adjudicated = 0
        for p in predictions.values():
            label = labels.get(p.key)
            verdict = adjudicate(p, label)
            supported = verdict.supported
            support_known = verdict.support_known
            if support_known:
                add("unsupported_claim_rate", int(not supported), 1)
            add("support_adjudication_rate", int(support_known), 1)
            add("primary_source_rate", int(verdict.provenance), 1)
            add(
                "verbatim_evidence_rate", int(verdict.exact_evidence), 1
            ) if verdict.labelled else None
            if p.current is not None:
                add("current_evidence_rate", int(p.current), 1)
            if p.conflict_visible is not None:
                add("conflict_visibility_rate", int(p.conflict_visible), 1)
            if verdict.labelled:
                add("other_scope_claim_rate", int(verdict.other_scope), 1)
                add("partial_claim_rate", int(verdict.partial), 1)
            if verdict.adjudicated:
                add("wrong_scope_claim_rate", int(not verdict.valid_scope), 1)
                correct = verdict.correct
                if verdict.value_matches and verdict.valid_scope and verdict.supported_same_page:
                    correct_same_page_keys.add(p.key)
                correct_predictions += int(correct)
                adjudicated += 1
                if correct:
                    correct_keys.add(p.key)
                fields[p.key]["precision"][0] += int(correct)
                fields[p.key]["precision"][1] += 1
                if p.key.startswith("scholarships."):
                    if ".applicability." in p.key:
                        add("scholarship_applicability_precision", int(correct), 1)
                    if ".coverage." in p.key:
                        add("scholarship_coverage_precision", int(correct), 1)
        known = {label.key for label in case.labels if label.status == "known"}
        critical = {
            label.key
            for label in case.labels
            if label.critical and label.status != "not_applicable"
        }
        add("claim_precision", correct_predictions, adjudicated)
        add("claim_adjudication_rate", adjudicated, len(predictions))
        add("claim_recall", len(correct_keys), len(known))
        add("claim_recall_same_page", len(correct_same_page_keys), len(known))
        add("critical_field_coverage", len(critical & answered), len(critical))
        for label in case.labels:
            if label.status == "not_applicable":
                continue
            fields[label.key]["coverage"][0] += int(label.key in answered)
            fields[label.key]["coverage"][1] += 1
            if label.status == "known":
                fields[label.key]["recall"][0] += int(label.key in correct_keys)
                fields[label.key]["recall"][1] += 1
                if label.key.startswith("scholarships."):
                    if ".applicability." in label.key:
                        add("scholarship_applicability_recall", int(label.key in correct_keys), 1)
                    if label.key.endswith(".exists") and label.value is True:
                        add("scholarship_discovery_recall", int(label.key in correct_keys), 1)
        per_case.append(
            {
                "case_id": case.id,
                "country": case.country,
                "site_types": case.site_types,
                "programme_hit": hit,
                "correct_claims": len(correct_keys),
                "answerable_claims": len(known),
                "error": observation.error,
            }
        )
    names: tuple[str, ...] = (
        "programme_page_recall",
        "programme_page_precision",
        "recall_at_5",
        "recall_at_10",
        "recall_at_20",
        "claim_precision",
        "claim_recall",
        "claim_recall_same_page",
        "unsupported_claim_rate",
        "wrong_scope_claim_rate",
        "other_scope_claim_rate",
        "partial_claim_rate",
        "critical_field_coverage",
        "scholarship_discovery_recall",
        "scholarship_applicability_precision",
        "scholarship_applicability_recall",
        "scholarship_coverage_precision",
        "primary_source_rate",
        "verbatim_evidence_rate",
        "current_evidence_rate",
        "conflict_visibility_rate",
        "support_adjudication_rate",
        "claim_adjudication_rate",
    )
    operations = {}
    for name in (
        "http_fetches",
        "browser_fetches",
        "pdf_fetches",
        "search_calls",
        "model_input_tokens",
        "jev_input_tokens",
        "latency_seconds",
        "cost_usd",
        "human_review_required",
    ):
        values = [
            getattr(o.telemetry, name)
            for o in capture.observations
            if getattr(o.telemetry, name) is not None
        ]
        operations[name] = {
            "sum": sum(values) if values else None,
            "measured_cases": len(values),
            "cases": len(ids),
        }
    times = sorted(
        o.telemetry.latency_seconds
        for o in capture.observations
        if o.telemetry.latency_seconds is not None
    )
    operations["latency_percentiles"] = {
        f"p{p}": times[max(0, math.ceil(len(times) * p / 100) - 1)] if times else None
        for p in (50, 95)
    }
    review_values = [
        o.telemetry.human_review_required
        for o in capture.observations
        if o.telemetry.human_review_required is not None
    ]
    counts["human_review_rate"] = [sum(review_values), len(review_values)]
    names = (*names, "human_review_rate")
    digest = hashlib.sha256(dataset.model_dump_json().encode()).hexdigest()
    return {
        "dataset_version": dataset.version,
        "dataset_sha256": digest,
        "pipeline_sha": capture.pipeline_sha,
        "provisional": any(c.review.status != "human_verified" for c in dataset.cases),
        "mode": capture.mode,
        "captured_at": capture.captured_at,
        "config": capture.config,
        "metrics": {name: ratio(*counts[name]) for name in names},
        "fields": {
            key: {name: ratio(*v) for name, v in values.items()}
            for key, values in sorted(fields.items())
        },
        "operations": operations,
        "cases": per_case,
        "notes": [
            "Exact value and evidence-scope matching; unlabelled predictions are unadjudicated, not correct.",
            "Missing rank lists/telemetry yield null; per-case failures stay in recall denominators.",
            "No overall accuracy score. Programme URLs measure identity, not intake confirmation.",
        ],
    }


def dump_report(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
