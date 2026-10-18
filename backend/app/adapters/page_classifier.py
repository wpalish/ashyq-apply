"""What kind of page is this?

Every false positive found in the first live run had the same shape: an
extractor ran on a page that could not possibly answer the question it was
asking. A page titled "Check admission requirements | BSc Dutch diploma"
cannot confirm that a computer science bachelor's programme exists; a page
titled "Scholarships" is not a scholarship.

Classification happens once per page, from the URL, the title, the headings and
the body structure. Extractors declare which classes they accept and are not
run otherwise. The classifier is deliberately conservative: when the signals do
not add up it returns UNKNOWN, and UNKNOWN is accepted by nothing.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

#: Plan rule PG-1 (discovery analysis 2026-10-17 §0 #5, §1.2, §4 rank 5), off
#: until a paired run passes. Identity recovery spent its eight reads on
#: publications, news and archives, and the classifier accepted some of that
#: junk: TUM/Serper reported ``portal.fis.tum.de/en/publications/…/fingerprints``
#: as its bachelor because the URL-only IRRELEVANT hint rejects only with two
#: research words in the body and a Pure "fingerprints" page has none; HKU
#: reported the department root ``cs.hku.hk/``. On, one rule in three places:
#: (i) the search prefilter drops URLs :func:`classify_url` calls IRRELEVANT,
#: plus archive hosts, and discovery's excluded paths learn ``/publications/``,
#: ``/article/``, ``news-single-view`` and ``/clippings/``; (ii)
#: :func:`classify_page` returns at most UNKNOWN instead of a programme type
#: for a URL-IRRELEVANT page or a host root unless the body shows at least
#: PROGRAMME_STRUCTURE_MIN programme-structure signals (credits, duration,
#: admission requirements, start of studies, tuition); (iii) identity recovery
#: no longer promotes unread search leads to programme pages — they are kept as
#: ``unresolved`` in the discovery trace. The flag lives here because this is
#: the lowest module the three call sites share; they read it at call time.
#: The benchmark harness flips it per capture (``--programme-page-guard``).
#: On since paired runs 39067949720 (cohort) and 39067951214 (dev2): no label
#: change, 0 losses; unread or non-programme pages (a PDF, a researcher profile,
#: a minor, a host root) are no longer reported as the programme. Owner
#: delegation 2026-10-17. False turns it off.
PROGRAMME_PAGE_GUARD = True
#: Plan rule CL-1 (evidence analysis 2026-10-17 §0 #2, §1.2, §4 rank 3), on
#: since paired runs 39074829596 (cohort: Groningen IELTS a stable gain) and
#: 39074831170 (dev2: TCD and Uppsala programme pages found in both
#: repetitions), 0 losses, 0 wrong claims; owner delegation 2026-10-17. False
#: turns it off. ``_CATALOG`` was matched against the title and
#: every h1/h2 joined into one string, so catalogue words from two unrelated
#: headings made a real programme page a catalogue: TCD's course page
#: ("Computer Science - Courses | …" + h2 "Overview") read ``courses … overview``
#: and Uppsala's ("Bachelor's Programme in Computer Science" + "Admitted or on
#: the waiting list") read ``programme … list``; the walker rejected both. On,
#: ``_CATALOG`` is tested against the page's identity (its h1, else the title
#: before the site suffix) and against the title, each on its own, never the
#: concatenation of every heading. ``_PLURAL_PROGRAM_HEADING`` and the
#: many-links/no-identity rule are unchanged, so a page whose own title or h1
#: is catalogue-shaped ("Undergraduate courses", "Find a course") still is one.
#: The benchmark harness flips it per capture (``--catalog-heading-scope``).
CATALOG_HEADING_SCOPE = True
#: Plan rule LX-1 (dev3 discovery analysis 2026-10-18 §1, §3 fix C), off until
#: a paired run passes. Four lexicon gaps decided dev3 pages: IIT Delhi's
#: "BTech in CSE" read UNKNOWN because no degree word knew B.Tech; PUC's
#: "Licenciatura en Ingeniería en Ciencia de la Computación" had no degree
#: word either; Auckland's "Undergraduate study in Computer Science" entered
#: the funding family on an h2 "Scholarships and awards" and came out a
#: scholarship index (the defect CL-1 fixed for ``_CATALOG``); and PG-1 knew
#: ``/publications/`` but not ``/publicaciones/`` (PUC's false positive) nor the
#: ``lirias.`` repository host (three of KU Leuven's eight reads). On: (i)
#: ``_degree_level`` also reads ``_LEXICON_V2_DEGREE_WORDS`` (B.Tech/BTech →
#: bachelor, M.Tech → master, licenciatura, "grado en", "bachillerato en",
#: bachelorprogram/-studium/… compounds → bachelor) and discovery's
#: ``degree_level_named`` the ``b-tech``/``m-tech`` slugs; (ii) the funding
#: gate tests ``_SCHOLARSHIP_WORD`` on the page's identity (h1, else the title
#: before the site suffix) and on the title, each on its own, never on every
#: heading joined; (iii) the ontology entries marked ``"flag": "LEXICON_V2"``
#: (informatikk, datalogi, informàtica, ciencia de la computación; not
#: "enginyeria informàtica", computer engineering, refused like the Italian
#: "ingegneria informatica") join discovery's localized identity aliases — never the strong
#: aliases or the query terms; (iv) PG-1's publication path words and research
#: hosts learn ``publicaciones``/``publicacion``/``publicaties``/
#: ``publikasjoner`` and ``lirias``. One flag for all four, read at call time
#: by every module that applies a part; the benchmark harness flips it per
#: capture (``--lexicon-v2``). False (the default) changes nothing.
LEXICON_V2 = False
#: Plan v3 rule R1 (LI-2, stage 4(a); ``discovery-v3-plan.md``), off until its
#: paired runs and a dev4 run pass (16-Q7). No development programme page was
#: ever confirmed through a local-language page: the degree words were English
#: (plus LX-1's Spanish/Indian subset, off), so UBA's "Licenciatura en Ciencias
#: de la Computación", PUC's licenciatura and Paris-Saclay's French "licence"
#: page read UNKNOWN, and nothing in page text knew a local master's word
#: either. On: (i) ``_degree_level`` also reads ``_LOCALIZED_DEGREE_WORDS`` —
#: bachelor **and** master words for every language in ``languages.json``
#: (earliest match wins; on a tie the master's word wins, and a master's
#: compound such as "laurea magistrale" or "yüksek lisans" is never read as its
#: bachelor stem); a word that means something else in another language
#: ("licence", "kandidat", "kandidaat") counts only under the page's own
#: ``<html lang>``. LX-1's degree words (B.Tech, licenciatura, "grado en",
#: bachelor compounds) are part of the table, and discovery reads LX-1's
#: ``b-tech`` slugs (16-Q4: R1 absorbs LX-1's degree and subject parts). (ii)
#: discovery's localized identity aliases include the ontology entries flagged
#: ``LOCALIZED_PAGE_IDENTITY`` and ``LEXICON_V2``, the localized
#: ``related_not_equivalent`` forms are refused by name, local bachelor words
#: are title filler (master's words never are), and a title in an unspaced
#: script (ja, zh, ko, th) is matched on the alias with only degree words left;
#: (iii) an English programme candidate that is refused has its declared twin
#: in a language of the institution's country read once, inside the same cap.
#: Not part of R1: LX-1's funding gate (that is FI-1's flag — the Imperial
#: wrong deadline of LX-1's run came through it) and LX-1's publication paths.
#: The benchmark harness flips it per capture (``--localized-page-identity``).
#: On since paired runs 39119685301 / 39119686849 / 39119688512 / 39119690148
#: (dev4 rwth stable gain, 0 losses, 0 new wrong claims); False turns it off.
LOCALIZED_PAGE_IDENTITY = True
#: Plan rule FI-1 (wrong-claims analysis 2026-10-18 R-D1): part (ii) of LX-1 on
#: its own, so the funding-gate scope can be measured without the lexicon. UNSW's
#: own "Bachelor of Science (Computer Science)" page lists one scholarship link
#: under an h2 and read as a scholarship index, so identity recovery refused it
#: and confirmed the Bengaluru campus page instead; Auckland's "Undergraduate
#: study in Computer Science" (h2 "Scholarships and awards") is the same shape.
#: On: ``_SCHOLARSHIP_WORD`` is tested on the page's identity (h1, else the
#: title before the site suffix) and on the title, each on its own, never on
#: every heading joined. ``LEXICON_V2`` turns it on as well (either flag
#: enables it). The benchmark harness flips it per capture
#: (``--funding-identity-scope``). False (the default) changes nothing.
FUNDING_IDENTITY_SCOPE = True
#: Plan rule AP-1 (core-gap analysis 2026-10-18, change 1), off until a paired
#: run passes. Six known scholarship answers sat on pages the funding walk had
#: already read and threw away. Imperial's "Imperial Inspires Scholarships
#: (Undergraduate)" award page links its own hub and the fees page, so the
#: link-count rule called it an index before the named-award rule ran; UBC's
#: International Major Entrance Scholarship and TCD's Undergraduate E3
#: Scholarship are described, eligibility and all, under their own headings
#: on an index page, and nothing is ever recorded from an index; TCD's index
#: was refused besides, because the depth-0 index had used up the index
#: budget; HKU's School of Computing and Data Science scholarships page is
#: linked from the confirmed programme page's navigation only, which
#: ``_award_links`` never reads. On: (i) in the funding branch the named-award
#: rule runs before the link-count rule when the identity is a proper award
#: name (``proper_award_name``) and the page links fewer than three awards
#: below its own path; (ii) an index's own sections under a proper award-name
#: heading are read as awards — existence and international applicability
#: from that section's eligibility sentences only, no amount, coverage or
#: deadline, and a heading naming another level or a section restricted to
#: another faculty claims nothing; (iii) the depth-0 index read is not
#: charged to the index budget, and an index past the budget still has its
#: own sections read; (iv) one "Scholarships" link in the navigation of the
#: confirmed programme page or the admissions page is followed when its
#: content links no award, on the same registrable domain, charged to the
#: read ledger as an award read. The flag lives here because this is the
#: lowest module its two call sites share; ``web_scholarships`` reads it at
#: call time. The benchmark harness flips it per capture
#: (``--award-page-evidence``). False (the default) changes nothing.
AWARD_PAGE_EVIDENCE = False
#: PG-1: structure signals a guarded page needs to stay a programme page.
PROGRAMME_STRUCTURE_MIN = 2
#: PG-1: what a programme page states and a publication, a department home or
#: a blog post does not. Each pattern counts once, however often it matches.
_PROGRAMME_STRUCTURE: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "credits",
        re.compile(r"\bects\b|\b\d{2,3}\s*(?:credits?|credit points|cp|study points)\b", re.I),
    ),
    (
        "duration",
        re.compile(
            r"\b(?:\d{1,2}|two|three|four|five|six|seven|eight|ten|twelve)\s+semesters?\b"
            r"|\bstandard period of study\b|\b(?:programme|program|study|course)\s+duration\b"
            r"|\bduration\s*(?::|of\s+(?:the\s+)?(?:programme|program|studies|study))",
            re.I,
        ),
    ),
    (
        "admission_requirements",
        re.compile(r"\b(?:admission|entry|entrance)\s+requirements?\b", re.I),
    ),
    (
        "start",
        re.compile(
            r"\bstart of (?:studies|study|the programme|the program|programme|program)\b"
            r"|\b(?:study|programme|program) start\b|\bbeginning of studies\b|\bintakes?\b"
            r"|\bcommencement of studies\b",
            re.I,
        ),
    ),
    (
        "tuition",
        re.compile(r"\btuition\b|\bsemester (?:fee|contribution)s?\b|\bstudy fees?\b", re.I),
    ),
)
#: PG-1: a host root, optionally one language segment or an index document.
_HOST_ROOT_PATH = re.compile(r"^/?(?:[a-z]{2}(?:[-_][a-z]{2})?/?)?(?:index\.(?:html?|php))?$", re.I)


def programme_structure_signals(text: str) -> list[str]:
    """PG-1: the programme-structure signals a page's own text shows."""
    return [name for name, pattern in _PROGRAMME_STRUCTURE if pattern.search(text or "")]


