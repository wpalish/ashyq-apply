"""Knowledge-base facts as pipeline claims, and discovery from the catalogue without the web.

The claims use the product's own ``Claim`` model exactly as a live read would:
an official source, the verified quote as the excerpt, the confidence and
status the claim builder gives an official, quoted page
(``app.adapters.extraction.ClaimBuilder.add``: 0.8, ``VERIFIED_CURRENT``). A
stale fact (``app.knowledge.stale_reasons``) is ``POSSIBLY_STALE`` and says why.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.base import Candidate, CandidateProgram
from app.catalogue.retrieval import retrieve
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimStatus, ClaimType, CostCategory, DegreeLevel, SourceSpecificity
from app.knowledge import KnowledgeBase, KnowledgeEntry, review_label, stale_reasons
from app.models import University
from app.schemas.claim import Claim
from app.schemas.money import Money
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import CostBreakdown

#: ``app.adapters.extraction.ClaimBuilder.add``'s default for an official,
#: quoted page; the KB quote was found on that page by the CI evidence check.
OFFICIAL_QUOTED_CONFIDENCE = 0.8

#: Intended-field words the KB answers for (it covers Computer Science only).
_CS_WORDS = ("computer", "computing", "informatic", "informatik", "software")

KB_DISCOVERY_SOURCE = "knowledge-base"
#: Tuition periods the cost table (a yearly figure) can take as they are. A
#: per-semester or whole-programme figure stays a claim, published as it is.
_ANNUAL = frozenset({"year", "annual", "per year", "academic year", "yearly"})
NO_VERIFIED_DATA = "no verified data yet"
#: The KB value of a "does not apply" fact ("no scholarship for bachelor's").
NOT_APPLICABLE = "not_applicable"


def covers(profile: ApplicantProfileIn) -> bool:
    """Whether the applicant asks the one question the KB answers: a CS bachelor."""
    context = profile.context
    if context.level is not DegreeLevel.BACHELOR:
        return False
    fields = [f.lower() for f in context.intended_fields] or ["computer science"]
    return any(word in f for f in fields for word in _CS_WORDS)


def seed_id_of(uni: University) -> str | None:
    record = (uni.seed_snapshot or {}).get("record") or {}
    return str(record.get("seed_id") or "") or None


def entry_for(kb: KnowledgeBase, uni: University) -> KnowledgeEntry | None:
    return kb.get(seed_id_of(uni)) or kb.by_domain(uni.domain)


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
            title = next(
                (str(e.get("quote")) for e in programme.get("evidence") or [] if e.get("quote")),
                "Computer Science",
            )
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


@dataclass
class KnowledgeAnswer:
    """What the KB says for one programme row: claims, cost table, stale flags."""

    claims: list[Claim]
    costs: CostBreakdown
    stale: dict[int, list[str]]


def answer(
    entry: KnowledgeEntry,
    *,
    programme: str,
    intake: str,
    academic_year: str,
    today: date | None = None,
) -> KnowledgeAnswer:
    """Every KB fact of one entry as a claim; tuition also as the cost table."""
    today = today or datetime.now(UTC).date()
    built = _moment(entry.verified_on, datetime.now(UTC))
    label = review_label(entry.review_status)
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
        # The build's own reasons (a past cycle it saw) stay; today's are added.
        reasons = list(
            dict.fromkeys([*stale_reasons(fact, today, intake), *(fact.get("stale_reasons") or [])])
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
            if not isinstance(value, dict) or value.get("amount") is None:
                continue
            value = {"amount": float(value["amount"]), "currency": str(value["currency"])}
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
            costs.items[CostCategory.TUITION] = Money(
                amount=value["amount"],
                currency=value["currency"],
                academic_year=fact.get("academic_year") or academic_year,
                source_url=claim.source_url,
            )
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
