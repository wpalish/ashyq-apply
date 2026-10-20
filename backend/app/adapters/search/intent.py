"""What discovery is allowed to tell a search engine.

A provider logs whatever it is sent. A name, a score or a budget sent once
cannot be unsent, and it is sent on behalf of a person who asked for help
finding a university, not for their file to be handed to a vendor. So the
query generator does not take an applicant profile. It takes a
:class:`DiscoveryIntent`, which has room for the discovery dimensions and for
nothing else.

Two different guarantees are at work, and neither replaces the other:

* the search seam's signature takes a query string, so no profile *object*
  can reach a provider — see ``app.adapters.search.base``;
* :class:`DiscoveryIntent` validates its own values, so a profile *formatted
  into a string* cannot reach one either.

The second exists because the first is easy to satisfy while still leaking:
``f"{profile.display_name} bsc computer science"`` passes every type check
ever written.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from app.domain.enums import DegreeLevel

if TYPE_CHECKING:  # pragma: no cover - import kept out of the runtime path
    from app.schemas.profile import ApplicantProfileIn

#: The most queries one intent may produce. §4 of the phase guide: do not
#: explode aliases into unlimited queries. A budget also bounds spend and the
#: footprint left in a vendor's logs.
DEFAULT_QUERY_BUDGET = 6
#: Plan rule BL-1 (2026-10-05), off until a paired run passes: every stage's
#: provider queries count against one budget of DEFAULT_QUERY_BUDGET per
#: institution, kept on the candidate. Five cohort cases sent seven
#: (discovery six, then the scholarship search one), run 37279746829.
#: On by default since 2026-10-06 (owner: "Да"): its paired run had zero
#: losses, and seven-query cases fell from 10 to 0.
SHARED_QUERY_BUDGET = True
#: Queries topic search leaves for the scholarship search that runs after it.
SCHOLARSHIP_QUERY_RESERVE = 1
#: Plan rule QB-1 (evidence analysis 2026-10-17 §0 #1, §4 rank 1), on since
#: paired runs 39080847253 / 39080850234 / 39080851464 (QB-1 + QB-1b + FS-1:
#: Uppsala IELTS overall and subscores, Auckland IELTS overall stable gains,
#: 0 stable losses on cohort, dev2 and dev3); owner delegation 2026-10-17.
#: False turns it off. Programme discovery sent all six query families and
#: stopped only on HTTP 429, so under BL-1 topic search was left ``6 − 6 − 1``
#: queries and never ran, and the scholarship search was refused the same way:
#: on a site with no seeds nothing else can reach a university-level
#: admissions, fee or award page (every dev2 trace: ``search_calls == 6``; NTU,
#: whose slots were full before search, ran three topic queries and read the
#: general admission requirements). On: single-field discovery sends the first
#: DISCOVERY_FIRST_PASS_QUERIES families, reads and confirms their candidates,
#: and sends the remaining families only when no programme page is confirmed
#: by then. A confirmed page leaves the unsent queries in the shared budget for
#: topic search and the award search. Never more than DEFAULT_QUERY_BUDGET in
#: all; the confirm predicate is unchanged. The trace records
#: ``discovery_query_passes``. The benchmark harness flips it per capture
#: (``--discovery-query-reserve``).
DISCOVERY_QUERY_RESERVE = True
#: QB-1: query families the first discovery pass sends.
DISCOVERY_FIRST_PASS_QUERIES = 3
#: Plan rule QA-1 (discovery analysis 2026-10-17 §0 #3, §1.2), off until a paired
#: run passes. The operator families quoted the applicant's own words, which a
#: neural index reads for meaning but a keyword engine matches literally: an
#: English programme page titled "Informatics" that never says "computer
#: science" was missed by Serper 4/4 where Exa found it 4/4. On: the
#: field_and_degree, programmes and undergraduate families name the field as
#: an OR-group of the ontology's *strong* aliases — ``("computer science" OR
#: "computing science" OR computing OR informatics)`` — never a related
#: concept, so the page-subject confirm (which accepts the same aliases) still
#: decides. natural_language stays unquoted and in the applicant's words; the
#: number of queries and the shared budget (BL-1) are unchanged. Serper also
#: stops appending a second, identical ``site:``. The benchmark harness flips
#: it per capture (``--alias-queries``).
ALIAS_QUERIES = False
#: Plan v3 rule R5 (LQ-1, stage 3; ``discovery-v3-plan.md``), off until its
#: paired runs and a dev4 run pass (16-Q7). Every discovery query was English,
#: and Serper was never told a language, so six development programme pages
#: published only in the institution's language were never returned (ticket
#: 07). M5's probe (run 39126325681): ``site:{domain} "{alias}" {bachelor
#: word}`` with Serper ``hl``/``gl`` put the gold page in the top 10 on 5 of 6
#: local-language cases, today's ``field_and_degree`` on 1. On: for an
#: institution whose country (``DiscoveryIntent.institution_country``, the
#: institution's catalogue row — never the applicant) publishes in a language
#: other than English, and when the ontology has the field's alias in that
#: language and R1's table a bachelor's word for it, a ``local_language``
#: family takes the third first-pass slot and is sent with ``hl``/``gl`` of
#: that language and country; ``programmes`` moves to the reserve ahead of
#: ``courses`` and ``admissions`` is dropped, so six families stay six (07 Q3).
#: The first language of ``languages.json`` that has both words is used, one
#: family per institution. An institution in an English-speaking country, or
#: with no alias or degree word, keeps today's plan byte for byte. The
#: benchmark harness flips it per capture (``--local-language-queries``).
LOCAL_LANGUAGE_QUERIES = (
    True  # on: runs 39127583646 / 585479 / 587124 / 588639 (uba, iitd programme pages; 0 losses)
)
#: Plan rule LQ-2 (LQ-2a; ``LOCAL_LANGUAGE_LOCO_2026-10-20.md`` §5), off until a
#: search key makes it measurable (regime C: a new query text is a recorded-store
#: miss). R5 sends one alias per language, the first in the ontology, and that
#: alias reaches the title shape it was written from and misses its neighbours:
#: Spanish carries uba's plural «ciencias de la computación», puc's own title is
#: singular and tec's names neither. On, the one ``local_language`` query takes
#: its subject words from the site before the bundled lexicon:
#: (1) :attr:`DiscoveryIntent.local_phrase`, the text of a homepage or
#: catalogue link the navigation read classified as a programme listing or page,
#: in the page's ``<html lang>``, naming a localized alias's head — rendered as
#: one quoted phrase in place of the alias (the bachelor word follows unless the
#: phrase already holds it);
#: (2) else :attr:`DiscoveryIntent.native_name`, the seed row's native name, as
#: a second quoted phrase beside today's alias;
#: (3) else today's words, byte for byte.
#: Every phrase passes :func:`local_query_phrase` (at most
#: LOCAL_PHRASE_MAX_WORDS words, no digit, no personal name, nothing
#: :func:`_reject_applicant_data` refuses). Still one query of six, the same
#: first-pass slot and the same ``hl``/``gl``. The benchmark harness flips it
#: per capture (``--local-query-from-evidence``). False changes nothing.
LOCAL_QUERY_FROM_PAGE_EVIDENCE = False
#: LQ-2: the most words a page phrase may carry; a longer link text is refused,
#: not cut (a card's run-on description is not a programme's name).
LOCAL_PHRASE_MAX_WORDS = 8

#: Population markers that may appear in a query, and only for a country's
#: public requirements page. They describe a published policy audience, not
#: this applicant: "Kazakhstan admission requirements" is a page title, not a
#: statement that our applicant is Kazakhstani.
ALLOWED_POPULATION_MARKERS = frozenset({"international", "Kazakhstan"})

_EMAIL = re.compile(r"\S+@\S+")
_PHONE_OR_SCORE = re.compile(r"\d{3,}")
_MONEY = re.compile(r"[$€£₸]|\b(?:usd|eur|gbp|kzt)\b", re.IGNORECASE)
_GPA = re.compile(r"\b\d\.\d+\b")


class QueryPrivacyError(ValueError):
    """Raised when a value carries something a provider must never be told."""


def _reject_applicant_data(field: str, value: str) -> None:
    """Refuse a value that looks like it came off a profile.

    Deliberately blunt. A false positive here costs one caller a clearer
    phrasing; a false negative puts a real person's score in a vendor's logs
    forever. Years are the one numeric run a discovery query legitimately
    needs, and they are carried by ``intake_year`` rather than free text.
    """
    if _EMAIL.search(value):
        raise QueryPrivacyError(
            f"{field}={value!r} contains an email address. Contact details are never "
            "part of a discovery query."
        )
    if _MONEY.search(value):
        raise QueryPrivacyError(
            f"{field}={value!r} contains a currency amount. Budget and family "
            "contribution never leave this service."
        )
    if _GPA.search(value):
        raise QueryPrivacyError(
            f"{field}={value!r} looks like a grade. A search engine is asked where a "
            "programme is, never how well the applicant did."
        )
    if _PHONE_OR_SCORE.search(value):
        raise QueryPrivacyError(
            f"{field}={value!r} contains a long number, which is how a test score or a "
            "phone number gets into a query. Use intake_year for a year."
        )


@dataclass(frozen=True, slots=True)
class DiscoveryIntent:
    """The discovery question, with no room for anything else.

    Every field here is about a *programme*. There is deliberately no field
    for the applicant: adding one is the change that would need reviewing.
    """

    institution: str
    domain: str
    degree: DegreeLevel
    field: str
    #: Included in a query only when it plausibly narrows a result, e.g. a
    #: catalogue that publishes per-year pages.
    intake_year: int | None = None
    #: ``international`` or a country name, and only for a public
    #: requirements page. See :data:`ALLOWED_POPULATION_MARKERS`.
    population_marker: str = ""
    #: R5: the country the *institution* is in, from its catalogue or registry
    #: row — never the applicant's citizenship, residence or school country.
    #: Read only by :data:`LOCAL_LANGUAGE_QUERIES`, through :attr:`languages`.
    institution_country: str = ""
    #: LQ-2 (:data:`LOCAL_QUERY_FROM_PAGE_EVIDENCE`): the institution's own link
    #: text naming the field (a programme or listing link on its homepage or
    #: catalogue), already passed through :func:`local_query_phrase`. Never the
    #: applicant's words; empty while the rule is off.
    local_phrase: str = ""
    #: LQ-2: the seed row's native name of the institution, checked the same
    #: way; empty while the rule is off or the row carries none.
    native_name: str = ""

    def __post_init__(self) -> None:
        if not self.institution.strip():
            raise ValueError("A discovery intent needs an institution")
        if not self.domain.strip():
            raise ValueError("A discovery intent needs the institution's domain")
        if not self.field.strip():
            raise ValueError("A discovery intent needs a field of study")
        for name in (
            "institution",
            "domain",
            "field",
            "population_marker",
            "institution_country",
            "local_phrase",
            "native_name",
        ):
            _reject_applicant_data(name, getattr(self, name))
        if self.population_marker and self.population_marker not in ALLOWED_POPULATION_MARKERS:
            raise QueryPrivacyError(
                f"population_marker={self.population_marker!r} is not one of "
                f"{sorted(ALLOWED_POPULATION_MARKERS)}. A narrower audience describes this "
                "applicant rather than a published policy."
            )
        if self.intake_year is not None and not (2000 <= self.intake_year <= 2100):
            raise ValueError(f"intake_year={self.intake_year} is not a plausible intake year")

    @classmethod
    def from_profile(
        cls,
        profile: ApplicantProfileIn,
        *,
        institution: str,
        domain: str,
        field: str = "",
        include_intake: bool = False,
        population_marker: str = "",
    ) -> DiscoveryIntent:
        """The only sanctioned way to build an intent from a profile.

        It reads exactly three things — the degree level, the first intended
        field, and optionally the intake year — and ignores the rest of the
        object. Written once, here, so that every call site does not invent
        its own subset and quietly include one field too many.

        Dropped, explicitly: ``display_name``, every test score, every grade
        and GPA, the funding and family contribution, all activities,
        achievements, preferences and weights, citizenship, residence and
        graduation date. Citizenship is *not* forwarded even though it feels
        like a discovery dimension: use ``population_marker`` for a country's
        public requirements page, which is a statement about the page, not
        about the applicant.
        """
        context = profile.context
        chosen = field or (context.intended_fields[0] if context.intended_fields else "")
        return cls(
            institution=institution,
            domain=domain,
            degree=context.level,
            field=chosen,
            intake_year=context.intake_year if include_intake else None,
            population_marker=population_marker,
        )

    def without_intake(self) -> DiscoveryIntent:
        return replace(self, intake_year=None)

    @property
    def languages(self) -> tuple[str, ...]:
        """R5: the non-English languages the institution's country publishes in."""
        from app.adapters.search.ontology import country_languages

        return tuple(code for code in country_languages(self.institution_country) if code != "en")