_HTML_LANG = re.compile(r"<html[^>]*\blang\s*=\s*[\"']?([a-z]{2})", re.I)
#: Two-letter language codes that are also programme abbreviations in a URL
#: (computer science, IT, AI, information systems, machine learning, electrical,
#: civil, mechanical engineering). Without the page's own lang attribute they
#: are read as a programme path, never as a language root.
_SUBJECT_LIKE_CODES = frozenset({"cs", "it", "ai", "is", "ml", "ee", "ce", "me"})
_LANGUAGE_SEGMENT = re.compile(r"^/?([a-z]{2})(?:[-_][a-z]{2})?/?(?:index\.(?:html?|php))?$", re.I)


def is_host_root(url: str, html: str = "") -> bool:
    """PG-1: a site's home page, which is a department or a portal, not a programme.

    A bare host (``/``, ``/index.html``) always counts. A single two-letter
    segment (``/en/``) counts only when the page itself is in that language:
    ``/cs`` is also where a computer-science programme lives, and "cs" is
    Czech, so the path alone cannot tell a language root from a programme.
    """
    parts = urlparse(url)
    path = parts.path or ""
    if parts.query or not _HOST_ROOT_PATH.match(path):
        return False
    segment = _LANGUAGE_SEGMENT.match(path)
    if not segment:
        return True
    code = segment.group(1).lower()
    lang = _HTML_LANG.search(html or "")
    if lang:
        return lang.group(1).lower() == code
    return code not in _SUBJECT_LIKE_CODES


class PageType(StrEnum):
    PROGRAM_DETAIL = "program_detail"
    PROGRAM_CATALOG = "program_catalog"
    INTAKE_SPECIFIC_PROGRAM = "intake_specific_program"
    GENERAL_ADMISSIONS = "general_admissions"
    COUNTRY_CREDENTIAL_REQUIREMENTS = "country_credential_requirements"
    SCHOLARSHIP_INDEX = "scholarship_index"
    SCHOLARSHIP_AWARD = "scholarship_award"
    SCHOLARSHIP_FAQ = "scholarship_faq"
    COSTS = "costs"
    DOCUMENTS = "documents"
    NEWS = "news"
    NAVIGATION = "navigation"
    IRRELEVANT = "irrelevant"
    UNKNOWN = "unknown"


#: Page classes each extractor is permitted to run on. Anything else is skipped
#: and reported, never guessed at.
ACCEPTS: dict[str, frozenset[PageType]] = {
    "program_exists": frozenset({PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM}),
    "requirements": frozenset(
        {
            PageType.PROGRAM_DETAIL,
            PageType.INTAKE_SPECIFIC_PROGRAM,
            PageType.GENERAL_ADMISSIONS,
            PageType.COUNTRY_CREDENTIAL_REQUIREMENTS,
        }
    ),
    "intake": frozenset({PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM}),
    "costs": frozenset({PageType.COSTS, PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM}),
    "scholarship_award": frozenset({PageType.SCHOLARSHIP_AWARD}),
    # A fees page often lists the awards alongside the costs; following its
    # links is safe because each target must classify as an award itself.
    "scholarship_links": frozenset(
        {
            PageType.SCHOLARSHIP_INDEX,
            PageType.SCHOLARSHIP_AWARD,
            PageType.COSTS,
        }
    ),
    "documents": frozenset(
        {
            PageType.DOCUMENTS,
            PageType.PROGRAM_DETAIL,
            PageType.INTAKE_SPECIFIC_PROGRAM,
            PageType.GENERAL_ADMISSIONS,
            PageType.SCHOLARSHIP_AWARD,
        }
    ),
}


@dataclass(frozen=True)
class PageClassification:
    page_type: PageType
    confidence: float
    signals: list[str] = field(default_factory=list)
    title: str = ""
    #: Present when the page identifies one programme or one award.
    subject: str | None = None
    degree_level: str | None = None
    language_of_instruction: str | None = None
    academic_year: str | None = None
    #: Complete main-content title/label proof; None keeps the prose route.
    language_evidence: str | None = None

    def accepts(self, extractor: str) -> bool:
        return self.page_type in ACCEPTS.get(extractor, frozenset())


# --- signal vocabularies ---------------------------------------------------

