"""AW-2: the award-page battery, one synthetic award page per language.

REACH_ROWS_2026-10-20 (AW-1 step 1): the award-page classifier's words were
English only, so dev4's German award page, which states its monthly amount,
target group and application route in German, found 0 of the six
``_AWARD_SIGNALS`` and was refused as "not an award page". Rule AW-2 gives
every language of ``languages.json`` a row of ``award_lexicon.DICTIONARY``
(dictionary- or statute-sourced, cited per row), read under the page's own
``<html lang>`` while ``page_classifier.AWARD_SIGNALS_ALL_LANGUAGES`` is on.

The battery follows LV-1's (``tests/test_lexicon_language_coverage.py``): for
every language, a synthetic award page written in that language's dictionary
words is an award page with the flag on and is not one with it off; a news
page, a page about how to apply for awards and a listing heading in the same
language stay refused with the flag on; an English award page reads the same
either way. Every sentence below is written from the row's own dictionary
words; none comes from a page, no page is fetched, and no heldout file,
capture, log or label was opened.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.adapters import award_lexicon, page_classifier
from app.adapters.award_lexicon import DICTIONARY, SIGNAL_NAMES
from app.adapters.page_classifier import PageType, classify_page
from app.adapters.scholarship import web_scholarships
from evaluation.research import live
from tests.test_lexicon_language_coverage import LANGUAGES


@dataclass(frozen=True)
class AwardPage:
    """One language's synthetic award page, and three pages that are not one award."""

    #: The award's name (title and h1).
    name: str
    #: One sentence per signal, in ``SIGNAL_NAMES`` order.
    amount: str
    coverage: str
    eligibility: str
    application: str
    deadline: str
    #: The title of a news item about the award.
    news: str
    #: The title of a page about how to apply for awards.
    process: str
    #: The plural category heading of a list of awards.
    listing: str