@dataclass(frozen=True, slots=True)
class DiscoveryQuery:
    """One query, and which family it came from.

    The family travels with the text so telemetry can say *which kind* of
    query finds programme pages, which is the question V2-13 has to answer.
    ``hl``/``gl`` (R5 only) are the language and country a provider that takes
    them is told; empty for every other family.
    """

    text: str
    family: str
    hl: str = ""
    gl: str = ""


@dataclass(frozen=True, slots=True)
class LocalQueryTerms:
    """R5: the institution's own-language words for one ``local_language`` query.

    Every value is institution data or bundled vocabulary: ``language`` from
    ``languages.json`` for the institution's country, ``alias`` from the
    ontology's ``localized_aliases``, ``degree_word`` from R1's table
    (``page_classifier.local_bachelor_word``), ``hl``/``gl`` derived from the
    language and the country.
    """

    language: str
    alias: str
    degree_word: str
    hl: str
    gl: str
    #: LQ-2 only: the site's own words, sent as one quoted phrase.
    phrase: str | None = None
    #: LQ-2 only: where :attr:`phrase` came from, ``"link"`` (it replaces the
    #: alias) or ``"native_name"`` (it is sent beside the alias).
    phrase_source: str = ""


#: Google's ``hl`` for a language whose primary subtag it does not take as is.
_TRADITIONAL_CHINESE_REGIONS = frozenset({"tw", "hk", "mo"})