_DEGREE_WORDS: tuple[tuple[str, str], ...] = (
    (r"\bph\.?d\b|\bdoctoral\b|\bdoctorate\b", "phd"),
    (r"\bmaster'?s?\b|\bm\.?sc\b|\bm\.?a\b\.?|\bmphil\b|\bllm\b|\bmba\b", "master"),
    (r"\bbachelor'?s?\b|\bb\.?sc\b|\bb\.?a\b\.?|\bbeng\b|\bllb\b|\bundergraduate\b", "bachelor"),
    (r"\bfoundation year\b|\bpre-?bachelor\b", "foundation"),
)
#: LX-1 only (``LEXICON_V2``): degree words the base table misses. The
#: Spanish "bachillerato" is a school-leaving qualification in Spain and a
#: university bachelor in Central America; only "bachillerato en …" /
#: "bachillerato universitario" counts, so an admissions page asking for the
#: Spanish Bachillerato does not become a bachelor page. "grado" alone is any
#: degree; "grado en …" is the Spanish bachelor's title.
_LEXICON_V2_DEGREE_WORDS: tuple[tuple[str, str], ...] = (
    (r"\bm\.?\s?tech\b|\bmaster of technology\b", "master"),
    (
        r"\bb\.?\s?tech\b|\bbachelor of technology\b|\blicenciatura\b|\bgrado en\b"
        r"|\bbachillerato (?:en|universitario)\b"
        r"|\bbachelor(?:program(?:me|ma|met)?|programm|opleiding|studium|studiengang"
        r"|studier?|grad(?:en)?)\b",
        "bachelor",
    ),
)
#: R1 (``LOCALIZED_PAGE_IDENTITY``): degree words in page text, per language,
#: as ``(pattern, level, languages)``. ``languages`` is ``None`` when the word
#: is certain in any page, else the ``<html lang>`` primary subtags under which
#: it counts. Master's words come first so that a tie goes to the master's.
#: Dictionary words only, the same shape for every language, matched on the
#: lowercased text (Turkish "İ" lowercases to "i" + U+0307, hence ``\u0307?``).
_LOCALIZED_DEGREE_WORDS: tuple[tuple[str, str, frozenset[str] | None], ...] = (
    # --- master's ---------------------------------------------------------
    # de/nl/da/no/sv compounds: Masterstudium, masteropleiding, masterprogram.
    (
        r"\bmaster(?:program(?:me|ma|met)?|programm|opleiding|studium|studiengang"
        r"|studier?|grad(?:en)?|uddannelse(?:n)?)\b",
        "master",
        None,
    ),
    # es/pt/ca: máster, maestría, magíster, mestrado, pós-graduação.
    (
        r"\bm[áà]ster\b|\bmaestr[ií]as?\b|\bmag[íi]ster\b|\bmestrados?\b"
        r"|\bp[óo]s[-\s]?gradua[çc][ãa]o\b",
        "master",
        None,
    ),
    (r"\blaurea\s+(?:magistrale|specialistica)\b", "master", None),  # it
    (r"\by[üu]ksek\s+l[iı]\u0307?sans\b", "master", None),  # tr
    # cs/sk/pl/et/lt/sv/de: magisterský, magisterskie, magistriõpe, magistras,
    # magistrantūra, magisterprogram — never "magistrate" or "magistral".
    (r"\bmagist(?:er|r)(?!at|al|ial)\w*|\bnavazuj[íi]c[íi]\b", "master", None),
    (r"\bstudia drugiego stopnia\b", "master", None),  # pl
    (r"\bmaisteri\w*", "master", None),  # fi
    (r"\bkandidatuddannelse\w*", "master", None),  # da
    (r"\bkandidat\w*", "master", frozenset({"da", "no", "nb", "nn"})),
    (r"магистр\w*", "master", None),  # ru/kk
    (r"大学院|修士|硕士|碩士|研究生", "master", None),  # ja/zh
    (r"석사|대학원", "master", None),  # ko
    (r"ปริญญาโท", "master", None),  # th
    # --- bachelor's -------------------------------------------------------
    (r"\blicence\b", "bachelor", frozenset({"fr"})),
    (r"\blaurea\b(?!\s+(?:magistrale|specialistica)\b)", "bachelor", None),  # it
    (
        r"(?<!yüksek )(?<!yuksek )(?<!ön )\bl[iı]\u0307?sans(?![üu]st)",
        "bachelor",
        None,
    ),  # tr
    (r"\bbakal[áa][řr]\w*", "bachelor", None),  # cs/sk
    (r"\bbakalaur\w*", "bachelor", None),  # et/lt
    (
        r"\blicencja(?:t|ck)\w*|\bstudia (?:pierwszego stopnia|in[żz]ynierskie)\b",
        "bachelor",
        None,
    ),  # pl
    (r"\bbacharel(?:ado)?\b|(?<!p[óo]s-)(?<!p[óo]s )\bgradua[çc][ãa]o\b", "bachelor", None),
    (r"\bgrau (?:en|d['’])", "bachelor", None),  # ca
    (r"\bkandidat(?:program\w*|examen)\b", "bachelor", frozenset({"sv"})),
    (r"\bkandidaat\w*", "bachelor", frozenset({"fi"})),
    (r"\bbachelor(?:uddannelse(?:n)?|opleiding)\b", "bachelor", None),  # da/nl
    (r"бакалавр\w*", "bachelor", None),  # ru/kk
    # "学部" is also a faculty (理学部) and in Chinese a division (信息学部);
    # as a level it is Japanese only. Korean "학부" alone is a school (전산학부).
    (r"学部", "bachelor", frozenset({"ja"})),
    (r"学士|學士|本科", "bachelor", None),  # ja/zh
    (r"학부\s?(?:과정|생)|학사\s?(?:학위|과정)", "bachelor", None),  # ko
    (r"ปริญญาตรี", "bachelor", None),  # th
)
#: Plan v3 R5 (``LOCAL_LANGUAGE_QUERIES``): the one bachelor's word a query
#: names the level by, per language of ``languages.json``. Not a second degree
#: table: each is a headword of the patterns above, and
#: :func:`local_bachelor_word` hands it out only while this module's own table
#: (``_DEGREE_WORDS``, LX-1's and R1's words, under that page language) reads it
#: as a bachelor's and nothing else, so a word can never drift from what the
#: confirm step accepts. M5's words where the probe measured one (es
#: licenciatura, fr licence, no/da/nl bachelor, zh 本科, th ปริญญาตรี). Catalan
#: has none: "grau" alone is not R1's "grau en", so a ca site gets no family.
_LOCAL_BACHELOR_QUERY_WORDS: dict[str, str] = {
    "es": "licenciatura",
    "pt": "bacharelado",
    "fr": "licence",
    "it": "laurea",
    "de": "bachelor",
    "nl": "bachelor",
    "da": "bachelor",
    "no": "bachelor",
    "nb": "bachelor",
    "nn": "bachelor",
    "sv": "kandidatprogram",
    "fi": "kandidaatti",
    "cs": "bakalářský",
    "sk": "bakalársky",
    "pl": "licencjat",
    "et": "bakalaureus",
    "lt": "bakalauras",
    "ru": "бакалавриат",
    "kk": "бакалавр",
    "tr": "lisans",
    "ja": "学士",
    "zh": "本科",
    "ko": "학사과정",
    "th": "ปริญญาตรี",
}
_CATALOG = re.compile(
    r"\b(programmes?|programs?|courses?|degrees?|studies)\b.*\b(overview|list|all|browse|find|search|a-?z)\b"
    r"|\b(all|our|browse|find|search)\b.*\b(programmes?|programs?|courses?|degrees?)\b",
    re.IGNORECASE,
)
#: A heading that is a plural category is a listing, never one programme or one
#: award. "Bachelor's programmes" is a catalogue; "BSc Computer Science" is not.
_PLURAL_PROGRAM_HEADING = re.compile(
    r"^\s*((our|all|browse|find|search|list of|overview of)\s+)?"
    r"((bachelor'?s?|master'?s?|undergraduate|postgraduate|graduate|phd|doctoral)\s+)?"
    r"(programmes?|programs?|courses?|degrees?|studies)\s*$",
    re.IGNORECASE,
)
_PLURAL_FUNDING_HEADING = re.compile(
    r"^\s*((our|all|available|list of|overview of|other|external)\s+)?"
    r"(scholarships|funding|financial aid|grants|bursaries|awards|fellowships|stipends"
    r"|prizes and awards|practical matters)"
    # A plural category followed by a scope phrase is still a listing:
    # "Scholarships from other providers", "Grants for international students".
    r"(\s+(and|&|from|for|at|by|in|of|to)\s+.{0,60})?\s*$",
    re.IGNORECASE,
)
_ADMISSIONS = re.compile(
    r"admission requirements|entry requirements|how to apply|application procedure"
    # Vienna heads its admissions page "Admission procedure" (run 32).
    r"|admissions? (?:procedure|process)"
    r"|admission and application|apply for admission|entry criteria"
    # A page headed "International admissions" or "Undergraduate admissions" is
    # a general admissions page even though it never says "requirements".
    r"|\b(?:international|undergraduate|graduate|postgraduate|general)\s+admissions?\b"
    r"|\badmissions?\b\s*(?:-|–|\||$)|general entry information",
    re.IGNORECASE,
)
#: The school-qualification names this repository recognises, as one
#: alternation so there is exactly one such list. ``app.adapters.scope_reader``
#: reads a page's stated qualification from the same vocabulary — a second
#: list would drift from this one, and the two would disagree about what the
#: page said.
QUALIFICATION_NAMES = r"vwo|abitur|attestat|baccalaur|a-?levels?|matura|gaokao|cbse"

