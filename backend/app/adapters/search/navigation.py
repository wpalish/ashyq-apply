"""One hop through a site's own navigation, for pages a search index cannot see.

KAIST's computer science programme lives at ``cs.kaist.ac.kr/content?menu=188``.
No query shape reaches it — not English, not Korean, not restricted to the
subdomain — because there is not one word in that URL to match. The department
root, however, comes back first or second in almost every query, and the target
is linked directly from its navigation.

That is the general shape, not a KAIST quirk. A search index finds what is
linkable and word-bearing, so it reliably finds *entry points*. Structural
traversal does not care about words in a URL. The two fail differently, which
is why fusion has several generators, and why the answer to an opaque site is
one hop rather than better queries.

The link *text* carries the meaning the URL lost. ``matches_field_text`` in
``live_discovery`` was written for the same reason — Toronto's programme sits
at ``/data-computer-science`` behind the words "Data & Computer Science" — and
is reused here rather than reimplemented.

This module reads HTML it is handed. It fetches nothing: the entry point comes
through ``Fetcher`` like every other page.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from lxml import html as lxml_html

from app.adapters.discovery.live_discovery import (
    canonical_url,
    degree_level_named,
    is_excluded_path,
    matches_field_text,
    same_institution,
    scheme_free_identity,
)
from app.adapters.search.fusion import Generator, SourcedCandidate
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.ontology import retrieval_candidates
from app.adapters.url_canonical import page_link

#: Most links to read from one page. A university front page can carry several
#: hundred; past this the page is a directory and the hop is the wrong tool.
MAX_LINKS_PER_PAGE = 400

#: Most candidates one hop may contribute. The hop is a supplement to search,
#: not a crawl, and an unbounded one would drown fusion in navigation chrome.
DEFAULT_HOP_LIMIT = 10

_SPACE = re.compile(r"\s+")

#: A staff or faculty listing is not a programme. ``live_discovery`` already
#: rejects research groups, labs and institutes; people pages belong with them
#: and are rejected here rather than there, because that module's rule is used
#: by the existing pipeline and widening it is a separate change.
_NOT_A_PROGRAMME_LINK = re.compile(
    r"/(people|faculty|staff|directory|professors?|members?|alumni)(/|$)", re.IGNORECASE
)

#: Words that name a study section, in the languages this corpus meets. A
#: navigation label is often the only place the meaning survives, and on a
#: Korean or Finnish site it survives in Korean or Finnish. Verified against
#: the pages they were read from; nothing here is guessed.
_SECTION_WORDS = (
    # English
    "education",
    "study",
    "studies",
    "academics",
    "programme",
    "program",
    "curriculum",
    "undergraduate",
    "bachelor",
    # Korean: 교육 education, 교과과정 curriculum. Note the absence of a bare
    # 학부 ("undergraduate"): CJK has no word boundaries, so as a substring it
    # also matched 학부발전기금 (development fund), 학부장 인사말 (the dean's
    # greeting) and 학부동아리 (student clubs) on KAIST's real navigation.
    "교육",
    "교과과정",
)


#: Plan v3 rule R4 (LC-1, ticket 20 Q1; ``live_discovery.LOCAL_CATALOGUE_ENTRY``):
#: the study section and the programme catalogue named in each language of
#: ``languages.json``, the same two kinds of word for every language — a
#: dictionary translation of "programmes / degree programmes / find a
#: programme" (``_LOCAL_CATALOGUE_WORDS``) and of "study / studies / education"
#: (``_LOCAL_SECTION_WORDS``). The language comes from the institution's
#: country, never from the applicant. Admission words are not here: a
#: "prospective students" section is not the list of programmes (ER-05 keeps
#: its own table). Every entry is general vocabulary, not read off a page.
_LOCAL_CATALOGUE_WORDS: dict[str, tuple[str, ...]] = {
    "es": (
        "carreras",
        "carreras de grado",
        "carreras de pregrado",
        "carreras universitarias",
        "oferta académica",
        "oferta educativa",
        "programas de estudio",
        "programas académicos",
        "grados",
        "titulaciones",
        "estudios de grado",
        "pregrado",
    ),
    "ca": ("graus", "estudis de grau", "oferta acadèmica", "titulacions"),
    "pt": ("cursos", "cursos de graduação", "graduação", "oferta formativa", "licenciaturas"),
    "fr": (
        "formations",
        "nos formations",
        "choisir sa formation",
        "offre de formation",
        "catalogue des formations",
        "trouver une formation",
        "licences",
    ),
    "it": ("corsi di laurea", "corsi di studio", "offerta formativa", "lauree", "corsi"),
    "de": ("studienangebot", "studienangebote", "studiengänge", "studienfächer"),
    "nl": ("opleidingen", "onderwijsaanbod", "opleidingsaanbod", "studieaanbod"),
    "da": ("uddannelser", "bacheloruddannelser", "find uddannelse", "studieretninger"),
    "no": ("studieprogrammer", "studieprogram", "studietilbud", "finn studier", "finn studie"),
    "sv": ("utbildningar", "program och kurser", "utbildningsprogram", "hitta utbildning"),
    "fi": ("koulutukset", "koulutusohjelmat", "hakukohteet"),
    "pl": ("kierunki studiów", "kierunki", "oferta kształcenia", "oferta dydaktyczna"),
    "cs": ("studijní programy", "studijní obory", "nabídka studia"),
    "sk": ("študijné programy", "študijné odbory", "ponuka štúdia"),
    "et": ("õppekavad", "erialad"),
    "lt": ("studijų programos", "programos"),
    "tr": ("bölümler", "programlar", "lisans programları", "akademik programlar"),
    "ru": (
        "образовательные программы",
        "направления подготовки",
        "специальности",
        "программы обучения",
        "бакалавриат",
    ),
    "kk": ("білім беру бағдарламалары", "оқу бағдарламалары", "мамандықтар", "бакалавриат"),
    "ja": ("学部", "学部・大学院", "学部・大学院等", "学部・研究科", "学科"),
    "zh": ("本科专业", "专业设置", "专业介绍", "招生专业", "學系介紹"),
    "ko": ("학과", "학부", "학과안내", "학부과정", "전공"),
    "th": ("หลักสูตร", "หลักสูตรที่เปิดสอน", "คณะ"),
}
#: R4: words that name the study section as a whole. Only a label that *is*
#: one of these counts ("Studier", "Formation"); "Formation en alternance" is
#: not the section, and a headline that contains the word is not a label.
_LOCAL_SECTION_WORDS: dict[str, tuple[str, ...]] = {
    "es": ("estudios", "estudiar", "estudia", "grado"),
    "ca": ("estudis", "estudiar", "grau"),
    "pt": ("ensino", "estudar", "estudos"),
    "fr": ("formation", "études", "étudier"),
    "it": ("didattica", "studiare"),
    "de": ("studium", "studieren", "studium und lehre"),
    "nl": ("onderwijs", "studeren", "opleiding"),
    "da": ("uddannelse", "studier", "studere"),
    "no": ("studier", "studere", "utdanning"),
    "sv": ("utbildning", "studera", "studier"),
    "fi": ("koulutus", "opiskelu", "opiskele"),
    "pl": ("studia", "studiuj", "kształcenie", "dydaktyka"),
    "cs": ("studium", "studovat", "vzdělávání"),
    "sk": ("štúdium", "študovať", "vzdelávanie"),
    "et": ("õppimine", "õpingud", "õppetöö"),
    "lt": ("studijos", "studijuok"),
    "tr": ("akademik", "eğitim", "öğrenim"),
    "ru": ("образование", "обучение", "учёба"),
    "kk": ("білім беру", "оқу", "білім"),
    "ja": ("教育",),
    "zh": ("本科生教育", "本科教育", "大學部", "教育教学", "教學", "教育", "人才培养"),
    "ko": ("교육", "교육과정"),
    "th": ("การศึกษา",),
}
#: R4: languages whose pages declare a variant tag of one table's language.
_LANGUAGE_VARIANTS = {"nb": "no", "nn": "no"}
#: R4: degree levels as words in a section label, every language at once. A
#: label naming only another level is not the applicant's section ("Carreras de
#: Posgrado", "Ph.d.-uddannelse", "研究生教育").
_LEVEL_WORDS: dict[str, tuple[str, ...]] = {
    "bachelor": (
        "pregrado",
        "grado",
        "grau",
        "graduação",
        "licence",
        "licences",
        "laurea triennale",
        "bachelor",
        "bakalářské",
        "bakalárske",
        "бакалавриат",
        "lisans",
        "undergraduate",
        "本科",
        "本科生",
        "学部",
        "학부",
        "ปริญญาตรี",
    ),
    "master": (
        "posgrado",
        "postgrado",
        "máster",
        "master",
        "masters",
        "magíster",
        "magister",
        "maestría",
        "maestrías",
        "mestrado",
        "pós-graduação",
        "laurea magistrale",
        "magistrale",
        "magistratura",
        "магистратура",
        "yüksek lisans",
        "magistrantūra",
        "magistriõpe",
        "graduate",
        "postgraduate",
        "研究生",
        "硕士",
        "碩士",
        "大学院",
        "대학원",
        "ปริญญาโท",
    ),
    "phd": (
        "doctorado",
        "doctorat",
        "dottorato",
        "doutorado",
        "doktorat",
        "аспирантура",
        "докторантура",
        "doktora",
        "doktorantūra",
        "doktoriõpe",
        "ph d",
        "phd",
        "博士",
        "박사",
        "ปริญญาเอก",
    ),
}
#: R4: continuing, lifelong and online education: never a degree's section.
_NOT_A_DEGREE_SECTION: tuple[str, ...] = (
    "formation continue",
    "educación continua",
    "formación continua",
    "formação contínua",
    "efteruddannelse",
    "videreutdanning",
    "weiterbildung",
    "fortbildning",
    "uppdragsutbildning",
    "täydennyskoulutus",
    "继续教育",
    "终身教育",
    "在线教育",
    "평생교육",
    "生涯学習",
)
#: R4: words a section label carries beside its section word without changing
#: what it names: function words, and the icon-font ligatures menus render as
#: text ("Carreras de pregrado launch", "… arrow_forward").
_LABEL_NOISE = frozenset(
    "de del la las los el en y e o a al sa son nos des du le les et l d di della delle dei "
    "il lo gli da do dos das na nas em og och i und der die van het een ve ile ir w z ze u "
    "и в на launch arrow forward chevron right left expand more open new keyboard down "
    "north east navigate next".split()
)
#: R4: catalogue words a catalogue label may carry one more word beside (the
#: institution's short name, "Onderwijsaanbod 2026 - 2027" after its years);
#: a section word must be the whole label.
LOCAL_CATALOGUE_TIER = 0
LOCAL_SECTION_TIER = 1
_UNSPACED = re.compile("[฀-๿ᄀ-ᇿ぀-ヿ㄰-㆏㐀-䶿一-鿿가-힯豈-﫿]")
_FOLD_LETTERS = str.maketrans({"ı": "i", "ł": "l", "ø": "o", "đ": "d"})


def _fold_label(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold().translate(_FOLD_LETTERS))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _label_tokens(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", _fold_label(text))


def _unspaced(text: str) -> str:
    return re.sub(r"[\s\d\-–—:|/,.]+", "", _fold_label(text))


def _contains(tokens: list[str], phrase: list[str]) -> int:
    """Where ``phrase`` starts in ``tokens`` as a run of whole words; -1 if not."""
    width = len(phrase)
    for start in range(len(tokens) - width + 1):
        if tokens[start : start + width] == phrase:
            return start
    return -1


def _without(text: str, words: Sequence[str]) -> str | list[str]:
    """The label with every occurrence of ``words`` taken out (squeezed or as tokens)."""
    if _UNSPACED.search(text):
        squeezed = _unspaced(text)
        for word in sorted(words, key=len, reverse=True):
            if _UNSPACED.search(word):
                squeezed = squeezed.replace(_unspaced(word), " ")
        return squeezed
    tokens: list[str] = _label_tokens(text)
    for word in sorted(words, key=len, reverse=True):
        phrase = _label_tokens(word)
        while phrase and (at := _contains(tokens, phrase)) >= 0:
            tokens[at : at + len(phrase)] = [""]
    return tokens


def _names_any(text: str | list[str], words: Sequence[str]) -> bool:
    if isinstance(text, str) and _UNSPACED.search(text):
        squeezed = _unspaced(text)
        return any(_unspaced(word) in squeezed for word in words if _UNSPACED.search(word))
    tokens = text if isinstance(text, list) else _label_tokens(text)
    return any(_contains(tokens, _label_tokens(word)) >= 0 for word in words)


def label_fits_degree(text: str, degree: str) -> bool:
    """R4: whether a label (or a host name) may name the section for ``degree``.

    False for continuing or online education, and for a label naming another
    degree level without naming ``degree`` ("Carreras de Posgrado" for a
    bachelor's applicant); a label naming no level says nothing and passes.
    """
    if _names_any(text, _NOT_A_DEGREE_SECTION):
        return False
    others = [word for level, words in _LEVEL_WORDS.items() if level != degree for word in words]
    if not _names_any(text, others):
        return True
    # "Pós-graduação" names a master's, not the graduação inside it.
    rest = _without(text, others)
    wanted = _LEVEL_WORDS.get(degree, ())
    if isinstance(rest, str):
        return any(_unspaced(word) in rest for word in wanted if _UNSPACED.search(word))
    return _names_any(rest, wanted)


@dataclass(frozen=True, slots=True)
class SectionLabel:
    """R4: the lexicon entry a link label matched, and which kind of word it is."""

    phrase: str
    tier: int


def study_section_label(label: str, languages: Sequence[str], degree: str) -> SectionLabel | None:
    """R4: the study-section or catalogue word a link's label is, if any.

    ``languages`` are the institution's (``country_languages``). A catalogue
    word may stand beside one other word ("Carreras de pregrado launch"); a
    section word must be the whole label. Unspaced scripts have no word
    boundary, so there the label must be the phrase itself (学部 is a school,
    学部発展基金 a fund). A label for another degree level or for continuing
    education is never a section link.
    """
    if not label or not label.strip():
        return None
    codes = list(dict.fromkeys(_LANGUAGE_VARIANTS.get(code, code) for code in languages))
    best: SectionLabel | None = None
    unspaced = bool(_UNSPACED.search(label))
    tokens = [] if unspaced else _label_tokens(label)
    for tier, table in (
        (LOCAL_CATALOGUE_TIER, _LOCAL_CATALOGUE_WORDS),
        (LOCAL_SECTION_TIER, _LOCAL_SECTION_WORDS),
    ):
        allowed_extra = 1 if tier == LOCAL_CATALOGUE_TIER else 0
        for code in codes:
            for phrase in table.get(code, ()):
                if unspaced:
                    if not _UNSPACED.search(phrase) or _unspaced(label) != _unspaced(phrase):
                        continue
                else:
                    words = _label_tokens(phrase)
                    at = _contains(tokens, words)
                    if not words or at < 0:
                        continue
                    rest = tokens[:at] + tokens[at + len(words) :]
                    if sum(1 for word in rest if word not in _LABEL_NOISE) > allowed_extra:
                        continue
                candidate = SectionLabel(phrase=phrase, tier=tier)
                if best is None or len(phrase) > len(best.phrase):
                    best = candidate
        if best is not None:
            break
    if best is None or not label_fits_degree(label, degree):
        return None
    return best


#: Experiment ER-05, off until a paired capture decides. The KAIST blind trace
#: of 2026-09-27 found the undergraduate admission route behind a link labelled
#: "학부 입학" that the pipeline saw on six pages and never followed: it names
#: neither the field nor a URL word. With this on, a link whose text names
#: admission *and* the undergraduate level becomes a candidate. The words are
#: general vocabulary per language, not read from any benchmark or held-out
#: page.
ADMISSION_LEXICON = False
_ADMISSION_WORDS = (
    "admission",
    "admissions",
    "apply",
    "applying",
    "entry requirements",
    "입학",
    "入学",
    "zulassung",
    "bewerbung",
    "přijímací",
    "prijimaci",
    "přijetí",
    "vastuvõtt",
    "ammissione",
    "ammissioni",
    "priėmimas",
    "kabul",
    "başvuru",
    "admisión",
    "hakeminen",
    "haku",
    "поступление",
    "прием",
    "приём",
    "қабылдау",
)
_UNDERGRADUATE_WORDS = (
    "undergraduate",
    "bachelor",
    "bachelor's",
    "first-cycle",
    "학부",
    "学部",
    "本科",
    "bakalář",
    "bakalářsk",
    "bakalaureus",
    "bakalaur",
    "laurea triennale",
    "lisans",
    "kandidaatti",
    "бакалавр",
)


def _names_admission_route(text: str) -> bool:
    lowered = text.lower()
    return any(w in lowered for w in _ADMISSION_WORDS) and any(
        w in lowered for w in _UNDERGRADUATE_WORDS
    )


@dataclass(frozen=True, slots=True)
class NavigationLink:
    url: str
    text: str
    #: The page this link was found on. §11 wants a parent for every candidate.
    parent_url: str


def _clean(raw: str) -> str:
    return _SPACE.sub(" ", raw or "").strip()


def _names(term: str, haystack: str) -> bool:
    """Whether ``haystack`` names ``term`` as a word, not as a fragment.

    Substring matching put four faculty pages above the programme on KAIST's
    real navigation, because ``facultyInteractiveComputing`` contains
    ``computing``. A URL is split on its own separators and on camelCase, so a
    term has to be a segment rather than a coincidence.
    """
    words = re.split(
        r"[^0-9a-z\u0400-\u04ff\uac00-\ud7a3]+",
        re.sub(r"(?<=[a-z])(?=[A-Z])", " ", haystack).lower(),
    )
    wanted = [w for w in re.split(r"[^0-9a-z]+", term.lower()) if w]
    return bool(wanted) and all(w in words for w in wanted)


def links_from(html: str, base_url: str) -> tuple[NavigationLink, ...]:
    """Every same-institution link on the page, with its text, deduplicated.

    Off-domain links are dropped with the same registrable-domain comparison
    discovery uses, so a hop can never wander onto a partner site. Excluded
    paths — news, events, vacancies, media — go too: a hop is for finding a
    programme, and following the news feed is how a bounded step becomes a
    crawl.
    """
    try:
        tree = lxml_html.fromstring(html)
    except (ValueError, lxml_html.etree.ParserError):
        # Malformed or empty markup yields no links rather than an exception:
        # one unparseable page must not end a discovery run.
        return ()

    seen: set[str] = set()
    links: list[NavigationLink] = []
    anchors = sorted(tree.iter("a"), key=lambda a: not (a.get("href") or "").startswith("https"))
    for anchor in anchors:
        if len(links) >= MAX_LINKS_PER_PAGE:
            break
        href = (anchor.get("href") or "").split("#", 1)[0].strip()
        if not href:
            continue
        # A malformed link (a zero-width space in the host, a phone number
        # where the port goes) is dropped here, not raised: see ``page_link``.
        link = page_link(base_url, href)
        if link is None:
            continue
        url = canonical_url(link)
        if not url:
            continue
        if not same_institution(url, base_url) or is_excluded_path(url):
            continue
        if _NOT_A_PROGRAMME_LINK.search(url):
            continue
        # http:// and https:// of one page are one page. ``canonical_url``
        # keeps the scheme, correctly for the pipeline at large, but a site
        # that links itself both ways would otherwise spend two candidate
        # slots on the same document.
        identity = scheme_free_identity(url)
        if identity in seen:
            continue
        seen.add(identity)
        # A real parser, because the labels here decide the ranking. A regex
        # over anchors read KAIST's ``navi="교육"`` attributes as if they were
        # link text and ranked four staff pages above the programme.
        links.append(
            NavigationLink(url=url, text=_clean(anchor.text_content()), parent_url=base_url)
        )
    return tuple(links)


def _score(link: NavigationLink, intent: DiscoveryIntent) -> tuple[int, list[str]]:
    """How strongly this link looks like the requested programme, and why."""
    terms = retrieval_candidates(intent.field)
    strong = [t.term for t in terms if t.is_match]
    related = [t.term for t in terms if not t.is_match]

    text = link.text.lower()
    url = link.url.lower()
    score = 0
    signals: list[str] = []

    if matches_field_text(link.text, strong):
        score += 6
        signals.append("field_in_link_text")
    elif any(_names(term, url) for term in strong):
        score += 4
        signals.append("field_in_url")
    elif matches_field_text(link.text, related) or any(_names(t, url) for t in related):
        # The neighbourhood, which V2-12 says is a candidate and never a match.
        score += 1
        signals.append("related_field_only")

    named = degree_level_named(link.url) or degree_level_named(f"/{text}/")
    if named == str(intent.degree):
        score += 3
        signals.append("degree_matches")
    elif named is not None:
        # An outright rejection, not a penalty — the same rule V2-13's
        # prefilter applies. A master's page is not a weak bachelor lead, and
        # a strong field match in its link text must not buy it a place.
        return 0, ["other_degree_level"]

    if any(word in text or _names(word, url) for word in _SECTION_WORDS):
        score += 2
        signals.append("education_section")

    if ADMISSION_LEXICON and _names_admission_route(link.text):
        score += 5
        signals.append("admission_route_section")

    return score, signals


def navigation_candidates(
    html: str,
    base_url: str,
    intent: DiscoveryIntent,
    *,
    limit: int = DEFAULT_HOP_LIMIT,
) -> tuple[SourcedCandidate, ...]:
    """Links worth following from this page, best first, as fusion input.

    Emitted under ``CATALOGUE_WALKER`` so V2-16 merges them with search results
    and keeps both attributions when the two generators agree — which is the
    strongest signal fusion can produce and the reason to have both.
    """
    if limit < 1:
        raise ValueError(f"limit must be at least 1, got {limit}")

    scored = []
    for link in links_from(html, base_url):
        score, signals = _score(link, intent)
        if score <= 0:
            # A link with nothing to recommend it is navigation chrome. Keeping
            # it would hand fusion a hundred rows of footer.
            continue
        scored.append((score, link, signals))

    scored.sort(key=lambda row: (-row[0], row[1].url))
    return tuple(
        SourcedCandidate(
            url=link.url,
            generator=Generator.CATALOGUE_WALKER,
            rank=rank,
            title=link.text,
        )
        for rank, (_, link, _signals) in enumerate(scored[:limit], start=1)
    )