PAGES: dict[str, AwardPage] = {
    "ca": AwardPage(
        "Beca Zq d'Excel·lència",
        "L'import de la beca és de 300 euros per mes.",
        "La beca comporta l'exempció de la matrícula.",
        "Requisits: la poden demanar els estudiants de primer curs.",
        "La sol·licitud es presenta en línia.",
        "El termini acaba el 15 de març.",
        "Notícies: la Beca Zq, adjudicada",
        "Com sol·licitar una beca",
        "Beques i ajuts a l'estudi",
    ),
    "cs": AwardPage(
        "Stipendium Zq",
        "Výše stipendia je 5000 Kč měsíčně.",
        "Stipendium zahrnuje prominutí školného.",
        "Podmínky: o stipendium se mohou ucházet studenti prvního ročníku.",
        "Žádost se podává elektronicky.",
        "Uzávěrka je 15. března.",
        "Aktuality: Stipendium Zq uděleno",
        "Jak podat žádost o stipendium",
        "Stipendia a granty pro studenty",
    ),
    "da": AwardPage(
        "Zq Legat",
        "Legatet udgør et beløb på 3.000 kr. om måneden.",
        "Legatet dækker studieafgiften.",
        "Betingelser: legatet kan søges af studerende på første år.",
        "Ansøgningen indsendes online.",
        "Ansøgningsfristen er den 15. marts.",
        "Nyheder: Zq Legat uddelt",
        "Sådan søger du et legat",
        "Legater og stipendier til studerende",
    ),
    "de": AwardPage(
        "Zq-Stipendium",
        "Das Stipendium beträgt 300 Euro monatlich.",
        "Zusätzlich gibt es eine Befreiung von den Studiengebühren.",
        "Bewerben können sich Studierende im ersten Fachsemester.",
        "Die Bewerbung erfolgt online.",
        "Bewerbungsfrist ist der 15. März.",
        "Neuigkeiten: Zq-Stipendium vergeben",
        "Bewerbung um ein Stipendium",
        "Stipendien für Studierende",
    ),
    "es": AwardPage(
        "Beca Zq de Excelencia",
        "La cuantía de la beca es de 300 euros al mes.",
        "Incluye la exención de matrícula.",
        "Requisitos: pueden pedirla los estudiantes de primer año.",
        "La solicitud se presenta en línea.",
        "El plazo termina el 15 de marzo.",
        "Noticias: la Beca Zq, concedida",
        "Cómo solicitar una beca",
        "Becas y ayudas al estudio",
    ),
    "et": AwardPage(
        "Zq stipendium",
        "Stipendiumi suurus on 300 eurot kuus.",
        "Stipendium katab õppetasu.",
        "Tingimused: esimese kursuse üliõpilased.",
        "Taotlus esitatakse veebis.",
        "Tähtaeg on 15. märts.",
        "Uudised: Zq stipendium välja antud",
        "Kuidas taotleda stipendiumi",
        "Stipendiumid ja toetused",
    ),
    "fi": AwardPage(
        "Zq-apuraha",
        "Apurahan suuruus on 300 euroa kuukaudessa.",
        "Apuraha kattaa lukuvuosimaksun.",
        "Hakukelpoisuus: ensimmäisen vuoden opiskelijat.",
        "Hakemus jätetään verkossa.",
        "Hakuaika päättyy 15. maaliskuuta.",
        "Uutiset: Zq-apuraha myönnetty",
        "Näin haet apurahaa",
        "Apurahat ja stipendit",
    ),
    "fr": AwardPage(
        "Bourse Zq d'excellence",
        "Le montant de la bourse s'élève à 300 euros par mois.",
        "La bourse comprend l'exonération des frais d'inscription.",
        "Conditions d'éligibilité : étudiants de première année.",
        "La candidature se fait en ligne.",
        "Date limite : 15 mars.",
        "Actualités : la Bourse Zq attribuée",
        "Comment candidater à une bourse",
        "Bourses et aides financières pour les étudiants",
    ),
    "it": AwardPage(
        "Borsa di studio Zq",
        "L'importo della borsa è pari a 300 euro al mese.",
        "La borsa prevede l'esonero dalle tasse universitarie.",
        "Requisiti: possono partecipare gli studenti del primo anno.",
        "La domanda si presenta online.",
        "La scadenza è il 15 marzo.",
        "Notizie: assegnata la borsa di studio Zq",
        "Come presentare domanda per una borsa di studio",
        "Borse di studio per studenti internazionali",
    ),
    "ja": AwardPage(
        "Zq奨学金",
        "支給額は月額3万円です。",
        "授業料も免除されます。",
        "応募資格：学部1年生。",
        "申請はオンラインで行います。",
        "締切は3月15日です。",
        "ニュース：Zq奨学金の授与",
        "奨学金の申請方法",
        "奨学金制度",
    ),
    "kk": AwardPage(
        "Zq шәкіртақысы",
        "Шәкіртақы мөлшері айына 100 000 теңге.",
        "Шәкіртақы оқу ақысын өтейді.",
        "Талаптар: бірінші курс студенттері.",
        "Өтінім онлайн қабылданады.",
        "Соңғы күні – 15 наурыз.",
        "Жаңалықтар: Zq шәкіртақысы тағайындалды",
        "Шәкіртақыға өтінім беру",
        "Шәкіртақылар мен гранттар",
    ),
    "ko": AwardPage(
        "Zq 장학금",
        "지급액은 매월 30만 원입니다.",
        "등록금 감면도 포함됩니다.",
        "지원 자격: 1학년 학생.",
        "신청은 온라인으로 합니다.",
        "마감은 3월 15일입니다.",
        "뉴스: Zq 장학금 수여",
        "장학금 신청 방법",
        "장학금 안내",
    ),
    "lt": AwardPage(
        "Zq stipendija",
        "Stipendijos dydis – 300 eurų per mėnesį.",
        "Stipendija padengia studijų kainą.",
        "Reikalavimai: pirmo kurso studentai.",
        "Paraiška teikiama internetu.",
        "Terminas – kovo 15 d.",
        "Naujienos: paskirta Zq stipendija",
        "Kaip pateikti paraišką stipendijai",
        "Stipendijos ir parama",
    ),
    "nb": AwardPage(
        "Zq-stipendet",
        "Stipendet utgjør et beløp på 3000 kroner i måneden.",
        "Stipendet dekker studieavgiften.",
        "Vilkår: stipendet kan søkes av studenter på første år.",
        "Søknaden sendes inn elektronisk.",
        "Søknadsfristen er 15. mars.",
        "Nyheter: Zq-stipendet tildelt",
        "Slik søker du stipend",
        "Stipender og legater for studenter",
    ),
    "nl": AwardPage(
        "Zq-beurs",
        "Het bedrag van de beurs is 300 euro per maand.",
        "De beurs omvat een vrijstelling van het collegegeld.",
        "Voorwaarden: studenten in het eerste jaar komen in aanmerking.",
        "De aanvraag dien je online in.",
        "De sluitingsdatum is 15 maart.",
        "Nieuws: Zq-beurs toegekend",
        "Hoe vraag je een beurs aan",
        "Beurzen voor internationale studenten",
    ),
    "nn": AwardPage(
        "Zq-stipendet",
        "Stipendet utgjer eit beløp på 3000 kroner i månaden.",
        "Stipendet dekkjer studieavgifta.",
        "Vilkår: stipendet kan søkjast av studentar på første år.",
        "Søknaden blir send inn elektronisk.",
        "Søknadsfristen er 15. mars.",
        "Nyheiter: Zq-stipendet tildelt",
        "Slik søkjer du stipend",
        "Stipend og legat for studentar",
    ),
    "no": AwardPage(
        "Zq-stipendet",
        "Stipendet utgjør et beløp på 3000 kroner i måneden.",
        "Stipendet dekker studieavgiften.",
        "Vilkår: stipendet kan søkes av studenter på første år.",
        "Søknaden sendes inn elektronisk.",
        "Søknadsfristen er 15. mars.",
        "Nyheter: Zq-stipendet tildelt",
        "Slik søker du stipend",
        "Stipender og legater for studenter",
    ),
    "pl": AwardPage(
        "Stypendium Zq",
        "Wysokość stypendium wynosi 1000 zł miesięcznie.",
        "Stypendium obejmuje zwolnienie z czesnego.",
        "Warunki: o stypendium mogą ubiegać się studenci pierwszego roku.",
        "Wniosek składa się elektronicznie.",
        "Termin składania upływa 15 marca.",
        "Aktualności: przyznano Stypendium Zq",
        "Jak złożyć wniosek o stypendium",
        "Stypendia dla studentów",
    ),
    "pt": AwardPage(
        "Bolsa Zq de Mérito",
        "O valor da bolsa é de 300 euros por mês.",
        "A bolsa inclui isenção de propinas.",
        "Requisitos: estudantes do primeiro ano.",
        "A candidatura é feita online.",
        "O prazo termina a 15 de março.",
        "Notícias: atribuída a Bolsa Zq",
        "Como se candidatar a uma bolsa",
        "Bolsas de estudo para estudantes internacionais",
    ),
    "ru": AwardPage(
        "Стипендия Zq",
        "Размер стипендии — 20 000 рублей в месяц.",
        "Стипендия включает освобождение от оплаты обучения.",
        "Требования: студенты первого курса.",
        "Заявка подаётся онлайн.",
        "Срок подачи — 15 марта.",
        "Новости: присуждена стипендия Zq",
        "Как подать заявку на стипендию",
        "Стипендии и гранты для студентов",
    ),
    "sk": AwardPage(
        "Štipendium Zq",
        "Výška štipendia je 300 eur mesačne.",
        "Štipendium zahŕňa odpustenie školného.",
        "Podmienky: o štipendium sa môžu uchádzať študenti prvého ročníka.",
        "Žiadosť sa podáva elektronicky.",
        "Uzávierka je 15. marca.",
        "Aktuality: udelené Štipendium Zq",
        "Ako podať žiadosť o štipendium",
        "Štipendiá a granty pre študentov",
    ),
    "sv": AwardPage(
        "Zq-stipendiet",
        "Stipendiets belopp är 3000 kronor per månad.",
        "Stipendiet täcker studieavgiften.",
        "Villkor: studenter i årskurs ett.",
        "Ansökan görs digitalt.",
        "Sista ansökningsdag är den 15 mars.",
        "Nyheter: Zq-stipendiet utdelat",
        "Så söker du stipendium",
        "Stipendier för studenter",
    ),
    "th": AwardPage(
        "ทุนการศึกษา Zq",
        "จำนวนเงิน 5,000 บาทต่อเดือน",
        "ทุนนี้ครอบคลุมค่าเล่าเรียน",
        "คุณสมบัติ: นักศึกษาชั้นปีที่ 1",
        "การสมัครทำทางออนไลน์",
        "ปิดรับวันที่ 15 มีนาคม",
        "ข่าว: มอบทุนการศึกษา Zq",
        "วิธีการสมัครทุนการศึกษา",
        "ทุนการศึกษา",
    ),
    "tr": AwardPage(
        "Zq Bursu",
        "Burs tutarı aylık 5.000 TL'dir.",
        "Burs öğrenim ücretini karşılar.",
        "Kimler başvurabilir: birinci sınıf öğrencileri.",
        "Başvuru formu çevrim içi doldurulur.",
        "Son başvuru tarihi 15 Mart'tır.",
        "Haberler: Zq Bursu verildi",
        "Burs Başvurusu",
        "Burslar ve hibeler",
    ),
    "zh": AwardPage(
        "Zq奖学金",
        "奖励金额为每人5000元。",
        "并可减免学费。",
        "申请条件：一年级本科生。",
        "申请在网上进行。",
        "截止日期为3月15日。",
        "新闻：Zq奖学金颁发",
        "奖学金申请指南",
        "奖学金",
    ),
}