def _google_hl(language: str, region: str) -> str:
    if language == "zh":
        return "zh-tw" if region in _TRADITIONAL_CHINESE_REGIONS else "zh-cn"
    if language in {"nb", "nn"}:
        return "no"
    return language


def local_language_terms(intent: DiscoveryIntent) -> LocalQueryTerms | None:
    """R5: the local-language query words for ``intent``, or ``None`` for no family.

    ``None`` when the intent is not for a bachelor's (R1's table gives the
    family a bachelor's word only), when the institution's country publishes
    in English only or is unknown, or when no language of that country has
    both an ontology alias of the field and a degree word. The first language
    of ``languages.json`` (most common first) that has both is used.
    """
    if intent.degree is not DegreeLevel.BACHELOR:
        return None
    languages = intent.languages
    if not languages:
        return None
    from app.adapters import page_classifier
    from app.adapters.search.ontology import country_region, localized_aliases_in

    region = country_region(intent.institution_country)
    if not region:
        return None
    flags = page_classifier.localized_alias_flags()
    for language in languages:
        aliases = localized_aliases_in(intent.field, language, flags=flags)
        word = page_classifier.local_bachelor_word(language)
        if aliases and word:
            terms = LocalQueryTerms(
                language, aliases[0], word, _google_hl(language, region), region
            )
            return _with_page_phrase(terms, intent) if LOCAL_QUERY_FROM_PAGE_EVIDENCE else terms
    return None


