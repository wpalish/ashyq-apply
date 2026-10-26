"""Knowledge-base facts as pipeline claims, and discovery from the catalogue without the web.

The claims use the product's own ``Claim`` model exactly as a live read would:
an official source, the verified quote as the excerpt, the confidence and
status the claim builder gives an official, quoted page
(``app.adapters.extraction.ClaimBuilder.add``: 0.8, ``VERIFIED_CURRENT``). A
stale fact (``app.knowledge.stale_reasons``) is ``POSSIBLY_STALE`` and says why.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.search.ontology import canonical_field
from app.catalogue.retrieval import retrieve
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimStatus, ClaimType, CostCategory, DegreeLevel, SourceSpecificity
from app.knowledge import (
    CAVEAT_MARK,
    KnowledgeBase,
    KnowledgeEntry,
    carried_stale_reasons,
    fact_caveat,
    review_label,
    stale_reasons,
)
from app.models import University
from app.schemas.claim import Claim, UnresolvedQuestion
from app.schemas.money import Money
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import CostBreakdown

#: ``app.adapters.extraction.ClaimBuilder.add``'s default for an official,
#: quoted page; the KB quote was found on that page by the CI evidence check.
OFFICIAL_QUOTED_CONFIDENCE = 0.8

#: The ontology concept the KB answers for (it covers Computer Science only).
KB_FIELD = "computer_science"
#: Words that name the CS subject in a programme heading (``programme_name``).
_CS_WORDS = ("computer", "computing", "informatic", "informatik", "software")

KB_DISCOVERY_SOURCE = "knowledge-base"
#: Tuition periods the cost table (a yearly figure) can take as they are. A
#: per-semester or whole-programme figure stays a claim, published as it is.
_ANNUAL = frozenset({"year", "annual", "per year", "academic year", "yearly"})
#: Periods that are a unit of study, not a stretch of time: the page printed a
#: rate (UBC: per credit) and no yearly figure, and the load is not ours to
#: guess, so the rate is never multiplied out. ``app.knowledge.funding`` says so.
PER_UNIT_PERIODS = frozenset({"credit", "credit hour", "unit", "point", "credit point", "course"})
NO_VERIFIED_DATA = "no verified data yet"
#: The KB value of a "does not apply" fact ("no scholarship for bachelor's").
NOT_APPLICABLE = "not_applicable"


def covers(profile: ApplicantProfileIn) -> bool:
    """Whether the applicant asks the one question the KB answers: a CS bachelor.

    An intended field counts only when the ontology resolves it to Computer
    Science (the field or a strong / localized alias), so the KB's facts are
    never shown as another programme's.
    """
    context = profile.context
    if context.level is not DegreeLevel.BACHELOR:
        return False
    fields = context.intended_fields or ["computer science"]
    # Computer Science or one of its ontology aliases ("Computing", "Informatics",
    # "Informatik"), never a field that merely contains a CS word: Software
    # Engineering, Computer Engineering and Business Informatics are other
    # programmes, and the KB holds the CS bachelor's facts only.
    return any(canonical_field(f) == KB_FIELD for f in fields)


def seed_id_of(uni: University) -> str | None:
    record = (uni.seed_snapshot or {}).get("record") or {}
    return str(record.get("seed_id") or "") or None


def entry_for(kb: KnowledgeBase, uni: University) -> KnowledgeEntry | None:
    return kb.get(seed_id_of(uni)) or kb.by_domain(uni.domain)


#: The row's programme name when the KB holds no short title for it.
FALLBACK_PROGRAMME = "Bachelor's in Computer Science"
#: Words that name the subject; a candidate name without one is not the CS programme.
_SUBJECT_WORDS = (*_CS_WORDS, "datateknik", "datavetenskap", "datalogi")
#: Words that open a degree title inside a longer heading.
_DEGREE_WORDS = frozenset({"bachelor", "bachelor's", "bsc", "b.sc.", "b.s.", "beng", "bs", "ba"})
#: Words at which a heading stops being the programme's name.
_NAME_STOPS = frozenset(
    {
        "additional",
        "course",
        "degree",
        "department",
        "home",
        "major",
        "minor",
        "our",
        "plan",
        "this",
        "ucas",
        "undergraduate",
        "we",
        "you",
    }
)
_CONNECTORS = frozenset({"and", "of", "in", "&", "-", "–", "—"})
#: After the subject, only these carry a title on ("... Science and Engineering, BSc").
_CONTINUATIONS = frozenset(
    {
        *_CONNECTORS,
        *_DEGREE_WORDS,
        "ai",
        "b.a.",
        "engineering",
        "honours",
        "meng",
        "science",
        "sciences",
        "studies",
        "systems",
        "technology",
    }
)
#: A heading that opens like a sentence is not a name ("The ...", "In the ...").
_SENTENCE_OPENERS = frozenset({"a", "for", "in", "on", "the"})
#: A heading that names a unit, not a programme ("School of Computer Science").
_UNIT_WORDS = frozenset({"college", "department", "dept.", "faculty", "school"})
_NAME_MAX_WORDS = 8


def _names_subject(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in _SUBJECT_WORDS)


def _trim_name(words: list[str]) -> str:
    """The words up to the first one that leaves the title, tidied."""
    kept: list[str] = []
    for i, word in enumerate(words):
        bare = word.lower().strip(",")
        following = words[i + 1].lower() if i + 1 < len(words) else ""
        second_title = (
            bare in _DEGREE_WORDS
            and (bare.startswith("bachelor") or following in {"of", "in"})
            and _names_subject(" ".join(kept))
        )
        if i and (bare in _NAME_STOPS or second_title):
            break
        if _names_subject(" ".join(kept)) and not (bare in _CONTINUATIONS or _names_subject(bare)):
            break
        kept.append(word)
    while kept and kept[-1].lower().strip(",") in _CONNECTORS:
        kept.pop()
    name = " ".join(kept).strip(" ,:-–|")
    # "Computer Science Computer Science": a heading over its own title.
    return re.sub(r"\b(.+?)(?: \1\b)+", r"\1", name)


def _without_parentheses(text: str) -> str:
    """The text with every bracketed aside removed, nested ones included."""
    previous = None
    while previous != text:
        previous, text = text, re.sub(r"\([^()]*\)", " ", text)
    return text.replace("(", " ").replace(")", " ")


def _title_run(words: list[str]) -> list[str]:
    """Leading words of a title: capitalised words and the connectors between them."""
    run: list[str] = []
    for word in words:
        if not (word[:1].isupper() or word.lower() in _CONNECTORS):
            break
        run.append(word)
    return run


def programme_name(programme: dict[str, Any]) -> str:
    """A short programme name for the row, never a whole evidence quote.

    The KB's own ``title`` when it has one. Otherwise the shortest evidence
    quote that reads as a heading rather than a sentence (parentheses dropped,
    cut where the title ends); then a degree title inside a longer quote
    ("... Bachelor of Science in Computer Science and Engineering"); else
    ``FALLBACK_PROGRAMME``. The quotes themselves stay the evidence.
    """
    if programme.get("title"):
        return str(programme["title"])[:200]
    quotes = [
        _without_parentheses(str(e["quote"]))
        for e in programme.get("evidence") or []
        if e.get("quote")
    ]
    headings: list[str] = []
    for quote in quotes:
        name = _trim_name(quote.split(":")[0].split())
        words = [w.lower() for w in name.split()]
        if (
            words
            and words[0] not in _SENTENCE_OPENERS
            and not _UNIT_WORDS.intersection(words)
            and not name.endswith(".")
            and len(words) <= _NAME_MAX_WORDS
            and _names_subject(name)
        ):
            headings.append(name)
    if headings:
        # A name that says the degree ("BSc Informatik") over a bare subject.
        return min(
            headings,
            key=lambda n: (not _DEGREE_WORDS.intersection(n.lower().split()), len(n)),
        )
    for quote in quotes:
        words = quote.split()
        for i, word in enumerate(words):
            if word.lower().strip(",") not in _DEGREE_WORDS:
                continue
            name = _trim_name([word, *_title_run(words[i + 1 :])])
            if _names_subject(name) and len(name.split()) <= _NAME_MAX_WORDS:
                return name
    return FALLBACK_PROGRAMME


@dataclass
class KnowledgeDiscovery:
    """Catalogue retrieval with KB programme pages; no search, no fetch, no network."""

    session: Session
    kb: KnowledgeBase
    university_ids: list[str] | None
    name: str = "verified-knowledge-base"

    async def discover(self, profile: ApplicantProfileIn, limit: int = 50) -> list[Candidate]:
        rows = retrieve(
            self.session,
            preferred=profile.preferences.preferred_countries,
            excluded=profile.preferences.excluded_countries,
            university_ids=self.university_ids,
        )[:limit]
        in_scope = covers(profile)
        candidates: list[Candidate] = []
        for uni in rows:
            entry = entry_for(self.kb, uni) if in_scope else None
            if entry is None or not entry.has_verified_data:
                candidates.append(
                    Candidate(
                        name=uni.name,
                        country=uni.country,
                        city=uni.city,
                        domain=uni.domain or "",
                        discovery_source=f"local-catalogue:{uni.id}",
                        notes=NO_VERIFIED_DATA,
                    )
                )
                continue
            programme = entry.programme
            urls = [str(u) for u in programme.get("urls") or []]
            title = programme_name(programme)
            programs = (
                [
                    CandidateProgram(
                        name=title[:200],
                        field="computer science",
                        degree=DegreeLevel.BACHELOR,
                        url=urls[0] if urls else None,
                    )
                ]
                if entry.programme_known
                else []
            )
            candidates.append(
                Candidate(
                    name=uni.name,
                    country=uni.country,
                    city=uni.city,
                    domain=entry.official_domains[0] if entry.official_domains else "",
                    programs=programs,
                    discovery_source=f"{KB_DISCOVERY_SOURCE}:{entry.seed_id}",
                    notes=f"Verified knowledge base ({review_label(entry.review_status)}).",
                )
            )
        return candidates


#: Fact key -> claim type. Keys outside this table are kept in the KB and not
#: turned into claims (no product claim type carries them yet).
def claim_type_for(key: str) -> ClaimType | None:
    if key == "ielts.overall":
        return ClaimType.IELTS_MIN_OVERALL
    if key == "ielts.subscores":
        return ClaimType.IELTS_MIN_SUBSCORE
    if key == "english_evidence.toefl_ibt.minimum":
        return ClaimType.TOEFL_MIN_TOTAL
    if key == "english_evidence.duolingo.minimum":
        return ClaimType.DUOLINGO_MIN
    if key == "gpa":
        return ClaimType.MIN_GPA
    if key == "deadline":
        return ClaimType.ADMISSION_DEADLINE
    if key == "tuition":
        return ClaimType.TUITION
    if key.startswith("scholarships") and key.endswith(".exists"):
        return ClaimType.SCHOLARSHIP_EXISTS
    if key.startswith("scholarships") and key.endswith(".applicability.international"):
        return ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE
    return None


_SPECIFICITY = {
    ClaimType.TUITION: SourceSpecificity.PROGRAM,
    ClaimType.SCHOLARSHIP_EXISTS: SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR,
    ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE: SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR,
}


def _moment(value: Any, fallback: datetime) -> datetime:
    try:
        day = date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return fallback
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def award_slug(key: str) -> str | None:
    """``imperial_inspires`` of ``scholarships.imperial_inspires.exists``; None otherwise."""
    parts = key.split(".")
    return parts[1] if key.startswith("scholarships.") and len(parts) > 2 else None


def _award_subjects(entry: KnowledgeEntry) -> dict[str, str]:
    """One display name per award slug, so all of an award's facts share a subject.

    The build stamps the award's name on the facts it read it for; a fact of
    the same award without the stamp takes it too, and an award never named
    keeps its slug.
    """
    subjects: dict[str, str] = {}
    for _question, fact in entry.all_facts():
        slug = award_slug(str(fact.get("key") or ""))
        subject = (fact.get("award") or {}).get("subject")
        if slug and subject and slug not in subjects:
            subjects[slug] = str(subject)
    return subjects


def _subject(fact: dict[str, Any], subjects: dict[str, str] | None = None) -> str | None:
    award = fact.get("award") or {}
    slug = award_slug(str(fact.get("key") or ""))
    if slug and subjects and slug in subjects:
        return subjects[slug]
    if award.get("subject"):
        return str(award["subject"])
    return slug


def _is_scholarship(row: dict[str, Any]) -> bool:
    return str(row.get("question") or "").startswith("scholarship") or str(
        row.get("key") or ""
    ).startswith("scholarships")


def none_offered_rows(entry: KnowledgeEntry) -> list[dict[str, Any]]:
    """The verified statements that the university has no scholarship for this applicant.

    Either a ``not_applicable`` row of a scholarship question or a scholarship
    fact whose value is ``not_applicable``. They count only when the entry
    names no award at all: a named award contradicts "none", and the award is
    what the funding stage then assesses.
    """
    facts = [(q, f) for q, f in entry.all_facts() if q.startswith("scholarship")]
    if any(str(f.get("value")).lower() != NOT_APPLICABLE for _q, f in facts):
        return []
    rows = [
        {**n, "key": n.get("key") or n.get("question")}
        for n in entry.not_applicable
        if _is_scholarship(n)
    ]
    rows += [{**f, "reason": f.get("notes")} for _q, f in facts]
    return [r for r in rows if r.get("source_url") and r.get("quote")]


_EXPERT_NOTE = re.compile(r"\s*Expert \(\d{4}-\d{2}-\d{2}\):.*$", re.S)
_LANGUAGE_LEVEL = re.compile(r"\b\w+_level=([^;(]+)")
_STATEMENT_MAX = 240


def _statement(reason: str) -> str:
    """The verified "does not apply" reason as a sentence an applicant can read.

    The expert's working note and the build's ``german_level=...`` bookkeeping
    are dropped; a language level, when the build recorded one, is kept.
    """
    text = _EXPERT_NOTE.sub("", reason).strip()
    level = _LANGUAGE_LEVEL.search(text)
    if level:
        # "... is German (german_level=DSH 2 ...; german_required=True)": the
        # bracket is the build's bookkeeping, often cut off mid-way.
        opening = text.rfind("(", 0, level.start())
        text = text[: opening if opening >= 0 else level.start()]
    text = " ".join(_without_parentheses(text).split()).replace(" .", ".").replace(" ,", ",")
    text = text.rstrip(" .;:")
    if level and level.group(1).strip():
        text += f" ({level.group(1).strip()})"
    if len(text) > _STATEMENT_MAX:
        return text[:_STATEMENT_MAX].rsplit(" ", 1)[0].rstrip(" ,;:") + " …"
    return text + "." if text else ""


#: A non-English language, or a test of one, as a verified statement or its
#: quote names it: in English or in the page's own language (ETH "German C1",
#: LMU "Deutschkenntnisse", KU Leuven "Nederlandse taalvaardigheid", UBA "país
#: no hispanohablante", Nanjing "HSK5级"). The expert's working note is never
#: read: Kyoto's says "No Japanese Language Proficiency Required".
_OTHER_LANGUAGE = re.compile(
    r"(?<![A-Za-z])(?:German|Deutsch\w*|Dutch|Nederlands\w*|French|Fran[cç]ais\w*|Danish|Dansk\w*|"
    r"Japanese|Chinese|Mandarin|Spanish|Espa[nñ]ol\w*|Castellano|\w*hispanohablante|"
    r"Italian\w*|Italiano|Swedish|Svenska|Norwegian|Norsk|Finnish|Suomi|Korean|Portuguese|"
    r"Portugu[eê]s|Russian|Turkish|T[uü]rk[cç]e|Polish|Czech|Hebrew|Arabic|"
    r"HSK|TOPIK|JLPT|EJU|DSH|TestDaF|DELF|DALF|TCF|TEF|SIELE|CELU|NT2)(?![A-Za-z])"
    r"|日本語|中文|汉语|漢語|한국어",
    re.IGNORECASE,
)
_NEGATED_BEFORE = re.compile(r"\b(?:no|not|without)\s+$", re.IGNORECASE)
_NEGATED_AFTER = re.compile(r"^[^.;]{0,40}\b(?:required|needed|necessary|mandatory)\b", re.I)


def names_other_language(*texts: str) -> bool:
    """Whether a verified statement or quote names a non-English language proof.

    "No Japanese language proficiency required" names a language only to say
    it is not asked for, so a mention negated right before it, with "required"
    (or "needed") right after it, does not count.
    """
    for text in texts:
        for found in _OTHER_LANGUAGE.finditer(text):
            before, after = text[: found.start()], text[found.end() :]
            if _NEGATED_BEFORE.search(before) and _NEGATED_AFTER.search(after):
                continue
            return True
    return False


def requirement_statement_questions(
    entry: KnowledgeEntry, *, university: str, programme: str
) -> list[UnresolvedQuestion]:
    """Each verified "does not apply" requirement as an open question that quotes it.

    "No English test is required" (ETH: German C1 instead) or "the language
    requirement is German (DSH 2)" is verified, but no product claim type
    carries it, so on its own the row says "needs clarification" and nothing
    says why. Not blocking: the statement is verified; what is open is only
    whether the applicant meets what applies instead.

    A language row asks what is required "instead" only when the statement or
    its quote names another language (``names_other_language``). Where neither
    does (Stanford: "we do not require any English proficiency exams"), it asks
    whether any other language evidence is needed and says the KB names none.
    """
    questions: list[UnresolvedQuestion] = []
    seen: set[tuple[str, str, str]] = set()
    for row in entry.not_applicable:
        if _is_scholarship(row) or not row.get("source_url") or not row.get("quote"):
            continue
        statement = _statement(str(row.get("reason") or ""))
        url, quote = str(row["source_url"]), str(row["quote"])
        if not statement or (statement, url, quote) in seen:
            continue
        seen.add((statement, url, quote))
        kind = str(row.get("question") or row.get("key") or "")
        if kind == "english" or str(row.get("key") or "").startswith("ielts"):
            topic = "language requirement"
            if names_other_language(statement, quote):
                ask = (
                    f"Which language certificate does {university} require instead, and do "
                    "you hold it?"
                )
            else:
                # Stanford, Harvard, Kyoto: no English test, and nothing verified
                # names another language either. Asking what is required
                # "instead" would invent a requirement.
                ask = (
                    f"Does {university} ask for any other language evidence? The verified "
                    "knowledge base names none."
                )
        elif kind == "gpa":
            topic = "grade requirement"
            ask = (
                f"Which grades or scores does {university} use instead, and does your record "
                "meet them?"
            )
        else:
            topic = kind.replace("_", " ") or "requirement"
            ask = f"What does {university} require instead?"
        questions.append(
            UnresolvedQuestion(
                topic=topic,
                question=f"{statement} {ask}",
                why_it_matters=(
                    f'Verified on the official page {url}: "{quote}". The profile has no field '
                    "this can be compared against, so it is not counted as met or as failed."
                ),
                university=university,
                program=programme,
                suggested_contact="admissions office",
                blocking=False,
            )
        )
    return questions


def kb_today() -> date:
    """The UTC day KB staleness is judged on when the caller gives none (the runner).

    One seam, so a test pins the day instead of asserting on a KB fact that
    turns stale a year after its fixture date.
    """
    return datetime.now(UTC).date()


#: The claim note of a fee the page printed only as a range.
TUITION_RANGE_NOTE = "Published as a range, not a single figure."


def fee_range(value: Any) -> tuple[float, float, str] | None:
    """(low, high, currency) of a KB fee printed as a range (``{min, max, currency}``)."""
    if not isinstance(value, dict) or value.get("min") is None or value.get("max") is None:
        return None
    return float(value["min"]), float(value["max"]), str(value["currency"])


def tuition_value(value: Any) -> dict[str, Any] | None:
    """A KB fee as the tuition claim's value, the shape a live fee read gives.

    A single amount is ``{amount, currency}``. A printed range is the live
    range shape (``app.adapters.structured_costs``): ``amount`` is the upper
    bound, so whatever reads only ``amount`` never understates the fee, and
    ``range_low``/``range_high`` carry the range as printed. None when the
    fact holds neither.
    """
    bounds = fee_range(value)
    if bounds is not None:
        low, high, currency = bounds
        if not _fee_figures(low, high) or low >= high:
            return None
        return {"amount": high, "currency": currency, "range_low": low, "range_high": high}
    if not isinstance(value, dict) or value.get("amount") is None:
        return None
    amount = float(value["amount"])
    if not _fee_figures(amount):
        return None
    return {"amount": amount, "currency": str(value["currency"])}


def _fee_figures(*numbers: float) -> bool:
    """Whether every number is a fee figure: finite and not negative.

    A KB file is reviewed data, but ``NaN`` or ``Infinity`` in it would reach
    the catalogue and the run as a value the API's JSON encoder refuses, a 500
    on every page that lists the university (security review 2026-10-22, SR2-06).
    """
    return all(math.isfinite(n) and n >= 0 for n in numbers)


@dataclass
class KnowledgeAnswer:
    """What the KB says for one programme row: claims, cost table, stale flags."""

    claims: list[Claim]
    costs: CostBreakdown
    stale: dict[int, list[str]]


def fact_claim(
    entry: KnowledgeEntry,
    fact: dict[str, Any],
    claim_type: ClaimType,
    value: Any,
    *,
    programme: str,
    intake: str,
    today: date,
    specificity: SourceSpecificity,
    subject: str | None = None,
    note: str | None = None,
) -> tuple[Claim, list[str]]:
    """One KB fact as the claim an official, quoted page gives, and why it is stale.

    Official source, the verified quote as the excerpt, confidence 0.8;
    ``POSSIBLY_STALE`` with the reasons in its notes when the fact is stale
    (``app.knowledge.stale_reasons``, plus any the build recorded).
    """
    built = _moment(entry.verified_on, datetime.now(UTC))
    label = review_label(entry.review_status)
    # The build's own reasons (a past cycle it saw) stay, but for one
    # computed against another intake; today's are added.
    reasons = list(
        dict.fromkeys([*stale_reasons(fact, today, intake), *carried_stale_reasons(fact, intake)])
    )
    verified = fact.get("verified_on") or entry.verified_on
    notes = [
        f"Verified knowledge base ({label}); quote found on the official page"
        f"{f' on {verified}' if verified else ''}."
    ]
    if note:
        notes.append(note)
    period = fact.get("period")
    if claim_type is ClaimType.TUITION and period and str(period).lower() not in _ANNUAL:
        notes.append(f"Amount per {period}, as published; not a yearly figure.")
    if claim_type is ClaimType.TUITION and fee_range(fact.get("value")) is not None:
        notes.append(TUITION_RANGE_NOTE)
    caveat = fact_caveat(fact)
    if caveat:
        # Current, but never shown as fully verified: the page did not
        # print the year this fact is read for (``app.knowledge.fact_caveat``).
        notes.append(f"{CAVEAT_MARK}{caveat}.")
    if reasons:
        notes.append("Stale, not current: " + "; ".join(reasons) + ".")
    population = fact.get("population")
    year = fact.get("academic_year")
    scope = (
        ClaimScope(population=population or None, academic_year=year or None)
        if population or year
        else None
    )
    claim = Claim(
        claim_type=claim_type,
        normalized_value=value,
        original_text_excerpt=str(fact.get("quote") or ""),
        source_url=str(fact["source_url"]),
        official_domain=True,
        program=programme,
        subject_key=subject,
        intake=intake,
        academic_year=year or None,
        accessed_at=_moment(verified or fact.get("accessed_on"), built),
        scope=scope,
        source_specificity=specificity,
        confidence=OFFICIAL_QUOTED_CONFIDENCE,
        status=ClaimStatus.POSSIBLY_STALE if reasons else ClaimStatus.VERIFIED_CURRENT,
        extraction_method="structured",
        notes=" ".join(notes),
    )
    return claim, reasons


def answer(
    entry: KnowledgeEntry,
    *,
    programme: str,
    intake: str,
    academic_year: str,
    today: date | None = None,
) -> KnowledgeAnswer:
    """Every KB fact of one entry as a claim; tuition also as the cost table.

    Document facts are not claims here: the document stage turns them into the
    checklist after the applicant approves the row (``app.knowledge.documents``).
    """
    day = today or kb_today()
    claims: list[Claim] = []
    stale: dict[int, list[str]] = {}
    costs = CostBreakdown(academic_year=academic_year)

    def add(
        claim_type: ClaimType,
        value: Any,
        fact: dict[str, Any],
        *,
        specificity: SourceSpecificity,
        subject: str | None = None,
        note: str | None = None,
    ) -> Claim:
        claim, reasons = fact_claim(
            entry,
            fact,
            claim_type,
            value,
            programme=programme,
            intake=intake,
            today=day,
            specificity=specificity,
            subject=subject,
            note=note,
        )
        if reasons:
            stale[len(claims)] = reasons
        claims.append(claim)
        return claim

    if entry.programme_known:
        evidence = entry.programme["evidence"][0]
        add(
            ClaimType.PROGRAM_EXISTS,
            True,
            {
                "key": "programme",
                "quote": evidence.get("quote"),
                "source_url": evidence.get("url"),
                "accessed_on": evidence.get("accessed_on"),
                "verified_on": evidence.get("verified_on") or entry.verified_on,
            },
            specificity=SourceSpecificity.PROGRAM,
        )
    subjects = _award_subjects(entry)
    for _question, fact in entry.all_facts():
        key = str(fact.get("key") or "")
        claim_type = claim_type_for(key)
        if claim_type is None or not fact.get("source_url"):
            continue
        value = fact.get("value")
        if str(value).lower() == NOT_APPLICABLE and _is_scholarship(fact):
            continue  # below, as the "no institutional scholarship" claim
        if claim_type is ClaimType.TUITION:
            value = tuition_value(value)
            if value is None:
                continue
        claim = add(
            claim_type,
            value,
            fact,
            specificity=_SPECIFICITY.get(claim_type, SourceSpecificity.UNIVERSITY_ADMISSIONS),
            subject=(
                _subject(fact, subjects) if claim_type.value.startswith("scholarship") else None
            ),
        )
        if (
            claim_type is ClaimType.TUITION
            and isinstance(value, dict)
            and claim.status is ClaimStatus.VERIFIED_CURRENT
            and str(fact.get("period") or "year").lower() in _ANNUAL
        ):
            # A printed range enters only as a range, at its upper bound (the
            # live path's rule, ``web_costs``): the cost is never understated.
            costs.items[CostCategory.TUITION] = Money(
                amount=value["amount"],
                currency=value["currency"],
                academic_year=fact.get("academic_year") or academic_year,
                source_url=claim.source_url,
                range_low=value.get("range_low"),
                range_high=value.get("range_high"),
            )
            costs.is_range = costs.is_range or "range_low" in value
            costs.source_urls.append(claim.source_url)
    for row in none_offered_rows(entry):
        # "No scholarship exists" for this applicant, with no award named: the
        # claim the funding outcome reads (app.knowledge.funding).
        add(
            ClaimType.SCHOLARSHIP_EXISTS,
            False,
            row,
            specificity=SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR,
            note="No institutional scholarship"
            + (f": {row['reason']}" if row.get("reason") else "."),
        )
    return KnowledgeAnswer(claims=claims, costs=costs, stale=stale)