ENGLISH_AWARD = AwardPage(
    "Zq Merit Scholarship",
    "The scholarship is worth EUR 300 per month.",
    "It covers tuition.",
    "Who can apply: first-year students.",
    "How to apply: online.",
    "Deadline: 15 March.",
    "News: Zq Merit Scholarship awarded",
    "How to apply",
    "Scholarships",
)


def _url(lang: str, slug: str = "zq") -> str:
    _country, region = LANGUAGES.get(lang, ("", "example"))
    return f"https://www.uni.{region}/{slug}"


def _html(lang: str, title: str, page: AwardPage) -> str:
    body = "".join(
        f"<p>{getattr(page, name)}</p>"
        for name in ("amount", "coverage", "eligibility", "application", "deadline")
    )
    return (
        f'<html lang="{lang}"><head><title>{title} | Zq</title></head><body><main>'
        f"<h1>{title}</h1>{body}</main></body></html>"
    )


def _classify(lang: str, title: str, page: AwardPage | None = None):
    page = page or PAGES[lang]
    return classify_page(url=_url(lang), html=_html(lang, title, page))


@pytest.fixture
def aw2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(page_classifier, "AWARD_SIGNALS_ALL_LANGUAGES", True)


@pytest.fixture
def aw2_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(page_classifier, "AWARD_SIGNALS_ALL_LANGUAGES", False)