def _with_page_phrase(terms: LocalQueryTerms, intent: DiscoveryIntent) -> LocalQueryTerms:
    """LQ-2: the site's link phrase, else the native name, else today's terms."""
    link = local_query_phrase(intent.local_phrase)
    if link is not None:
        return replace(terms, phrase=link, phrase_source="link")
    native = local_query_phrase(intent.native_name)
    if native is not None:
        return replace(terms, phrase=native, phrase_source="native_name")
    return terms


#: LQ-2: titles that put a person's name in a link text. A link naming a
#: professor or a dean is a staff page, and a query never carries a name.
_PERSONAL_TITLES = frozenset(
    {
        "prof",
        "professor",
        "profesor",
        "profesora",
        "professeur",
        "dr",
        "dra",
        "mr",
        "mrs",
        "ms",
        "mme",
        "sr",
        "sra",
        "herr",
        "frau",
        "dott",
        "dottssa",
        "doc",
        "проф",
        "профессор",
        "академик",
        "教授",
        "교수",
    }
)
#: LQ-2: quote marks a phrase loses before it is quoted again. Every double
#: quote a search engine may fold to ``"`` (fullwidth ＂, the reversed and low
#: ‟ „, the CJK 〝〞〟, the double primes ″ ‶), not only the common ones: one left
#: in a link text would close the phrase early and put the rest of the text,
#: operators included, outside it (security review 2026-10-22, SR2-04).
_PHRASE_QUOTES = re.compile('["“”„‟«»＂〝〞〟″‶]')
#: LQ-2: separators a link text may carry around its name. Brackets and full
#: stops stay: «Informatik (B.Sc.)» is the name as the site writes it.
_PHRASE_EDGE = " \t-–—|·•:;,"