_CREDENTIAL = re.compile(
    r"\b(diploma|qualification|certificate)\b[^.]{0,60}\b(equivalen|recogni|accept|assess)"
    rf"|\b({QUALIFICATION_NAMES})\b",
    re.IGNORECASE,
)
_SCHOLARSHIP_WORD = re.compile(
    r"scholarship|bursar|grant|fellowship|financial aid|stipend|funding|beurs|stipendium",
    re.IGNORECASE,
)
_FAQ = re.compile(
    # The plural matters: "\bf\.?a\.?q\.?\b" does not match "FAQs", because there is no
    # word boundary between the q and the s. NTU's "FAQs on scholarships" therefore
    # classified as an award page, became a scholarship named after the FAQ, and its
    # own prose then produced a second claim saying that award did not exist.
    r"\bf\.?a\.?q\.?s?\b|frequently asked questions?",
    re.IGNORECASE,
)
_RESEARCH_OUTPUT = re.compile(
    r"\b(abstract|doi|peer[- ]reviewed|research output|journal|proceedings|conference paper"
    r"|published in|isbn|issn|citation)\b",
    re.IGNORECASE,
)
_NEWS = re.compile(r"\b(news|press release|announcement|blog|article)\b", re.IGNORECASE)
_IRRELEVANT = re.compile(
    r"\b(vacanc|job openings?|careers? (?:at|portal|site)|recruitment|staff directory"
    r"|alumni|donate|shop|library catalogue|contact us|privacy (?:policy|statement)"
    r"|cookie|sitemap|nobel prize|erc grant|research (?:prize|award)s?)\b",
    re.IGNORECASE,
)
#: Plurals matter: `\btuition fee\b` does not match "tuition fees", which is how
#: a fees page ended up classified as general admissions.
_COSTS = re.compile(
    r"\b(tuition fees?|registration fees?|enrolment fees?|enrollment fees?"
    r"|cost of attendance|costs? of study|fees? and (?:funding|costs?)"
    r"|tuition and fees?|study costs?|living costs?|statement of fees?"
    r"|fees? overview|what it costs)\b",
    re.IGNORECASE,
)
_DOCUMENTS = re.compile(
    r"\b(required documents|documents you need|document checklist|supporting documents"
    r"|what to submit|upload(?:ing)? documents)\b",
    re.IGNORECASE,
)
#: A page has to say something substantive about an award to be an award page.
_AWARD_SIGNALS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "amount",
        re.compile(
            r"\b(amount|value|worth|covers?|waiver|per year|per month|% of tuition)\b", re.I
        ),
    ),
    (
        "coverage",
        re.compile(
            r"\b(covers?|coverage|includes?|tuition|housing|accommodation|stipend|living costs)\b",
            re.I,
        ),
    ),
    (
        "eligibility",
        re.compile(r"\b(eligib|who can apply|criteria|requirements|open to|restricted to)\b", re.I),
    ),
    (
        "application",
        re.compile(
            r"\b(how to apply|apply for this|nominat|no separate application|separate application)\b",
            re.I,
        ),
    ),
    ("deadline", re.compile(r"\b(deadline|closing date|applications? close|apply by)\b", re.I)),
    (
        "duration",
        re.compile(r"\b(renewable|duration|for the duration|years of study|one-?time)\b", re.I),
    ),
)
_ACADEMIC_YEAR = re.compile(r"\b(20\d{2})\s*[/–—-]\s*(\d{2}|20\d{2})\b")
_LANGUAGE = re.compile(
    r"\b(?:taught|instruction|language of instruction)\b[^.]{0,40}?\b(english|dutch|german|french|finnish|polish)\b"
    r"|\b(english|dutch|german|french|finnish|polish)[- ]taught\b",
    re.IGNORECASE,
)
#: Programme fact tables often use just "Language / German" or
#: "Language: Polish", rather than the prose phrase "taught in".
_LANGUAGE_LABEL = re.compile(
    r"^[ \t]*(?:teaching language|language(?: of instruction)?)"
    r"[ \t]*:?[ \t]*(?:\n[ \t]*)*(english|dutch|german|french|finnish|polish)[ \t]*$",
    re.I | re.M,
)

#: URL path fragments that are strong evidence on their own.
_PATH_HINTS: tuple[tuple[re.Pattern[str], PageType], ...] = (
    (re.compile(r"/(news|nieuws|actueel|press)/"), PageType.NEWS),
    (re.compile(r"(careers?|vacanc|jobs?|werken-bij)\."), PageType.IRRELEVANT),
    (re.compile(r"/(vacature|vacancies|jobs|careers)/"), PageType.IRRELEVANT),
)


#: Wrappers that hold the page's own content rather than the site's furniture.
_MAIN_SELECTORS = ("main", "[role=main]", "#main-content", "#main", "#content", "article")
#: Site chrome. Present on every page, so counting its links made an award page
#: look like an index and an admissions page look like a catalogue.
_CHROME_TAGS = ("nav", "header", "footer", "aside")
_CHROME_HINT = re.compile(
    r"nav|menu|breadcrumb|header|footer|sidebar|skip|cookie|banner|social|share|toolbar",
    re.IGNORECASE,
)


def _parse_markup(markup: str) -> BeautifulSoup | None:
    """Parse hostile/mislabeled input without violating ``classify_page``'s
    never-raises contract.

    Fetchers can legitimately return a PDF for a catalogue link. Its decoded
    bytes are not HTML and malformed tag-like fragments can crash lxml's
    BeautifulSoup builder. The stdlib parser is a conservative fallback; if
    both reject the input the classifier proceeds with no DOM and returns an
    honest UNKNOWN unless URL/text signals prove something else.
    """
    for parser in ("lxml", "html.parser"):
        try:
            return BeautifulSoup(markup, parser)
        except Exception:
            continue
    return None


#: Class/id tokens that cannot plausibly name a page's own content. Narrower
#: than ``_CHROME_HINT`` on purpose: that one matches "banner" and "menu",
#: which deleted a requirements container whose class was
#: "requirements-banner" and a tab panel whose class was "tabs-nav-panel".
#: For reading, a false deletion costs the fact itself.
_NEVER_CONTENT_HINT = re.compile(
    r"(?:^|[-_ ])(?:cookie|skip|social|share|breadcrumb|toolbar)(?:$|[-_ ])",
    re.IGNORECASE,
)