# --- the table ---------------------------------------------------------------------


def test_the_dictionary_and_the_battery_cover_exactly_the_languages_of_languages_json() -> None:
    assert set(DICTIONARY) == set(LANGUAGES)
    assert set(PAGES) == set(LANGUAGES)


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_every_row_has_every_word_class_and_a_source(lang: str) -> None:
    row = DICTIONARY[lang]
    for field in ("noun", "listing", "process", "news", *SIGNAL_NAMES, "source"):
        assert getattr(row, field).strip(), field
    # A dictionary or a statute is named; no site.
    assert "s.v." in row.source or "Law" in row.source or "Act" in row.source
    assert "http" not in row.source
    words = award_lexicon.award_words(lang)
    assert words is not None and set(words.signals) == set(SIGNAL_NAMES)


def test_english_and_pages_without_a_language_have_no_row() -> None:
    assert award_lexicon.award_words("en") is None
    assert award_lexicon.award_words("") is None
    # A region subtag reads the language's row.
    assert award_lexicon.award_words("de-AT") is award_lexicon.award_words("de")


def test_the_rule_is_on_by_default() -> None:
    # On since the 2026-10-20 replay: no stable loss, no new wrong page (four sets, normal + knockout).
    assert page_classifier.AWARD_SIGNALS_ALL_LANGUAGES is True


# --- the battery, flag on ----------------------------------------------------------


@pytest.mark.usefixtures("aw2")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_on_the_award_page_is_an_award_page_with_every_signal(lang: str) -> None:
    page = PAGES[lang]
    result = _classify(lang, page.name)
    assert result.page_type is PageType.SCHOLARSHIP_AWARD, result.signals
    assert result.subject == page.name
    assert f"signals: {', '.join(SIGNAL_NAMES)}" in result.signals


@pytest.mark.usefixtures("aw2")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_on_a_news_item_about_the_award_is_news(lang: str) -> None:
    result = _classify(lang, PAGES[lang].news)
    assert result.page_type is PageType.NEWS, result.signals