def local_query_phrase(text: str) -> str | None:
    """LQ-2: ``text`` as a query phrase, or ``None`` when it may not be one.

    Refused: an empty text, more than LOCAL_PHRASE_MAX_WORDS words, any digit
    (a code, a year or a score), a personal title (a name follows it), an
    address or a URL, and anything :func:`_reject_applicant_data` refuses. The
    text is the institution's own; the checks keep it a programme's name and
    nothing that could be a person's.
    """
    phrase = re.sub(r"\s+", " ", _PHRASE_QUOTES.sub(" ", text or "")).strip(_PHRASE_EDGE)
    if not phrase:
        return None
    words = phrase.split(" ")
    if len(words) > LOCAL_PHRASE_MAX_WORDS:
        return None
    if any(ch.isdigit() for ch in phrase):
        return None
    folded = phrase.casefold()
    if "@" in folded or "http" in folded or "www." in folded:
        return None
    if any(re.sub(r"[.\-]", "", word.casefold()) in _PERSONAL_TITLES for word in words):
        return None
    try:
        _reject_applicant_data("local_phrase", phrase)
    except QueryPrivacyError:
        return None
    return phrase


def _quoted(term: str) -> str:
    """A multi-word term as a phrase; one word as it is (M5's shape)."""
    return f'"{term}"' if " " in term else term


def _degree_in_words(degree: DegreeLevel) -> str:
    """How a person names this level out loud, including the cycle wording.

    ``first cycle`` is what the Bologna catalogues that defeat a slug reader
    call a bachelor, and naming it is what reached Warsaw's page.
    """
    return {
        DegreeLevel.FOUNDATION: "foundation year",
        DegreeLevel.BACHELOR: "bachelor undergraduate first cycle",
        DegreeLevel.MASTER: "master second cycle",
        DegreeLevel.PHD: "doctoral PhD",
    }[degree]


def _degree_aliases(degree: DegreeLevel) -> str:
    return {
        DegreeLevel.FOUNDATION: "foundation",
        DegreeLevel.BACHELOR: "bachelor",
        DegreeLevel.MASTER: "master",
        DegreeLevel.PHD: "phd",
    }[degree]


def _field_terms(field: str) -> str:
    """The field as a query term: quoted, or (QA-1) an OR-group of its strong aliases.

    Aliases come from the bundled ontology, never from the applicant, so the
    group carries nothing the intent did not already validate.
    """
    quoted = f'"{field}"'
    if not ALIAS_QUERIES:
        return quoted
    from app.adapters.search.ontology import canonical_field, load_ontology

    key = canonical_field(field)
    if key is None:
        return quoted
    names = [field]
    for alias in load_ontology().fields[key]["strong_aliases"]:
        if alias.casefold() not in (name.casefold() for name in names):
            names.append(alias)
    if len(names) == 1:
        return quoted
    return "(" + " OR ".join(f'"{n}"' if " " in n else n for n in names) + ")"


