"""LL-1: recovery's listing follow-up reads a listing in its own words.

MISS_STAGES_2026-10-19 §3, candidate 6 (``LISTING_FOLLOWS_LOCAL_ALIASES``).
kaznu's bachelor listing (dev2) wraps each programme in one card anchor whose
text runs the code, the name and a description together, so no label matched
the field although the card's name is an ontology alias; msu's
``cs.msu.ru/education/bachelors`` (dev3), headed "Бакалавриат", was refused on
subject and its links were never looked at. On: a link is also followed when
the first heading inside its anchor matches the field (``matches_field_text``:
the applicant's words and the ontology's strong and localized aliases, nothing
added), and a refused page whose head names only the requested level is
followed as a listing.

The synthetic pages are written here in Russian, Kazakh and Czech. The dev
fixtures under ``fixtures/listing_local_aliases`` were read once through the
production ``Fetcher`` (``trust_env_proxy=True``, robots honoured) on
2026-10-19: kaznu's listing page holding the gold card and the gold itself,
msu's level-headed listing, and vut's branch page (the rule must not fire there).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.catalog_walker import extract_links
from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import head_names_only_a_level
from app.adapters.search.retrieval import RankedCandidate
from evaluation.research import live
from tests.test_live_discovery import StubSite

BACKEND = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "listing_local_aliases"
CS = ["computer science"]
HOST = "https://www.uni.example"


@pytest.fixture(params=[False, True], ids=["off", "on"])
def ll1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "LISTING_FOLLOWS_LOCAL_ALIASES", request.param)
    return request.param


@pytest.fixture
def ll1_on(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "LISTING_FOLLOWS_LOCAL_ALIASES", True)


def test_the_rule_is_off_by_default() -> None:
    assert live_discovery.LISTING_FOLLOWS_LOCAL_ALIASES is False


# --- a head that names only a level -----------------------------------------


@pytest.mark.parametrize(
    ("head", "lang", "level"),
    [
        ("Бакалавриат", "ru", "bachelor"),
        ("Бакалавр", "kk", "bachelor"),
        ("Bachelor", "en", "bachelor"),
        ("Undergraduate", "", "bachelor"),
        ("Магистратура", "ru", "master"),
    ],
)
def test_a_level_word_alone_names_its_level(head, lang, level) -> None:
    assert head_names_only_a_level(head, lang) == level


@pytest.mark.parametrize(
    ("head", "lang"),
    [
        ("Программы бакалавриата", "ru"),  # a list's own words: not a level alone
        ("Компьютерные науки", "ru"),
        ("Bakalářské studium Informatika", "cs"),
        ("Bachelor of Computer Science", ""),
        ("Bachelor and Master", ""),  # two levels
        ("", ""),
    ],
)
def test_any_other_word_or_two_levels_is_not_a_level_head(head, lang) -> None:
    assert head_names_only_a_level(head, lang) is None


# --- a card's own heading ---------------------------------------------------

#: (language, page head, card heading naming the field, gold page heading)
LANGUAGES = [
    ("ru", "Образовательные программы", "Компьютерные науки", "Бакалавриат: Компьютерные науки"),
    ("kk", "Білім беру бағдарламалары", "Информатика", "Бакалавриат: Информатика"),
    ("cs", "Studijní programy", "Informatika", "Bakalářský studijní program Informatika"),
]
LANG_IDS = [lang for lang, *_ in LANGUAGES]
CARD_OTHERS = {
    "ru": ["Журналистика", "Социология", "Психология", "Политология", "Биология"],
    "kk": ["Журналистика", "Әлеуметтану", "Психология", "Саясаттану", "Биология"],
    "cs": ["Žurnalistika", "Sociologie", "Psychologie", "Politologie", "Biologie"],
}
DESCRIPTION = {
    "ru": "Цель образовательной программы - подготовка конкурентоспособных специалистов.",
    "kk": "Білім беру бағдарламасының мақсаты - бәсекеге қабілетті мамандарды даярлау.",
    "cs": "Cílem studijního programu je připravit konkurenceschopné odborníky.",
}


def _card(url: str, code: str, name: str, lang: str) -> str:
    return (
        f"<a class='card' href='{url}'><div class='code'>{code}</div>"
        f"<h2>{name}</h2><div class='subtitle'>{DESCRIPTION[lang]}</div></a>"
    )


def _card_listing(lang: str, head: str, field_card: str, gold: str) -> str:
    cards = [
        _card(f"{HOST}/{lang}/programmes/{i + 1}", f"6B0{i}101", name, lang)
        for i, name in enumerate(CARD_OTHERS[lang])
    ]
    cards.insert(2, _card(gold, "6B06104", field_card, lang))
    return (
        f"<html lang='{lang}'><head><title>{head} | U</title></head><body><main>"
        f"<h1>{head}</h1><p>{' '.join([DESCRIPTION[lang]] * 12)}</p>"
        f"<div class='cards'>{''.join(cards)}</div></main></body></html>"
    )


def _gold_html(lang: str, heading: str) -> str:
    body = {
        "ru": "Срок обучения - 4 года. Язык обучения: русский. Прием документов до 25 августа.",
        "kk": "Оқу мерзімі - 4 жыл. Оқыту тілі: қазақ. Құжаттарды қабылдау 25 тамызға дейін.",
        "cs": "Standardní doba studia: 3 roky. Jazyk výuky: čeština. Přihlášky do 31. března.",
    }[lang]
    return (
        f"<html lang='{lang}'><head><title>{heading}</title></head><body><main>"
        f"<h1>{heading}</h1><p>{body}</p></main></body></html>"
    )


@pytest.mark.parametrize(("lang", "head", "card", "gold_head"), LANGUAGES, ids=LANG_IDS)
def test_extract_links_keeps_the_cards_heading_only_on(ll1, lang, head, card, gold_head) -> None:
    gold = f"{HOST}/{lang}/programmes/1730"
    links = extract_links(_card_listing(lang, head, card, gold), f"{HOST}/{lang}/", "uni.example")
    by_url = {link.url: link for link in links}
    assert card in by_url[gold].label and DESCRIPTION[lang][:20] in by_url[gold].label
    assert by_url[gold].heading == (card if ll1 else "")


async def _recover(tmp_path, profile, pages, leads, country):
    profile.context.intended_fields = list(CS)
    site = StubSite(pages)
    trace = DiscoveryTrace(institution="U", domain="uni.example", country=country)
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(leads, found, trace, profile)
    return found, trace, site.requested


COUNTRY = {"ru": "Russia", "kk": "Kazakhstan", "cs": "Czech Republic"}


@pytest.mark.asyncio
@pytest.mark.parametrize(("lang", "head", "card", "gold_head"), LANGUAGES, ids=LANG_IDS)
async def test_recovery_follows_a_card_named_by_a_local_alias_only_on(
    tmp_path, profile, ll1, lang, head, card, gold_head
) -> None:
    listing = f"{HOST}/{lang}/programmes"
    gold = f"{listing}/1730"
    pages: dict[str, bytes | str] = {
        listing: _card_listing(lang, head, card, gold),
        gold: _gold_html(lang, gold_head),
    }
    leads = [RankedCandidate(listing, head, 2.0, "fake")]
    found, trace, requested = await _recover(tmp_path, profile, pages, leads, COUNTRY[lang])
    assert requested[0] == listing
    assert any("program_catalog" in reason for url, reason in trace.rejected if url == listing)
    if ll1:
        # Only the card the alias names is followed; the other cards stay unread.
        assert requested == [listing, gold]
        assert found == [gold]
    else:
        assert requested == [listing]
        assert found == []


# --- a refused page headed by the level alone -------------------------------


def _level_page(lang: str, head: str, links: list[tuple[str, str]]) -> str:
    items = "".join(f"<li><a href='{url}'>{label}</a></li>" for url, label in links)
    return (
        f"<html lang='{lang}'><head><title>{head} | Факультет</title></head><body><main>"
        f"<h1>{head}</h1><p>Обучение ведется по направлениям подготовки.</p>"
        f"<ul>{items}</ul></main></body></html>"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("lang", "head", "followed_when_on"),
    [("ru", "Бакалавриат", True), ("kk", "Бакалавр", True), ("ru", "Магистратура", False)],
)
async def test_a_refused_page_headed_by_the_requested_level_is_followed_on(
    tmp_path, profile, ll1, lang, head, followed_when_on
) -> None:
    page = f"{HOST}/{lang}/education/level"
    gold = f"{HOST}/{lang}/education/informatika"
    related = f"{HOST}/{lang}/education/pmi"
    pages: dict[str, bytes | str] = {
        page: _level_page(
            lang,
            head,
            [(gold, "Информатика"), (related, "Прикладная математика и информатика")],
        ),
        gold: _gold_html(lang, "Бакалавриат: Информатика"),
    }
    leads = [RankedCandidate(page, head, 2.0, "fake")]
    found, trace, requested = await _recover(tmp_path, profile, pages, leads, COUNTRY[lang])
    assert requested[0] == page
    assert page in {url for url, _reason in trace.rejected}
    # A related programme's label is never a lead, on or off.
    assert related not in requested
    if ll1 and followed_when_on:
        assert requested == [page, gold]
        assert found == [gold]
    else:
        assert requested == [page]
        assert found == []


# --- the development pages --------------------------------------------------

KAZNU_LISTING = "https://welcome.kaznu.kz/ru/education_programs/bachelor?page=10"
KAZNU_GOLD = "https://welcome.kaznu.kz/ru/education_programs/bachelor/speciality/1730"
MSU_LISTING = "https://cs.msu.ru/education/bachelors"
VUT_BRANCH = "https://www.vut.cz/en/students/programmes/branch/11814/6090"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


async def _recover_dev(tmp_path, profile, pages, lead, domain, country):
    profile.context.intended_fields = list(CS)
    site = StubSite(pages)
    trace = DiscoveryTrace(institution="U", domain=domain, country=country)
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(
            [RankedCandidate(lead, "", 2.0, "fake")], found, trace, profile
        )
    return found, site.requested


@pytest.mark.asyncio
async def test_kaznu_gold_card_is_followed_from_its_listing_only_on(tmp_path, profile, ll1) -> None:
    pages: dict[str, bytes | str] = {
        KAZNU_LISTING: _fixture("kaznu_bachelor_listing_page10.html"),
        KAZNU_GOLD: _fixture("kaznu_speciality_1730.html"),
    }
    found, requested = await _recover_dev(
        tmp_path, profile, pages, KAZNU_LISTING, "kaznu.kz", "Kazakhstan"
    )
    if ll1:
        # "6B06104 Компьютерные науки Целью …": the card's h2 is an R1 alias.
        assert requested == [KAZNU_LISTING, KAZNU_GOLD]
        assert found == [KAZNU_GOLD]
    else:
        assert requested == [KAZNU_LISTING]
        assert found == []


@pytest.mark.asyncio
async def test_msu_level_listing_is_read_as_a_listing_and_follows_nothing_related(
    tmp_path, profile, ll1
) -> None:
    # "Бакалавриат" heads it; its programme links are "Прикладная математика и
    # информатика" and "Фундаментальная информатика и …" (related, never
    # leads) and it does not link the gold (pk.cs.msu.ru): nothing is followed.
    pages: dict[str, bytes | str] = {MSU_LISTING: _fixture("msu_cs_bachelors.html")}
    found, requested = await _recover_dev(tmp_path, profile, pages, MSU_LISTING, "msu.ru", "Russia")
    assert head_names_only_a_level("Бакалавриат", "ru") == "bachelor"
    assert requested == [MSU_LISTING]
    assert found == []


@pytest.mark.asyncio
async def test_vut_branch_page_is_untouched(tmp_path, profile, ll1) -> None:
    pages: dict[str, bytes | str] = {VUT_BRANCH: _fixture("vut_branch_11814_6090.html")}
    found, requested = await _recover_dev(
        tmp_path, profile, pages, VUT_BRANCH, "vut.cz", "Czech Republic"
    )
    assert requested == [VUT_BRANCH]
    assert found == []


# --- the harness ------------------------------------------------------------


def test_harness_exposes_forwards_and_negates_the_flag(monkeypatch, tmp_path) -> None:
    from tests.test_benchmark_rule_negations import _parent

    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--listing-follows-local-aliases" in result.stdout
    assert "--no-listing-follows-local-aliases" in result.stdout
    assert live.NEGATABLE_RULES["listing-follows-local-aliases"] == (
        ("app.adapters.discovery.live_discovery", "LISTING_FOLLOWS_LOCAL_ALIASES"),
    )
    assert "listing-follows-local-aliases" in live.DEFAULT_OFF_NEGATABLE
    commands = _parent(monkeypatch, tmp_path, "--listing-follows-local-aliases")
    assert "--listing-follows-local-aliases" in commands[0]


def test_the_child_switches_the_rule_on(monkeypatch, tmp_path) -> None:
    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        seen["ll1"] = live_discovery.LISTING_FOLLOWS_LOCAL_ALIASES

    monkeypatch.setattr(live_discovery, "LISTING_FOLLOWS_LOCAL_ALIASES", False)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "kaznu", "--out", str(tmp_path / "u.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--listing-follows-local-aliases"])
    live.main()
    assert seen == {"ll1": True}