@pytest.mark.usefixtures("aw2")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_on_a_page_about_how_to_apply_for_awards_is_no_award(lang: str) -> None:
    result = _classify(lang, PAGES[lang].process)
    assert result.page_type is not PageType.SCHOLARSHIP_AWARD, result.signals
    assert result.page_type is PageType.UNKNOWN, result.signals


@pytest.mark.usefixtures("aw2")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_on_a_listing_heading_is_a_list_of_awards(lang: str) -> None:
    result = _classify(lang, PAGES[lang].listing)
    assert result.page_type is PageType.SCHOLARSHIP_INDEX, result.signals
    assert "listing heading" in result.signals


@pytest.mark.usefixtures("aw2")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_on_a_process_page_that_names_no_award_is_not_a_funding_page(lang: str) -> None:
    """The local signal words alone never make a funding page: the gate is the noun."""
    page = PAGES[lang]
    on = classify_page(url=_url(lang), html=_html(lang, "Zq", page))
    assert on.page_type is not PageType.SCHOLARSHIP_AWARD
    assert on.page_type is not PageType.SCHOLARSHIP_INDEX


# --- the flag off: nothing in the page's language is read --------------------------


@pytest.mark.usefixtures("aw2_off")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_off_the_award_page_is_refused(lang: str) -> None:
    result = _classify(lang, PAGES[lang].name)
    assert result.page_type is not PageType.SCHOLARSHIP_AWARD, result.signals


@pytest.mark.usefixtures("aw2_off")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_off_the_non_award_pages_stay_refused(lang: str) -> None:
    page = PAGES[lang]
    for title in (page.news, page.process, page.listing):
        assert _classify(lang, title).page_type is not PageType.SCHOLARSHIP_AWARD, title


def test_off_no_row_is_ever_looked_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """Off is the code path of before AW-2: ``award_words`` is never called."""

    def boom(lang: str) -> None:
        raise AssertionError(f"award_words({lang!r}) called with AW-2 off")

    monkeypatch.setattr(page_classifier, "AWARD_SIGNALS_ALL_LANGUAGES", False)
    monkeypatch.setattr(page_classifier, "award_words", boom)
    for lang, page in PAGES.items():
        for title in (page.name, page.news, page.process, page.listing):
            _classify(lang, title)


# --- English, either way ------------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "de", ""])
def test_an_english_award_page_reads_the_same_on_and_off(monkeypatch, lang: str) -> None:
    """English words are read as before, whatever the page declares (or no lang at all)."""
    results = []
    for on in (False, True):
        monkeypatch.setattr(page_classifier, "AWARD_SIGNALS_ALL_LANGUAGES", on)
        html = _html(lang, ENGLISH_AWARD.name, ENGLISH_AWARD)
        if not lang:
            html = html.replace(' lang=""', "")
        results.append(classify_page(url="https://www.uni.example/zq", html=html))
    assert results[0] == results[1]
    assert results[1].page_type is PageType.SCHOLARSHIP_AWARD


@pytest.mark.parametrize(
    "title", [ENGLISH_AWARD.news, "How to apply for a scholarship", ENGLISH_AWARD.listing]
)
def test_english_non_award_pages_read_the_same_on_and_off(monkeypatch, title: str) -> None:
    results = []
    for on in (False, True):
        monkeypatch.setattr(page_classifier, "AWARD_SIGNALS_ALL_LANGUAGES", on)
        results.append(classify_page(url=_url("en"), html=_html("en", title, ENGLISH_AWARD)))
    assert results[0] == results[1]


@pytest.mark.usefixtures("aw2")
def test_on_a_local_page_without_a_lang_attribute_is_unchanged() -> None:
    """The row is read under the page's own ``<html lang>`` only."""
    page = PAGES["es"]
    html = _html("es", page.name, page).replace(' lang="es"', "")
    assert classify_page(url=_url("es"), html=html).page_type is not PageType.SCHOLARSHIP_AWARD


@pytest.mark.usefixtures("aw2")
def test_on_one_languages_words_do_not_count_under_another() -> None:
    page = PAGES["de"]
    html = _html("fr", page.name, page)
    result = classify_page(url=_url("fr"), html=html)
    assert result.page_type is not PageType.SCHOLARSHIP_AWARD