def queries_for(
    intent: DiscoveryIntent,
    *,
    budget: int = DEFAULT_QUERY_BUDGET,
    families: Sequence[str] = (),
    site_prefix: bool = True,
) -> tuple[DiscoveryQuery, ...]:
    """Render an intent into at most ``budget`` queries, best first.

    The order is the order of usefulness observed in the phase guide: the
    most specific query first, so a caller that can afford only one or two
    still gets the ones most likely to land on a programme page.
    """
    if budget < 1:
        raise ValueError(f"A query budget must be at least 1, got {budget}")

    # ``site:`` is keyword-search syntax. A provider that takes a domain filter
    # is already being told the domain, and repeating it inside the query text
    # is noise — on a neural index it skews the query's meaning rather than
    # narrowing it. Measured: with ``site:`` our queries never retrieved
    # Warsaw's bachelor page; without it, a query naming the cycle in plain
    # language returned it first.
    site = f"site:{intent.domain}" if site_prefix else intent.institution
    degree = _degree_aliases(intent.degree)
    year = f" {intent.intake_year}" if intent.intake_year else ""
    terms = _field_terms(intent.field)
    local = local_language_terms(intent) if LOCAL_LANGUAGE_QUERIES else None
    candidates: list[DiscoveryQuery] = [
        DiscoveryQuery(f'{site} {terms} "{degree}"{year}', "field_and_degree"),
        # Phrased the way a person would ask, with no search operators and no
        # quoting. The other families are five variations of one shape —
        # ``site:`` plus quoted terms — which is keyword syntax; a neural index
        # reads a query for meaning, so five variations of one shape are one
        # query asked five times. Measured: this shape returns Warsaw's
        # bachelor page first where the operator shape never returns it at all.
        DiscoveryQuery(
            f"{intent.institution} {_degree_in_words(intent.degree)} "
            f"{intent.field} programme{year}",
            "natural_language",
        ),
    ]
    if local is not None:
        # R5 (07 Q3): the third first-pass slot, in the site's language. No
        # intake year: M5 measured the shape without one.
        text = f"{site} {_quoted(local.alias)} {_quoted(local.degree_word)}"
        if local.phrase and local.phrase_source == "link":
            # LQ-2: the site's own name for the programme replaces the alias.
            text = f'{site} "{local.phrase}"'
            if local.degree_word.casefold() not in local.phrase.casefold():
                text += f" {_quoted(local.degree_word)}"
        elif local.phrase:
            # LQ-2: the institution's native name, beside today's words.
            text = f'{site} "{local.phrase}" {_quoted(local.alias)} {_quoted(local.degree_word)}'
        _reject_applicant_data("local_language", text)
        candidates.append(DiscoveryQuery(text, "local_language", hl=local.hl, gl=local.gl))
    candidates += [
        DiscoveryQuery(f"{site} programmes {terms}{year}", "programmes"),
        DiscoveryQuery(f'{site} courses "{intent.field}"{year}', "courses"),
        DiscoveryQuery(f"{site} undergraduate {terms}", "undergraduate"),
    ]
    if local is None:
        # R5 drops it for a local-language site: it never confirmed a page in
        # the development captures, and topic search does its job better.
        candidates.append(DiscoveryQuery(f"{site} admissions {degree}", "admissions"))
    if intent.population_marker:
        candidates.append(
            DiscoveryQuery(
                f"{site} {intent.population_marker} admission requirements",
                "country_requirements",
            )
        )
        candidates.append(
            DiscoveryQuery(
                f"{site} scholarships {intent.population_marker} {degree}",
                "scholarships",
            )
        )
        award_degree = {
            DegreeLevel.FOUNDATION: "foundation",
            DegreeLevel.BACHELOR: "(bachelor OR undergraduate)",
            DegreeLevel.MASTER: "(master OR postgraduate)",
            DegreeLevel.PHD: "(phd OR doctoral)",
        }[intent.degree]
        candidates.append(
            DiscoveryQuery(
                f"{site} scholarship {intent.population_marker} {award_degree} eligibility benefits",
                "award_policy",
            )
        )

    if families:
        wanted = set(families)
        unknown = wanted - {q.family for q in candidates}
        if unknown:
            raise ValueError(f"Unknown query families: {sorted(unknown)}")
        candidates = [q for q in candidates if q.family in wanted]

    return tuple(candidates[:budget])


@dataclass(frozen=True, slots=True)
class QueryAuditRecord:
    """What is safe to keep about a query we ran.

    The phase guide asks for a *redacted* audit record. Keeping the full
    query text in our own logs would recreate, on our side, exactly the
    trail we are careful not to leave on the vendor's.
    """

    institution: str
    domain: str
    degree: str
    field: str
    family: str
    provider: str
    result_count: int
    intake_year: int | None = None
    population_marker: str = ""


def redacted_audit_record(
    intent: DiscoveryIntent,
    query: DiscoveryQuery,
    *,
    provider: str,
    result_count: int,
) -> QueryAuditRecord:
    """Describe a search without storing its text."""
    return QueryAuditRecord(
        institution=intent.institution,
        domain=intent.domain,
        degree=str(intent.degree),
        field=intent.field,
        family=query.family,
        provider=provider,
        result_count=result_count,
        intake_year=intent.intake_year,
        population_marker=intent.population_marker,
    )