def content_for_reading(soup: BeautifulSoup) -> BeautifulSoup:
    """The page's content for **extraction**, not for classification.

    ``main_content`` exists for ``classify_page``, which must not count the
    site's menu as the page's own links. It therefore deletes ``form``,
    ``aside`` and anything whose class or id looks like chrome — and a
    requirement is very often inside exactly those. A live page with the IELTS
    line in a ``<form>``, the deadline in an ``<aside class="key-facts">`` and
    the GPA in a ``<div class="requirements-banner">`` reached the extractors
    as the single sentence "The programme lasts three years."

    So reading keeps what classification throws away: forms, asides, and any
    container whose class merely *mentions* a chrome word. It still drops what
    is never content, and still prefers a ``<main>`` region when the page
    offers one.
    """
    working = _parse_markup(str(soup))
    if working is None:
        return soup
    for tag in working(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    for selector in _MAIN_SELECTORS:
        found = working.select_one(selector)
        if found is not None and len(found.get_text(strip=True)) > 200:
            _drop_bulky_chrome(found)
            return found

    _drop_bulky_chrome(working)
    for attribute in ("class", "id"):
        for tag in working.find_all(attrs={attribute: _NEVER_CONTENT_HINT}):
            tag.decompose()
    return working


def _drop_bulky_chrome(node) -> None:
    """Remove nav/header/footer only when they are big enough to be the site's.

    A short ``<nav>`` is often a within-page tab strip, and a deadline lives in
    a sidebar often enough that deleting every aside costs real facts. The 800
    character threshold is the one ``html_to_text`` already uses.
    """
    for tag in node(["nav", "header", "footer"]):
        if len(tag.get_text(strip=True)) > 800:
            tag.decompose()


def main_content(soup: BeautifulSoup) -> BeautifulSoup:
    """The page's own content, with the site's navigation removed.

    Every page on a university site carries the same global menu. Reading the
    first <h1> or counting links across the whole document therefore measured
    the site, not the page: a single award page linked to six other awards from
    its menu and was classified as an index.
    """
    working = _parse_markup(str(soup))
    if working is None:
        return soup
    for tag in working(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()

    for selector in _MAIN_SELECTORS:
        found = working.select_one(selector)
        if found is not None and len(found.get_text(strip=True)) > 200:
            for tag in found(_CHROME_TAGS):
                tag.decompose()
            return found

    for tag in working(_CHROME_TAGS):
        tag.decompose()
    for tag in working.find_all(attrs={"class": _CHROME_HINT}):
        tag.decompose()
    for tag in working.find_all(attrs={"id": _CHROME_HINT}):
        tag.decompose()
    return working


#: What a URL alone can say about a page. Weaker than reading the page, and
#: that is the point: discovery has to rank candidates *before* fetching them,
#: and a URL that announces a research output or a news item is worth ranking
#: below one that announces a programme. Nothing here rejects a candidate —
#: rejections need evidence, and these are hints.
_URL_ONLY_HINTS: tuple[tuple[re.Pattern[str], PageType], ...] = (
    *_PATH_HINTS,
    # Research outputs. Aalto's top search result was a publication page and
    # KAIST's an organisation profile; both outranked the actual programme.
    (
        re.compile(
            r"/(publications?|research-?outputs?|organisations?|organizations?|persons?"
            r"|profiles?|datasets?|projects?|patents?|theses|dissertations?)(/|$)",
            re.IGNORECASE,
        ),
        PageType.IRRELEVANT,
    ),
    (re.compile(r"^(pure|research|scholar|repository)\.", re.IGNORECASE), PageType.IRRELEVANT),
)
#: LX-1 only (``LEXICON_V2``): publication paths in Spanish, Dutch and
#: Norwegian, and KU Leuven's ``lirias.`` repository host. PUC's false
#: positive was ``ing.uc.cl/publicaciones/…``.
LEXICON_V2_PUBLICATION_PATH = r"publicaciones|publicacion|publicaties|publikasjoner"
_LEXICON_V2_URL_HINTS: tuple[tuple[re.Pattern[str], PageType], ...] = (
    (
        re.compile(rf"/({LEXICON_V2_PUBLICATION_PATH})(/|$)", re.IGNORECASE),
        PageType.IRRELEVANT,
    ),
    (re.compile(r"^lirias\.", re.IGNORECASE), PageType.IRRELEVANT),
)

# Deliberately **only negative**. A "/programmes/" segment was tried as a
# positive hint and measurably hurt: it promotes catalogue index pages over
# the specific programme page that was asked for, and cost Warsaw its place
# entirely while pushing NTU down four. A URL can say reliably what a page is
# *not*; what it *is* needs the page.


def classify_url(url: str) -> PageType:
    """What the URL alone suggests this page is. ``UNKNOWN`` when it says nothing.

    Separate from :func:`classify_page`, which reads the page and is the
    authority. This exists because ranking happens before fetching, and the
    alternative — a second copy of these patterns inside the retrieval code —
    would drift from this one.
    """
    parts = urlparse(url)
    haystack = f"{parts.hostname or ''}{parts.path or ''}"
    for pattern, page_type in _URL_ONLY_HINTS:
        if pattern.search(haystack):
            return page_type
    if LEXICON_V2:
        for pattern, page_type in _LEXICON_V2_URL_HINTS:
            if pattern.search(haystack):
                return page_type
    return PageType.UNKNOWN


def classify_page(*, url: str, html: str = "", text: str = "") -> PageClassification:
    """Classify a fetched page. Never raises; unknown is a valid answer."""
    full = _parse_markup(html) if html else None
    soup = main_content(full) if full is not None else None
    title = _title(full) if full is not None else ""
    headings = _headings(soup) if soup else []
    identity = _identity(soup, title)  # from the content region, not the menu
    body = text or (_text(soup) if soup else "")
    head = " ".join([title, *headings])
    low_head = head.lower()
    low_body = body.lower()
    path = urlparse(url).path.lower()
    host = urlparse(url).netloc.lower()
    # R1: words such as "licence" are degree words only under the page's own language.
    lang = page_language(html) if LOCALIZED_PAGE_IDENTITY else ""
    signals: list[str] = []

    for pattern, page_type in _PATH_HINTS:
        if pattern.search(host) or pattern.search(path):
            return PageClassification(page_type, 0.85, [f"url matches {pattern.pattern}"], title)

    # --- clearly not about studying here --------------------------------
    if _IRRELEVANT.search(low_head):
        return PageClassification(PageType.IRRELEVANT, 0.8, ["title is off-topic"], title)

    # An audience qualification is not a degree the continuing course offers.
    course_identity = f"{identity} {title} {path.replace('-', ' ')}"
    if re.search(r"\bcourses?\s+(?:for\s+)?(?:teachers?|professionals?)\b", course_identity, re.I):
        return PageClassification(
            PageType.IRRELEVANT, 0.9, ["continuing course for a professional audience"], title
        )
    if re.search(
        r"\btopic courses?\b|\bcourse (?:descriptions?|syllabus)\b", course_identity, re.I
    ):
        return PageClassification(
            PageType.IRRELEVANT, 0.9, ["individual course content, not a degree programme"], title
        )

    # The page's own title and first heading only: a "News" block in the
    # sidebar is not the page. Run 31: Vienna's admission-procedure page and
    # HKU's admissions home were both rejected as news on a secondary h2.
    if _NEWS.search(" ".join([title, *headings[:1]]).lower()):
        return PageClassification(PageType.NEWS, 0.75, ["news markers in the title"], title)

    # --- a research output --------------------------------------------------
    # The URL alone only ranks (see _URL_ONLY_HINTS); with the page agreeing
    # it rejects. Run 23: Aalto's programme claim was a paper titled
    # "Arguments for and Approaches to Computing Education in Undergraduate
    # Computer Science Programmes", whose field words read as a programme.
    if classify_url(url) is PageType.IRRELEVANT:
        research = {m.group(1).lower() for m in _RESEARCH_OUTPUT.finditer(low_body[:6000])}
        if len(research) >= 2:
            return PageClassification(
                PageType.IRRELEVANT,
                0.8,
                [f"research-output url and content ({', '.join(sorted(research))})"],
                title,
            )

    # --- mostly links and little prose ----------------------------------
    if soup is not None and body and len(body) < 1500:
        link_text = sum(len(a.get_text(strip=True)) for a in soup.find_all("a"))
        if link_text / max(len(body), 1) > 0.75:
            signals.append("page is mostly link text")
            return PageClassification(PageType.NAVIGATION, 0.6, signals, title)

    # --- cost pages --------------------------------------------------------
    if _COSTS.search(identity) or _COSTS.search(title.lower()):
        return PageClassification(
            PageType.COSTS,
            0.8,
            ["cost vocabulary in the page heading"],
            title,
            academic_year=_academic_year(body),
        )

    # --- funding family ---------------------------------------------------
    # FI-1 (and LX-1): the page's own identity and title, each on its own, as
    # CL-1 does for catalogue words. Auckland's "Undergraduate study in Computer
    # Science" has an h2 "Scholarships and awards" and is not a funding page.
    funding_heading = (
        bool(_SCHOLARSHIP_WORD.search(identity) or _SCHOLARSHIP_WORD.search(title))
        if FUNDING_IDENTITY_SCOPE or LEXICON_V2
        else bool(_SCHOLARSHIP_WORD.search(low_head))
    )
    if funding_heading or "scholarship" in path or "financial-aid" in path:
        if _FAQ.search(low_head):
            return PageClassification(PageType.SCHOLARSHIP_FAQ, 0.9, ["FAQ markers"], title)

        award_links = _award_link_count(soup) if soup else 0
        present = [name for name, pattern in _AWARD_SIGNALS if pattern.search(low_body)]
        named = _award_name(identity)
        plural_index = bool(
            _PLURAL_FUNDING_HEADING.match(identity)
            or re.search(
                r"\b(overview of|list of|available) (scholarships|funding|grants)\b", low_body
            )
        )

        # AP-1: a page whose own heading is a proper award name and that files
        # no awards below its own path is that award, however many sibling or
        # hub links it carries (Imperial Inspires: its hub and the fees page).
        if (
            AWARD_PAGE_EVIDENCE
            and named
            and not plural_index
            and len(present) >= 2
            and proper_award_name(identity)
            and _award_links_below(soup, url) < _CHILD_AWARDS_FOR_INDEX
        ):
            return PageClassification(
                PageType.SCHOLARSHIP_AWARD,
                0.75 + 0.05 * min(len(present), 4),
                [
                    f"named award {named!r}",
                    f"signals: {', '.join(present)}",
                    f"{award_links} award links, fewer than {_CHILD_AWARDS_FOR_INDEX} below it",
                ],
                title,
                subject=named,
                degree_level=_degree_level(f"{head} {body[:2500]}", lang),
                academic_year=_academic_year(body),
            )
        # A listing heading, or several links out to named awards, or links out
        # with no award identity of its own.
        if plural_index or award_links >= 2 or (award_links >= 1 and named is None):
            signals += [
                f"{award_links} award links",
                "listing heading" if plural_index else "",
                "no award identity of its own" if named is None else "",
            ]
            return PageClassification(
                PageType.SCHOLARSHIP_INDEX, 0.8, [s for s in signals if s], title
            )
        # A named award plus at least two substantive signals.
        if named and len(present) >= 2:
            return PageClassification(
                PageType.SCHOLARSHIP_AWARD,
                0.75 + 0.05 * min(len(present), 4),
                [f"named award {named!r}", f"signals: {', '.join(present)}"],
                title,
                subject=named,
                degree_level=_degree_level(f"{head} {body[:2500]}", lang),
                academic_year=_academic_year(body),
            )
        return PageClassification(
            PageType.UNKNOWN,
            0.3,
            [f"funding page with {len(present)} substantive signals and no clear award name"],
            title,
        )

    if _DOCUMENTS.search(low_head):
        return PageClassification(PageType.DOCUMENTS, 0.7, ["document checklist heading"], title)

    # --- programme family --------------------------------------------------
    program_links = _program_link_count(soup) if soup else 0
    # A heading that is plural or catalogue-shaped settles it: that is the page
    # saying what it is.
    catalogue_heading = (
        bool(_CATALOG.search(identity) or _CATALOG.search(title))
        if CATALOG_HEADING_SCOPE
        else bool(_CATALOG.search(low_head))
    )
    if _PLURAL_PROGRAM_HEADING.match(identity) or catalogue_heading:
        return PageClassification(
            PageType.PROGRAM_CATALOG,
            0.75,
            [f"{program_links} programme links", "plural catalogue heading"],
            title,
        )

    # A programme page is identified before the admissions rules run: a real
    # programme page has an "entry requirements" section, and matching that
    # first classified BSc Computer Science and Engineering as a general
    # admissions page.
    subject = _program_name(identity, lang)
    context_degree: str | None = None
    if subject is None:
        from_context = _program_name_from_context(identity, title, path, body[:4000], lang)
        if from_context:
            subject, context_degree = from_context

    # Links alone may only decide when the page has no programme identity of
    # its own. Counting them first made "BSc Computing Science" a catalogue
    # because it linked to five other programmes — every real programme page
    # does — and the allow-list then refused every extractor. In live run
    # 35754594232 that is exactly what happened to Groningen's certified
    # source page, and to Delft's and Toronto's. The funding branch above
    # already carries this rule: a page with links out and "no award identity
    # of its own" is an index, and one that names its award is not.
    if subject is None and program_links >= 5:
        return PageClassification(
            PageType.PROGRAM_CATALOG,
            0.7,
            [f"{program_links} programme links", "no programme identity of its own"],
            title,
        )
    degree = context_degree or _degree_level(f"{identity} {body[:2500]}", lang)
    language_body = _text(soup) if soup is not None else body
    language = (
        _language(language_body) if _LANGUAGE_LABEL.search(language_body) else _prose_language(body)
    )
    language_evidence = _labelled_language_evidence(language_body, subject, language)
    year = _academic_year(body)

    if not subject:
        if _CREDENTIAL.search(low_head) and _ADMISSIONS.search(low_head):
            return PageClassification(
                PageType.COUNTRY_CREDENTIAL_REQUIREMENTS,
                0.75,
                ["admissions page scoped to a diploma type"],
                title,
            )
        if _ADMISSIONS.search(low_head):
            return PageClassification(
                PageType.GENERAL_ADMISSIONS,
                0.8,
                ["admissions phrasing without a single programme identity"],
                title,
            )

    if subject and degree and PROGRAMME_PAGE_GUARD:
        guarded = (
            "research-output url"
            if classify_url(url) is PageType.IRRELEVANT
            else "host root"
            if is_host_root(url, html)
            else None
        )
        structure = programme_structure_signals(body) if guarded else []
        if guarded and len(structure) < PROGRAMME_STRUCTURE_MIN:
            return PageClassification(
                PageType.UNKNOWN,
                0.3,
                [
                    f"{guarded} names {subject!r} but the page shows "
                    f"{len(structure)} programme-structure signal(s)"
                ],
                title,
            )

    if subject and degree:
        signals.append(f"single programme {subject!r} at {degree} level")
        if language:
            signals.append(f"language of instruction: {language}")
        if year:
            signals.append(f"academic year {year}")
            return PageClassification(
                PageType.INTAKE_SPECIFIC_PROGRAM,
                0.85,
                signals,
                title,
                subject=subject,
                degree_level=degree,
                language_of_instruction=language,
                academic_year=year,
                language_evidence=language_evidence,
            )
        return PageClassification(
            PageType.PROGRAM_DETAIL,
            0.75,
            signals,
            title,
            subject=subject,
            degree_level=degree,
            language_of_instruction=language,
            language_evidence=language_evidence,
        )

    if _CREDENTIAL.search(low_head) and _ADMISSIONS.search(low_head):
        return PageClassification(
            PageType.COUNTRY_CREDENTIAL_REQUIREMENTS,
            0.7,
            ["admissions page scoped to a diploma type"],
            title,
        )
    if _ADMISSIONS.search(low_head):
        return PageClassification(PageType.GENERAL_ADMISSIONS, 0.7, ["admissions phrasing"], title)
    cost_mentions = len(_COSTS.findall(low_body))
    if cost_mentions >= 2:
        return PageClassification(
            PageType.COSTS,
            0.6,
            [f"{cost_mentions} cost phrases in the body"],
            title,
            academic_year=_academic_year(body),
        )

    if _CREDENTIAL.search(low_body[:2000]):
        return PageClassification(
            PageType.COUNTRY_CREDENTIAL_REQUIREMENTS, 0.55, ["credential vocabulary"], title
        )

    return PageClassification(PageType.UNKNOWN, 0.2, ["no decisive signals"], title)


# --- helpers ---------------------------------------------------------------


def _title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return " ".join(soup.title.string.split())[:200]
    h1 = soup.find("h1")
    return " ".join(h1.get_text(" ", strip=True).split())[:200] if h1 else ""


def _headings(soup: BeautifulSoup) -> list[str]:
    return [" ".join(h.get_text(" ", strip=True).split()) for h in soup.find_all(["h1", "h2"])][:12]


def _text(soup: BeautifulSoup) -> str:
    # ``soup`` is already parsed and stripped by ``main_content``. Re-parsing
    # its serialization with lxml reintroduced the exact malformed-attribute
    # crash that the safe parser above recovered from.
    text = soup.get_text("\n")
    text = re.sub(r"[ \t ]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _r1_degree_words(lang: str = "") -> tuple[tuple[str, str], ...]:
    """R1's degree-word table for a page in ``lang``, whether or not R1 is on."""
    primary = (lang or "").strip().lower().split("-")[0]
    localized = tuple(
        (pattern, level)
        for pattern, level, languages in _LOCALIZED_DEGREE_WORDS
        if languages is None or primary in languages
    )
    return (*_DEGREE_WORDS, *_LEXICON_V2_DEGREE_WORDS, *localized)


def _degree_words(lang: str = "") -> tuple[tuple[str, str], ...]:
    """The degree-word table in force, for a page in ``lang`` (R1 gates on it)."""
    if LOCALIZED_PAGE_IDENTITY:
        return _r1_degree_words(lang)
    if LEXICON_V2:
        return (*_DEGREE_WORDS, *_LEXICON_V2_DEGREE_WORDS)
    return _DEGREE_WORDS


def local_bachelor_word(language: str) -> str | None:
    """R5: how a query in ``language`` names a bachelor's, or ``None``.

    The word is :data:`_LOCAL_BACHELOR_QUERY_WORDS`'s, returned only when R1's
    table reads it as a bachelor's — and as no other level — on a page in that
    language. ``language`` is an institution's (``languages.json``), never the
    applicant's.
    """
    primary = (language or "").strip().lower().split("-")[0]
    word = _LOCAL_BACHELOR_QUERY_WORDS.get(primary)
    if not word:
        return None
    levels = {
        level for pattern, level in _r1_degree_words(primary) if re.search(pattern, word.lower())
    }
    return word if levels == {"bachelor"} else None


def localized_alias_flags() -> frozenset[str]:
    """The ontology flags whose localized aliases discovery's identity accepts.

    LI-1's own entries always; LX-1's while ``LEXICON_V2`` is on; LX-1's and
    R1's while ``LOCALIZED_PAGE_IDENTITY`` is on (16-Q4). Read at call time, so
    a flag flipped per capture is honoured. Discovery's confirm step and R5's
    query family read the same set, so a query never names an alias the
    confirm would refuse.
    """
    flags = {"LOCALIZED_IDENTITY"}
    if LEXICON_V2:
        flags.add("LEXICON_V2")
    if LOCALIZED_PAGE_IDENTITY:
        flags.update({"LEXICON_V2", "LOCALIZED_PAGE_IDENTITY"})
    return frozenset(flags)


def page_language(html: str) -> str:
    """The primary language subtag a page's ``<html lang>`` declares, or ``""``."""
    found = _HTML_LANG.search((html or "")[:200_000])
    return found.group(1).lower() if found else ""


def _degree_level(text: str, lang: str = "") -> str | None:
    """The degree the text names first.

    First by position, not by the order of ``_DEGREE_WORDS``: that order made
    any "master" anywhere in the body outrank the "BSc" in the heading, and
    HKU's undergraduate page came out as a master's programme. On a tie the
    word listed first wins (R1 lists every master's word before the bachelor's).
    """
    low = text.lower()
    earliest: tuple[int, str] | None = None
    for pattern, level in _degree_words(lang):
        match = re.search(pattern, low)
        if match and (earliest is None or match.start() < earliest[0]):
            earliest = (match.start(), level)
    return earliest[1] if earliest else None


def _language(text: str) -> str | None:
    labelled = {m.group(1).lower() for m in _LANGUAGE_LABEL.finditer(text)}
    if labelled:
        return next(iter(labelled)) if len(labelled) == 1 else None
    return _prose_language(text)


def _prose_language(text: str) -> str | None:
    m = _LANGUAGE.search(text)
    if not m:
        return None
    return (m.group(1) or m.group(2) or "").lower() or None


def _labelled_language_evidence(text: str, subject: str | None, language: str | None) -> str | None:
    """Keep a contiguous programme title and explicit language field together.

    Only the main content reaches this helper. A navigation label with the
    same value must not become the shorter apparent proof. The claim reader
    subsequently applies its excerpt cap without truncating this evidence.
    """
    labels = list(_LANGUAGE_LABEL.finditer(text))
    if not labels or language is None:
        return None
    if not subject:
        return ""
    title_pattern = re.compile(r"\s+".join(re.escape(word) for word in subject.split()), re.I)
    titles = list(title_pattern.finditer(text))
    if not titles:
        return ""
    starts = [match.start() for match in titles]
    best: tuple[int, int] | None = None
    for label in labels:
        if label.group(1).lower() != language:
            continue
        index = bisect_left(starts, label.start())
        for nearby in (index - 1, index):
            if 0 <= nearby < len(titles):
                title = titles[nearby]
                span = (min(title.start(), label.start()), max(title.end(), label.end()))
                if best is None or span[1] - span[0] < best[1] - best[0]:
                    best = span
    return text[best[0] : best[1]].strip() if best else ""


def _academic_year(text: str) -> str | None:
    m = _ACADEMIC_YEAR.search(text)
    if not m:
        return None
    end = m.group(2)
    return f"{m.group(1)}/{end[-2:]}"


def _identity(soup: BeautifulSoup | None, title: str) -> str:
    """What the page says it is about: its h1, else the title before the site suffix."""
    if soup is not None:
        h1 = soup.find("h1")
        if h1:
            return " ".join(h1.get_text(" ", strip=True).split())
    return title.split("|")[0].strip()


#: Headings that contain a degree word and are still not a programme. Every
#: entry is a title a live run actually read and claimed a programme from:
#: Groningen's "Bachelor's Open Day" and Delft's "Preparing for a bachelor"
#: became `programme.exists` claims, and the benchmark scored them as wrong
#: -scope claims about Computing Science and Computer Science and Engineering.
#: A degree word in a heading says the page is *about* degrees, not that the
#: page *is* one.
_NOT_A_PROGRAMME_HEADING = re.compile(
    r"\b(open|information|info|orientation|taster|experience)\s+(day|days|evening|session|week)\b"
    r"|\b(webinar|fair|expo|roadshow|campus\s+tour)\b"
    r"|\b(preparing|prepare|getting\s+ready)\s+for\b"
    r"|\bmeet\s+(us|the)\b",
    re.IGNORECASE,
)


def _program_name(identity: str, lang: str = "") -> str | None:
    """The programme a page is about, if it is about exactly one."""
    name = identity
    if not name or len(name) > 120:
        return None
    if _PLURAL_PROGRAM_HEADING.match(name):
        return None
    if _NOT_A_PROGRAMME_HEADING.search(name):
        return None
    if not _degree_level(name, lang):
        return None
    # A heading that is a question or an instruction is not a programme name.
    if name.endswith("?") or re.match(r"^(check|how|what|apply|find|browse|search)\b", name, re.I):
        return None
    return name


def _program_name_from_context(
    identity: str, title: str, path: str, body: str = "", lang: str = ""
) -> tuple[str, str] | None:
    """A bare subject heading ("Computing Science") that the page's own title
    and address place at one degree level, and the degree they place it at.

    Groningen's certified programme page carries its degree only in the title
    and in ``/bachelors/``; the heading alone failed ``_program_name`` and the
    page's links then made it a catalogue, which the allow-list refuses. All
    must agree: a short single name, repeated in the title, with a degree word
    in the title or the path — and no full degree title in the body naming a
    different subject. HKU's "Computing and Data Science" is a school whose
    page says "The Bachelor of Engineering in Computer Science covers …": its
    heading is an area, and naming it a programme recorded a false one.
    """
    name = (identity or "").strip()
    if not name or len(name) > 80 or len(name.split()) > 6:
        return None
    if _PLURAL_PROGRAM_HEADING.match(name) or _NOT_A_PROGRAMME_HEADING.search(name):
        return None
    if name.endswith("?") or re.match(r"^(check|how|what|apply|find|browse|search)\b", name, re.I):
        return None
    if name.casefold() not in (title or "").casefold():
        return None
    segments = " ".join(re.split(r"[/_-]+", path or ""))
    degree = _degree_level(title or "", lang) or _degree_level(segments, lang)
    if not degree:
        return None
    for match in _FULL_DEGREE_TITLE.finditer(body or ""):
        if name.casefold() not in match.group(0).casefold():
            return None
    return name, degree


#: "Bachelor of Engineering in Computer Science", "BSc in Data Science",
#: "Master of Science in Computing": a degree named in full, with its subject.
_FULL_DEGREE_TITLE = re.compile(
    # The degree word in any case; the subject only in capitals, so "bachelor
    # in the Netherlands" or "taught in English" never reads as a programme.
    r"(?i:\b(?:bachelor|master|b\.?sc|m\.?sc|b\.?eng|m\.?eng)\b)"
    r"(?:\s+of\s+[A-Z]\w*(?:\s+[A-Z]\w*)?)?(?:\s*\((?i:hons)\))?"
    r"(?:\s+in\s+(?!English\b|Dutch\b|German\b|French\b)[A-Z][\w&]*(?:\s+(?:and\s+)?[A-Z][\w&]*){0,3}"
    # "Bachelor of Engineering (Computer Science)", the other way a programme
    # list writes the subject.
    r"|(?<=[a-z])\s+\((?!(?i:hons)\))[A-Z][\w&]*(?:\s+(?:and\s+)?[A-Z][\w&]*){0,3}\))"
)


def _award_name(identity: str) -> str | None:
    name = identity
    if not name or len(name) > 160:
        return None
    if name.endswith("?") or _FAQ.search(name):
        return None
    # A plural category heading is an index, not an award.
    if _PLURAL_FUNDING_HEADING.match(name) or re.fullmatch(
        r"(admission services|menu.*|search.*)", name.strip(), re.IGNORECASE
    ):
        return None
    if not _SCHOLARSHIP_WORD.search(name) and not re.search(
        r"\b(award|prize|fund|fellowship)\b", name, re.I
    ):
        return None
    return name


#: AP-1: the award noun a proper award name ends in, capitalised as a name is.
_AWARD_NOUN = r"(?:Scholarships?|Awards?|Bursar(?:y|ies)|Grants?)"
_PROPER_AWARD_NAME = re.compile(rf"(?P<lead>\S(?:.*?\S)?)\s+{_AWARD_NOUN}(?:\s*\([^()]{{1,40}}\))?")
#: AP-1: "1." / "2)" before a name in a numbered list of awards.
_LIST_NUMBER = re.compile(r"^\s*\d{1,2}\s*[.)]\s*")
#: AP-1: words a proper name may carry in lower case.
_NAME_LINK_WORDS = frozenset(
    {"of", "for", "a", "an", "the", "and", "in", "to", "at", "on", "with", "&", "de", "la"}
)
#: AP-1: words that describe a category of awards, not one award.
_GENERIC_AWARD_WORDS = frozenset(
    {
        "university",
        "international",
        "undergraduate",
        "postgraduate",
        "graduate",
        "entrance",
        "merit",
        "merit-based",
        "need-based",
        "academic",
        "student",
        "students",
        "general",
        "first-year",
        "first",
        "year",
        "freshman",
        "freshmen",
        "incoming",
        "ug",
        "pg",
        "bachelor",
        "bachelor's",
        "master",
        "master's",
        "doctoral",
        "phd",
        "research",
    }
)
#: AP-1: a heading that starts like this is about awards, not one award.
_NOT_A_NAME_START = frozenset(
    {
        "about",
        "apply",
        "applying",
        "how",
        "what",
        "why",
        "when",
        "where",
        "which",
        "who",
        "find",
        "search",
        "browse",
        "our",
        "your",
        "other",
        "more",
        "list",
        "overview",
        "all",
        "available",
        "external",
    }
)


def proper_award_name(text: str) -> str | None:
    """AP-1: ``text`` as one award's proper name, or None.

    A proper name ends in a capitalised award noun (an optional parenthesis
    after it), every word before it is capitalised or a linking word, and at
    least one of them is not a category word. "International Major Entrance
    Scholarship" and "Imperial Inspires Scholarships (Undergraduate)" are
    names; "UNSW scholarships for international students", "Scholarship
    Application Form" and "Merit-based awards" are not. A leading list number
    ("1.School of ... Scholarship") is dropped.
    """
    name = " ".join(_LIST_NUMBER.sub("", (text or "").replace("\xa0", " "), count=1).split())
    name = name.strip(" :;,–—-")
    if not name or len(name) > 120 or name.endswith("?") or _FAQ.search(name):
        return None
    match = _PROPER_AWARD_NAME.fullmatch(name)
    if match is None:
        return None
    words = match.group("lead").split()
    if len(words) > 12 or words[0].casefold() in _NOT_A_NAME_START:
        return None
    distinctive = False
    for word in words:
        bare = word.strip("()'’\",.:;")
        if not bare or bare.casefold() in _NAME_LINK_WORDS:
            continue
        if not (bare[0].isupper() or bare[0].isdigit()):
            return None
        distinctive = distinctive or bare.casefold() not in _GENERIC_AWARD_WORDS
    return name if distinctive else None


#: AP-1: as many award links below its own path make a page a list of awards
#: (``web_scholarships._CHILD_AWARDS_FOR_INDEX``).
_CHILD_AWARDS_FOR_INDEX = 3
_AWARD_LINK_HINT = re.compile(r"scholarship|award|bursar|grant|fellowship|funding", re.I)


def _award_links_below(soup: BeautifulSoup | None, url: str) -> int:
    """AP-1: distinct award links in the content filed beneath the page's own path."""
    if soup is None:
        return 0
    own = re.sub(r"(/index)?\.(?:html?|php|aspx?)$", "", urlparse(url).path.rstrip("/").lower())
    own += "/"
    host = urlparse(url).netloc.lower()
    below: set[str] = set()
    for a in soup.find_all("a", href=True):
        target = urlparse(urljoin(url, a["href"].strip()))
        path = target.path.lower()
        if (
            target.netloc.lower() != host
            or not path.startswith(own)
            or path.rstrip("/") + "/" == own
        ):
            continue
        if _AWARD_LINK_HINT.search(f"{a.get_text(' ', strip=True)} {path}"):
            below.add(path.rstrip("/"))
    return len(below)


def _award_link_count(soup: BeautifulSoup | None) -> int:
    if soup is None:
        return 0
    # A breadcrumb/category link and a detail link often name the same award.
    # Multiple links prove an index only when they name different awards.
    return len(
        {
            re.sub(r"\s+", " ", a.get_text(" ", strip=True)).casefold()
            for a in soup.find_all("a", href=True)
            if _SCHOLARSHIP_WORD.search(a.get_text(" ", strip=True) or "")
            and not _FAQ.search(a.get_text(" ", strip=True) or "")
        }
    )


def _program_link_count(soup: BeautifulSoup | None) -> int:
    if soup is None:
        return 0
    return sum(
        1
        for a in soup.find_all("a", href=True)
        if re.search(
            r"/(bsc|msc|ba|ma|bachelor|master|programme|program|course)s?/", a.get("href", ""), re.I
        )
    )


def full_degree_titles(text: str) -> list[str]:
    """Every degree a text names in full, with its subject, in order.

    "The Bachelor of Engineering in Computer Science covers …" yields
    "Bachelor of Engineering in Computer Science". Public for the one caller
    that may use a listing page's named programmes as evidence of existence.
    """
    # "Bachelor of Engineering (Computer Science)" is returned in the "in"
    # form, the one the programme ontology reads.
    return [
        re.sub(r"\s*\(([^()]+)\)$", r" in \1", m.group(0).strip())
        if not m.group(0).strip().lower().endswith("(hons)")
        else m.group(0).strip()
        for m in _FULL_DEGREE_TITLE.finditer(text or "")
    ]


def degree_level_of(text: str) -> str | None:
    """The degree a text names first; see ``_degree_level``."""
    return _degree_level(text or "")