@pytest.mark.usefixtures("aw2")
@pytest.mark.parametrize(
    ("lang", "title"),
    [
        # The dative of Turkish "burs" is also the city of Bursa.
        ("tr", "Bursa Kampüsü"),
        # A programme page named after its field stays one, whatever its body says.
        ("de", "Informatik (Bachelor of Science)"),
    ],
)
def test_on_neighbouring_words_do_not_open_the_funding_branch(lang: str, title: str) -> None:
    page = PAGES[lang]
    result = classify_page(url=_url(lang), html=_html(lang, title, page))
    assert result.page_type not in (PageType.SCHOLARSHIP_AWARD, PageType.SCHOLARSHIP_INDEX)


# --- dev4's shape: a German award page with one award link -------------------------


DEV4_SHAPE = (
    '<html lang="de"><head><title>Zq-Stipendium | Zq</title></head><body><main>'
    "<h1>Zq-Stipendium</h1>"
    "<p>Das Zq-Stipendium fördert Studierende aus Zqland mit 300 Euro monatlich.</p>"
    "<p>Zielgruppe: Studierende im ersten Fachsemester.</p>"
    "<p>Die Bewerbung erfolgt über das Online-Portal.</p>"
    '<p><a href="/stipendien/zq-stipendium/merkblatt">Merkblatt zum Zq-Stipendium</a></p>'
    "</main></body></html>"
)
DEV4_URL = "https://www.zq-uni.de/stipendien/zq-stipendium"


def test_dev4s_shape_is_refused_off_and_an_award_on(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "AWARD_SIGNALS_ALL_LANGUAGES", False)
    off = classify_page(url=DEV4_URL, html=DEV4_SHAPE)
    assert off.page_type is PageType.UNKNOWN
    assert off.signals == ["funding page with 0 substantive signals and no clear award name"]
    monkeypatch.setattr(page_classifier, "AWARD_SIGNALS_ALL_LANGUAGES", True)
    on = classify_page(url=DEV4_URL, html=DEV4_SHAPE)
    assert on.page_type is PageType.SCHOLARSHIP_AWARD
    assert "signals: amount, eligibility, application" in on.signals


INDEX_URL = "https://www.zq-uni.de/stipendien"
INDEX = (
    "<html><head><title>Scholarships</title></head><body><main><h1>Scholarships</h1>"
    "<p>Overview of scholarships available to our students.</p>"
    f'<ul><li><a href="{DEV4_URL}">Zq-Stipendium</a></li></ul></main></body></html>'
)


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
async def test_the_walk_records_the_german_award_only_with_the_rule(tmp_path, monkeypatch, on):
    from tests.test_award_page_evidence import _find

    monkeypatch.setattr(page_classifier, "AWARD_SIGNALS_ALL_LANGUAGES", on)
    awards, result, site = await _find(
        tmp_path,
        monkeypatch,
        {INDEX_URL: INDEX, DEV4_URL: DEV4_SHAPE},
        on=True,
        domain="zq-uni.de",
        scholarships_url=INDEX_URL,
    )
    assert DEV4_URL in site.requested
    assert ("Zq-Stipendium" in {a.name for a in awards}) is on
    detail = next(o.detail for o in result.page_outcomes if o.url == DEV4_URL)
    if on:
        assert detail.startswith("award page;")
    else:
        assert detail.startswith("not an award page; no scholarship recorded")
    assert web_scholarships.SAME_SITE_AWARD_LINKS is False


# --- the harness flag ----------------------------------------------------------------


def test_the_flag_is_a_negatable_rule(tmp_path, monkeypatch) -> None:
    from tests.test_benchmark_rule_negations import _parent

    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--award-signals-all-languages" in result.stdout
    assert "--no-award-signals-all-languages" in result.stdout
    assert live.NEGATABLE_RULES["award-signals-all-languages"] == (
        ("app.adapters.page_classifier", "AWARD_SIGNALS_ALL_LANGUAGES"),
    )
    assert "award-signals-all-languages" not in live.DEFAULT_OFF_NEGATABLE  # on since 2026-10-20
    commands = _parent(monkeypatch, tmp_path, "--award-signals-all-languages")
    assert "--award-signals-all-languages" in commands[0]


def test_the_child_switches_the_rule_on(tmp_path, monkeypatch) -> None:
    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        seen["on"] = page_classifier.AWARD_SIGNALS_ALL_LANGUAGES

    monkeypatch.setattr(page_classifier, "AWARD_SIGNALS_ALL_LANGUAGES", False)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "uio", "--out", str(tmp_path / "uio.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--award-signals-all-languages"])
    live.main()
    assert seen == {"on": True}
