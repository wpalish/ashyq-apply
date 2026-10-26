"""AW-2: the award-page words of every language ``languages.json`` names.

The award-page classifier (``page_classifier``'s funding branch) decides
"award page" from English words only: the funding nouns of
``_SCHOLARSHIP_WORD``, the plural listing heading, the news markers and the six
``_AWARD_SIGNALS``. A German award page that states its monthly amount, its
target group and its application route in German finds none of them and is
refused as "not an award page" (REACH_ROWS_2026-10-20, AW-1 step 1: dev4).

This module holds one row per language, read only under the page's own
``<html lang>`` and only while ``page_classifier.AWARD_SIGNALS_ALL_LANGUAGES``
is on. Every word comes from the dictionary or the official terminology cited
in the row's ``source`` (the higher-education law or the national funding
body's term for the thing), never from a site: no word was taken from a
university page, and no site list is involved. English stays where it is;
these rows only add.

Fields, each a regular expression matched case-insensitively:

- ``noun``: the scholarship / grant / bursary nouns (the funding gate, the
  award name and the award-link count, like ``_SCHOLARSHIP_WORD``);
- ``listing``: a heading that is the plural category, so the page is a list of
  awards (like ``_PLURAL_FUNDING_HEADING``); anchored with ``^…$``;
- ``process``: a heading about applying for awards, or their FAQ, which is not
  one award's name (a "how to apply for a scholarship" page);
- ``news``: news and press-release words in the title or first heading (like
  ``_NEWS``). Notice and announcement words are left out on purpose: local
  award calls are published as notices (Chinese 通知, Turkish duyuru, Italian
  avviso), so refusing them would refuse the award itself;
- ``amount``, ``coverage``, ``eligibility``, ``application``, ``deadline``: the
  substantive signals, under the names of ``_AWARD_SIGNALS`` (coverage carries
  the tuition-waiver and tuition words, as the English ``coverage`` signal
  carries "tuition"). No row adds a ``duration`` signal.

Languages written without spaces (ja, zh, ko particles, th) are matched
without word boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache

#: The signal names a row may add to, in ``_AWARD_SIGNALS`` order.
SIGNAL_NAMES: tuple[str, ...] = ("amount", "coverage", "eligibility", "application", "deadline")


@dataclass(frozen=True)
class AwardWords:
    """One language's award-page words (regular-expression sources)."""

    noun: str
    listing: str
    process: str
    news: str
    amount: str
    coverage: str
    eligibility: str
    application: str
    deadline: str
    source: str

    def signal_sources(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in SIGNAL_NAMES}


@dataclass(frozen=True)
class CompiledAwardWords:
    noun: re.Pattern[str]
    listing: re.Pattern[str]
    process: re.Pattern[str]
    news: re.Pattern[str]
    signals: dict[str, re.Pattern[str]]


def _listing(plural: str, connectors: str | None) -> str:
    """A plural category heading, optionally with a scope phrase, as English has."""
    if connectors is None:
        # Case languages put the scope in an inflected word, not a preposition.
        return rf"^\s*(?:{plural})(?:\s+.{{0,60}})?\s*$"
    return rf"^\s*(?:{plural})(?:\s+(?:{connectors})\s+.{{0,60}})?\s*$"


_NORWEGIAN_BOKMAL = AwardWords(
    noun=r"stipend\w*|\blegat\w*",
    listing=_listing(
        r"stipender|legater|stipender og legater|legater og stipender", "og|til|for|på|i|fra"
    ),
    process=r"^\s*(?:slik søker du|søknad\b|søk\b|ofte stilte spørsmål|informasjon om)",
    news=r"\b(?:nyheter|nyhet|pressemelding\w*)\b",
    amount=r"\bbeløp\w*|\bpr\.? (?:måned|år|semester)\b|\bi måneden\b|\bmånedlig\w*|\bkroner\b",
    coverage=r"\bfritak\w*|\bstudieavgift\w*|\bskolepenger\b|\bsemesteravgift\w*|\blevekostnader\b|\bdekker\b",
    eligibility=r"\bvilkår\w*|\bkrav\b|\bkriteri\w*|\bkan søke\b|\bberettiget\b|\bmålgruppe\w*|\bhvem kan søke",
    application=r"\bsøknad(?:en|er|ene|sskjema)?\b|\bslik søker du\b|\bsøk (?:om|her)\b",
    deadline=r"\bsøknadsfrist\w*|\bfrist\w*|\bsenest\b",
    source=(
        "Bokmålsordboka (Språkrådet/UiB) s.v. stipend, legat, søknad, søknadsfrist, vilkår, beløp, fritak; "
        "Forskrift om studieavgift (2023) (studieavgift, fritak)"
    ),
)

DICTIONARY: dict[str, AwardWords] = {
    "ca": AwardWords(
        noun=r"\bbec(?:a|ues)\b|\bajuts?\s+(?:a\s+l['’]estudi|econ[òo]mics?)",
        listing=_listing(r"beques|beques i ajuts|ajuts a l['’]estudi", "i|per a|per|de|a"),
        process=(
            r"^\s*(?:com sol[·.]?licitar|sol[·.]?licitud\b|preguntes freq[üu]ents"
            r"|informaci[óo] sobre)"
        ),
        news=r"\b(?:not[íi]ci(?:a|es)|actualitat|comunicats? de premsa)\b",
        amount=r"\bimport\b|\bquantia\b|\bdotaci[óo]\b|\bper (?:mes|any|curs)\b|\bmensual\w*",
        coverage=(
            r"\bexempci[óo]\w*|\bmatr[íi]cula\b|\btaxes acad[èe]miques\b|\ballotjament\b"
            r"|\bdespeses de manutenci[óo]\b|\bcobreix\w*"
        ),
        eligibility=(
            r"\brequisits?\b|\bdestinataris?\b|\bbeneficiaris?\b|\bqui (?:pot|en pot) sol[·.]?licitar"
            r"|\bcriteris? d['’](?:adjudicaci[óo]|avaluaci[óo])"
        ),
        application=(
            r"\bsol[·.]?licitud\w*|\bcom sol[·.]?licitar|\bpresentaci[óo] de sol[·.]?licituds"
            r"|\bconvocat[òo]ria\b"
        ),
        deadline=r"\btermini\b|\bdata l[íi]mit\b|\bfins al? \d|\bdata de tancament\b",
        source=(
            "DIEC2 (Institut d'Estudis Catalans) s.v. beca, ajut, import, quantia, requisit, "
            "sol·licitud, termini, exempció, matrícula"
        ),
    ),
    "cs": AwardWords(
        noun=r"\bstipendi\w*|\bgrant(?:y|u|ů)?\b",
        listing=_listing(
            r"stipendia|granty|stipendia a granty|stipendijní programy?", "a|pro|na|ve?|ze?|od"
        ),
        process=(
            r"^\s*(?:jak (?:se )?(?:přihlásit|podat|žádat)|podání žádosti|žádost o\b|přihláška\b"
            r"|časté dotazy|nejčastější dotazy|informace o\b)"
        ),
        news=r"\b(?:aktuality|aktualita|zprávy|novinky|tisková zpráva)\b",
        amount=r"\bvýše\b|\bvýši\b|\bčástk\w*|\bměsíčně\b|\bza měsíc\b|\bročně\b",
        coverage=(
            r"\bprominutí\b|\bosvobozen\w*|\bškolné\w*|\bpoplat\w* za studium|\bubytování\b"
            r"|\bživotní náklady"
        ),
        eligibility=(
            r"\bpodmínk\w*|\bnárok\w*|\bmohou (?:se )?(?:ucházet|žádat|přihlásit)|\bkritéri\w*"
            r"|\burčen\w* pro\b"
        ),
        application=r"\bžádost\w*|\bpřihlášk\w*|\bjak (?:se )?(?:přihlásit|žádat|podat)",
        deadline=r"\buzávěrk\w*|\btermín\w* (?:podání|pro podání)|\blhůt\w*|\bnejpozději do\b",
        source=(
            "Internetová jazyková příručka (ÚJČ AV ČR) / SSJČ s.v. stipendium, grant, výše, "
            "podmínka, žádost, uzávěrka; Act No. 111/1998 Coll. §58 (prominutí poplatku), §91 (stipendia)"
        ),
    ),
    "da": AwardWords(
        noun=r"stipendi\w*|\blegat\w*|\bfriplads\w*",
        listing=_listing(
            r"stipendier|legater|stipendier og legater|legater og stipendier|fripladser og stipendier",
            "og|til|for|på|i|fra",
        ),
        process=r"^\s*(?:sådan søger du|ansøgning\b|ansøg\b|søg\b|ofte stillede spørgsmål|information om)",
        news=r"\b(?:nyheder|nyhed|pressemeddelelse\w*)\b",
        amount=r"\bbeløb\w*|\bpr\.? (?:måned|år|semester)\b|\bom (?:måneden|året)\b|\bmånedlig\w*|\bdkk\b",
        coverage=r"\bfriplads\w*|\bstudieafgift\w*|\bstudiegebyr\w*|\bleveomkostninger\b|\bdækker\b",
        eligibility=(
            r"\bbetingelse\w*|\bkrav\b|\bkriteri\w*|\bkan søge\b|\bberettiget\b|\bmålgruppe\w*"
            r"|\bhvem kan søge"
        ),
        application=r"\bansøgning(?:en|er|erne|sskema)?\b|\bsådan søger du\b|\bsøg (?:om|her)\b",
        deadline=r"\bansøgningsfrist\w*|\bfrist\w*|\bsenest\b",
        source=(
            "Den Danske Ordbog (DSL) s.v. stipendium, legat, ansøgning, ansøgningsfrist, beløb, betingelse; "
            "Bekendtgørelse om fripladser og stipendier (friplads, stipendium, studieafgift)"
        ),
    ),
    "de": AwardWords(
        noun=r"stipendi\w*|\bstudienbeihilfe\w*|\bstudienförderung\b",
        listing=_listing(
            r"stipendien|stipendien und (?:förderung|preise|förderprogramme)|förderprogramme"
            r"|stipendienprogramme",
            "und|für|an|der|des|im|in|von|zur|zum",
        ),
        process=(
            r"^\s*(?:bewerbung\b|so bewerben sie sich|wie bewerbe ich mich|bewerben\b|häufige fragen"
            r"|häufig gestellte fragen|informationen (?:zu|zum|zur|über)\b)"
        ),
        news=r"\b(?:aktuelles|neuigkeiten|nachrichten|pressemitteilung(?:en)?)\b",
        amount=(
            r"\bhöhe\b|\bbeträgt\b|\bmonatlich\w*|\bpro (?:monat|semester|jahr)\b"
            r"|\bförder(?:betrag|summe|höhe)\w*|\bstipendienhöhe\b"
        ),
        coverage=(
            r"\bstudiengebühr\w*|\bgebühren(?:befreiung|erlass)\w*|\bbefreiung von\b|\bsemesterbeitr\w*"
            r"|\blebenshaltungskosten\b|\bunterkunft\b|\bwohnheim\w*"
        ),
        eligibility=(
            r"\bvoraussetzung\w*|\bbewerbungsvoraussetzung\w*|\bbewerben können sich\b|\bzielgruppe\w*"
            r"|\b(?:auswahl|förder)kriteri\w*|\bberechtigt\w*|\bwer kann sich bewerben|\bförderfähig\w*"
        ),
        application=(
            r"\bbewerbung\b|\bbewerbungsverfahren\b|\bbewerbungsunterlagen\b|\bbewerben sie sich\b"
            r"|\bso bewerben\b|\bantrag(?:stellung)?\b|\bonline-bewerbung\b"
        ),
        deadline=r"\bbewerbungs(?:frist|schluss|zeitraum)\w*|\bantragsfrist\w*|\beinsendeschluss\b|\bstichtag\w*|\bfrist\w*",
        source=(
            "Duden s.v. Stipendium, Studienbeihilfe, Höhe, Voraussetzung, Bewerbung, Bewerbungsfrist, "
            "Gebührenbefreiung; Stipendienprogramm-Gesetz (StipG) §§ 3-5 (Höhe, monatlich, Bewerbung, "
            "Auswahlkriterien); Studienförderungsgesetz 1992, AT (Studienbeihilfe)"
        ),
    ),
    "es": AwardWords(
        noun=r"\bbecas?\b|\bayudas? (?:al estudio|económicas?|para el estudio)",
        listing=_listing(
            r"becas|becas y ayudas(?: al estudio)?|ayudas al estudio|apoyos? económicos?|becas y apoyos",
            "y|para|de|del|a|al|en",
        ),
        process=(
            r"^\s*(?:cómo (?:solicitar|postular|aplicar)|solicitud de\b|solicitar\b|postulación\b"
            r"|preguntas frecuentes|información sobre)"
        ),
        news=r"\b(?:noticias?|comunicados? de prensa|sala de prensa|actualidad)\b",
        amount=r"\bcuantía\w*|\bimporte\b|\bmonto\b|\bal mes\b|\bmensual\w*|\bpor (?:mes|año|semestre)\b|\bporcentaje\b",
        coverage=(
            r"\bexenci[óo]n\w*|\bmatrícula\b|\bcolegiatura\w*|\bdescuento\w*|\balojamiento\b"
            r"|\bmanutención\b|\bcubre\b|\bcobertura\b"
        ),
        eligibility=(
            r"\brequisitos?\b|\bpueden (?:solicitar|postular)|\bdirigida a\b|\bdestinatari\w*"
            r"|\bbeneficiari\w*|\bcriterios?\b|\bquién puede (?:solicitar|postular)"
        ),
        application=(
            r"\bsolicitud\w*|\bcómo (?:solicitar|postular|aplicar)|\bpostulaci[óo]n\w*|\bconvocatoria\w*"
        ),
        deadline=r"\bplazo\w*|\bfecha límite\b|\bfecha de cierre\b|\bhasta el \d|\bcierre de (?:la )?convocatoria",
        source=(
            "RAE, Diccionario de la lengua española s.v. beca, ayuda, cuantía, requisito, solicitud, plazo, "
            "exención, matrícula; Real Decreto 1721/2007 (becas y ayudas al estudio: cuantías, requisitos, "
            "solicitudes, plazos)"
        ),
    ),
    "et": AwardWords(
        noun=r"stipendi\w*|\bõppetoetus\w*",
        listing=_listing(
            r"stipendiumid|stipendiumid ja toetused|toetused ja stipendiumid|õppetoetused", None
        ),
        process=(
            r"^\s*(?:kuidas taotleda|taotlemine\b|taotlus\b|kandideerimine\b"
            r"|korduma kippuvad küsimused|kkk\b)"
        ),
        news=r"\b(?:uudised|uudis|pressiteade\w*)\b",
        amount=r"\bsumm\w*|\bsuurus\w*|\bsuurune\b|\bigakuu\w*|\beurot? kuus\b",
        coverage=r"\bõppetasu\w*|\bvabastus\w*|\bvabasta\w*|\bmajutus\w*|\belamiskulu\w*|\bkatab\b",
        eligibility=r"\btingimus\w*|\bnõuded\b|\bnõue\b|\bkriteeri\w*|\bsaavad taotleda|\bkes saab taotleda",
        application=r"\btaotle\w*|\btaotlus\w*|\bkandideeri\w*",
        deadline=r"\btähtaeg\w*|\btähtaja\w*|\bhiljemalt\b|\btaotlusvoor\w*",
        source=(
            "EKSS (Eesti keele seletav sõnaraamat, EKI) s.v. stipendium, toetus, summa, tingimus, taotlus, "
            "tähtaeg; Õppetoetuste ja õppelaenu seadus (õppetoetus, stipendium); Kõrgharidusseadus (õppetasu)"
        ),
    ),
    "fi": AwardWords(
        noun=r"\bapura\w*|stipendi\w*",
        listing=_listing(r"apurahat|stipendit|apurahat ja stipendit|stipendit ja apurahat", None),
        process=(
            r"^\s*(?:näin haet|hakeminen\b|haku\b|hae\b|usein kysyttyä|usein kysytyt kysymykset)"
        ),
        news=r"\b(?:uutiset|uutinen|tiedote|tiedotteet|ajankohtaista)\b",
        amount=r"\bsuuruu\w*|\bmäärä\w*|\bkuukaudessa\b|\bvuodessa\b|\bkuukausittain\b|\beuroa\b",
        coverage=r"\blukuvuosimaksu\w*|\bvapautu\w*|\bmaksuvapau\w*|\basum\w*|\belinkustannu\w*|\bkattaa\b",
        eligibility=(
            r"\bhakukelpoi\w*|\bkelpoisuu\w*|\bedellytyk\w*|\bkriteer\w*|\bvoi hakea\b|\bkuka voi hakea"
            r"|\bkohderyhm\w*"
        ),
        application=r"\bhakemu\w*|\bnäin haet\b|\bhakeminen\b|\bhaku\b",
        deadline=r"\bhakuaika\w*|\bhakuajan\b|\bmääräai\w*|\bviimeistään\b|\bhaku päättyy",
        source=(
            "Kielitoimiston sanakirja (Kotus) s.v. apuraha, stipendi, määrä, hakukelpoisuus, hakemus, hakuaika, "
            "määräaika; Yliopistolaki 558/2009 §10 a (lukuvuosimaksu, apurahajärjestelmä)"
        ),
    ),
    "fr": AwardWords(
        noun=r"\bbourses?\b|\baides? financières?|\ballocations? (?:d['’]études|de mobilité)",
        listing=_listing(
            r"bourses|bourses et aides(?: financières)?|aides financières|financements?",
            "et|pour|de|des|du|aux?|en",
        ),
        process=(
            r"^\s*(?:comment (?:candidater|postuler|faire une demande|déposer)|candidature\b|candidater\b"
            r"|postuler\b|faire une demande|demande de\b|foire aux questions|questions fréquentes"
            r"|informations sur)"
        ),
        news=r"\b(?:actualités?|communiqués? de presse)\b",
        amount=r"\bmontant\w*|\bs['’]élève à\b|\bpar (?:mois|an)\b|\bmensuel\w*|\bvaleur\b",
        coverage=(
            r"\bexonération\w*|\bfrais (?:d['’]inscription|de scolarité)|\bdroits d['’]inscription"
            r"|\blogement\b|\bfrais de vie\b|\bcouvre\w*|\bprise en charge\b"
        ),
        eligibility=(
            r"\béligib\w*|\bconditions d['’](?:attribution|éligibilité|accès)|\bcritères?\b"
            r"|\bbénéficiaires?\b|\bqui peut (?:candidater|postuler|en bénéficier)|\bpublic concerné\b"
        ),
        application=(
            r"\bcandidature\w*|\bcomment (?:candidater|postuler)|\bdossier de candidature"
            r"|\bdéposer (?:un|votre) dossier|\bfaire une demande"
        ),
        deadline=r"\bdate limite\b|\bdate de clôture\b|\bclôture des candidatures\b|\bavant le \d|\bjusqu['’]au \d",
        source=(
            "Larousse / TLFi s.v. bourse, aide, montant, éligible, critère, candidature, date limite, "
            "exonération; Code de l'éducation art. R719-49 et R719-50 (exonération des droits d'inscription)"
        ),
    ),
    "it": AwardWords(
        noun=r"\bbors[ae](?: di studio)?\b|\bcontribut[oi] (?:di|per lo) studio|\bpremi[oi] di studio",
        listing=_listing(
            r"borse di studio|borse di studio e (?:premi|agevolazioni|contributi)|agevolazioni economiche"
            r"|benefici economici",
            "e|per|di|del|della|dei|degli|a|ai|agli|in",
        ),
        process=(
            r"^\s*(?:come (?:fare domanda|presentare (?:la )?domanda|candidarsi)|domanda di\b"
            r"|presentazione della domanda|candidatura\b|domande frequenti|informazioni su)"
        ),
        news=r"\b(?:notizie|notizia|comunicat[oi] stampa)\b",
        amount=r"\bimport[oi]\b|\bammontare\b|\bpari a\b|\b(?:al|per) (?:mese|anno)\b|\bmensil\w*|\bvalore\b",
        coverage=(
            r"\besoner\w*|\btasse universitarie\b|\bcontribuzione studentesca\b|\bcontributo onnicomprensivo\b"
            r"|\balloggio\b|\bcopr\w*|\bvitto\b"
        ),
        eligibility=(
            r"\brequisit\w*|\bpossono (?:partecipare|presentare|candidarsi)|\bdestinatar\w*|\bbeneficiar\w*"
            r"|\bcriteri\b|\bammissibil\w*|\bchi può (?:partecipare|candidarsi|presentare)"
        ),
        application=(
            r"\bdomanda\b|\bcandidatur\w*|\bcome (?:fare domanda|candidarsi|presentare)|\bbando\b"
            r"|\bpresentazione delle domande"
        ),
        deadline=r"\bscadenz\w*|\bentro il \d|\btermine\b|\bdata di chiusura\b",
        source=(
            "Treccani, Vocabolario s.v. borsa (di studio), importo, requisito, domanda, bando, scadenza, "
            "esonero; D.Lgs. 68/2012 (diritto allo studio: borse di studio, esonero dalle tasse)"
        ),
    ),
    "ja": AwardWords(
        noun=r"奨学金|奨学生|授業料免除",
        listing=(
            r"^\s*(?:奨学金|奨学金制度|奨学金一覧|奨学金情報|奨学金・授業料免除|授業料免除・奨学金"
            r"|経済支援|経済的支援)\s*$"
        ),
        process=r"申請方法|応募方法|申込方法|よくある質問",
        news=r"ニュース|プレスリリース|新着情報",
        amount=r"支給額|給付額|金額|月額|年額|万円",
        coverage=r"授業料|免除|減免|入学金|生活費",
        eligibility=r"応募資格|申請資格|対象者|資格要件|要件|条件|選考基準",
        application=r"申請|応募|申込|出願|推薦",
        deadline=r"締切|締め切り|〆切|期限|期日|募集期間",
        source=(
            "Kōjien (広辞苑) s.v. 奨学金, 支給, 資格, 申請, 締切, 免除; JASSO/MEXT terminology "
            "(給付型奨学金, 授業料免除, 応募資格)"
        ),
    ),
    "kk": AwardWords(
        noun=r"шәкіртақы\w*|\bгрант\w*|стипенди\w*",
        listing=_listing(
            r"шәкіртақылар|гранттар|стипендиялар|шәкіртақылар мен гранттар|гранттар мен шәкіртақылар",
            None,
        ),
        # Kazakh puts the object first ("Шәкіртақыға өтінім беру"), so the phrase is found anywhere.
        process=r"қалай (?:өтінім|тапсыру)|өтінім беру|құжат қабылдау|жиі қойылатын сұрақтар",
        news=r"\b(?:жаңалықтар|жаңалық)\b",
        amount=r"\bмөлшер\w*|\bсома\w*|\bайына\b|\bай сайын\b|\bжылына\b|\bтеңге\b",
        coverage=r"\bоқу ақы\w*|\bбосат\w*|\bжеңілдік\w*|\bжатақхана\w*|\bөтейді\b",
        eligibility=r"\bталап\w*|\bшарттар\w*|\bшарты\b|\bкритери\w*|\bүміткер\w*",
        application=r"\bөтінім\w*|\bқұжат қабылда\w*|\bқалай тапсыру",
        deadline=r"\bмерзім\w*|\bсоңғы күн\w*",
        source=(
            "Қазақ әдеби тілінің сөздігі (15 т., А. Байтұрсынұлы атындағы Тіл білімі институты) s.v. "
            "шәкіртақы, грант, мөлшер, талап, өтінім, мерзім; RK Law On Education art. 1 (білім беру гранты)"
        ),
    ),
    "ko": AwardWords(
        noun=r"장학",
        listing=r"^\s*(?:장학금|장학제도|장학 제도|장학 안내|장학금 안내|장학금 종류)\s*$",
        process=r"신청 ?방법|지원 ?방법|자주 묻는 질문",
        news=r"뉴스|보도자료|소식",
        amount=r"금액|지급액|매월|연간|만 ?원",
        coverage=r"등록금|수업료|감면|면제|기숙사|생활비",
        eligibility=r"자격|대상|요건|조건|기준",
        application=r"신청|접수|추천",
        deadline=r"마감|기한",
        source=(
            "표준국어대사전 (NIKL) s.v. 장학금, 금액, 자격, 신청, 마감, 감면; Korea Student Aid Foundation "
            "terminology (장학금, 등록금 감면, 신청 자격)"
        ),
    ),
    "lt": AwardWords(
        noun=r"stipendij\w*",
        listing=_listing(r"stipendijos|stipendijos ir (?:parama|išmokos)", None),
        process=(
            r"^\s*(?:kaip (?:pateikti|kreiptis|teikti)|paraiškų teikimas|paraiška\b|prašymas\b"
            r"|dažnai užduodami klausimai|duk\b|informacija apie)"
        ),
        news=r"\b(?:naujienos|naujiena|pranešimai? spaudai)\b",
        amount=r"\bdyd\w*|\bsum(?:a|os)\b|\bper mėnesį\b|\bkas mėnesį\b|\bmėnesin\w*|\beurų\b",
        coverage=(
            r"\bstudijų kain\w*|\batleid\w*|\bkompensuoj\w*|\bapgyvendin\w*|\bbendrabut\w*"
            r"|\bpragyvenimo išlaid\w*|\bpadengia\b"
        ),
        eligibility=r"\breikalavim\w*|\bsąlyg\w*|\bkriterij\w*|\bgali (?:teikti|pretenduoti|kreiptis)|\bpretendent\w*",
        application=r"\bparaišk\w*|\bprašym\w*|\bkaip (?:pateikti|kreiptis|teikti)",
        deadline=r"\bterminas\b|\btermino\b|\biki \d|\bpaskutinė diena\b|\bne vėliau kaip\b",
        source=(
            "Dabartinės lietuvių kalbos žodynas (LKI) s.v. stipendija, dydis, reikalavimas, paraiška, terminas, "
            "atleisti; Mokslo ir studijų įstatymas art. 70 (studijų kaina), art. 82 (stipendijos)"
        ),
    ),
    "nb": _NORWEGIAN_BOKMAL,
    "nl": AwardWords(
        noun=r"beurs|beurzen",
        listing=_listing(
            r"beurzen|studiebeurzen|beurzen en (?:subsidies|financiering|toelagen)",
            "en|voor|van|aan|bij|in",
        ),
        process=(
            r"^\s*(?:hoe (?:vraag|meld) (?:je|ik|u)|aanvragen\b|aanmelden\b|veel ?gestelde vragen"
            r"|informatie over)"
        ),
        news=r"\b(?:nieuws|nieuwsbericht|persbericht|actueel)\b",
        amount=r"\bbedrag\w*|\bhoogte\b|\bper (?:maand|jaar)\b|\bmaandelijks\b",
        coverage=r"\bcollegegeld\w*|\bvrijstelling\w*|\bhuisvesting\b|\blevensonderhoud\b",
        eligibility=(
            r"\bvoorwaarden\b|\btoelatingseisen\b|\bin aanmerking\b|\bcriteria\b"
            r"|\bwie kan (?:aanvragen|zich aanmelden)|\bdoelgroep\w*"
        ),
        application=r"\baanvra\w*|\bhoe vraag (?:je|ik|u)",
        deadline=r"\bdeadline\b|\bsluitingsdatum\b|\buiterlijk\b|\baanvraagtermijn\b|\btermijn\b",
        source=(
            "Van Dale s.v. beurs, studiebeurs, bedrag, voorwaarde, aanvragen, sluitingsdatum, vrijstelling; "
            "WHW art. 7.45a-7.48 (collegegeld); Nuffic terminology (beurs, Holland Scholarship)"
        ),
    ),
    "nn": AwardWords(
        noun=r"stipend\w*|\blegat\w*",
        listing=_listing(r"stipend|legat|stipend og legat|legat og stipend", "og|til|for|på|i|frå"),
        process=r"^\s*(?:slik søkjer du|søknad\b|søk\b|ofte stilte spørsmål|informasjon om)",
        news=r"\b(?:nyheiter|nyheit|pressemelding\w*)\b",
        amount=r"\bbeløp\w*|\bpr\.? (?:månad|år|semester)\b|\bi månaden\b|\bmånadleg\w*|\bkroner\b",
        coverage=r"\bfritak\w*|\bstudieavgift\w*|\bskulepengar\b|\bsemesteravgift\w*|\blevekostnader\b|\bdekkjer\b",
        eligibility=r"\bvilkår\w*|\bkrav\b|\bkriteri\w*|\bkan søkje\b|\bkven kan søkje|\bmålgruppe\w*",
        application=r"\bsøknad(?:en|er|ene|sskjema)?\b|\bslik søkjer du\b|\bsøk (?:om|her)\b",
        deadline=r"\bsøknadsfrist\w*|\bfrist\w*|\bseinast\b",
        source=(
            "Nynorskordboka (Språkrådet/UiB) s.v. stipend, legat, søknad, søknadsfrist, vilkår, beløp, "
            "fritak; Forskrift om studieavgift (2023)"
        ),
    ),
    "no": _NORWEGIAN_BOKMAL,
    "pl": AwardWords(
        noun=r"\bstypendi\w*|\bgrant(?:y|u|ów)?\b",
        listing=_listing(
            r"stypendia|granty|stypendia i granty|stypendia i zapomogi|programy stypendialne",
            "i|dla|na|we?|ze?|od",
        ),
        process=(
            r"^\s*(?:jak (?:złożyć|aplikować|się ubiegać)|składanie wniosków|wniosek o\b"
            r"|najczęściej zadawane pytania|informacje o\b)"
        ),
        news=r"\b(?:aktualności|aktualność|wiadomości|komunikaty? prasowy|informacja prasowa)\b",
        amount=r"\bkwot\w*|\bwysokoś\w*|\bzł\b|\bmiesięcznie\b|\bna miesiąc\b|\brocznie\b",
        coverage=(
            r"\bzwolnieni\w*|\bczesne\w*|\bopłat\w* za (?:studia|kształcenie)|\bzakwaterowani\w*"
            r"|\bkoszty utrzymania\b"
        ),
        eligibility=r"\bwarunk\w*|\buprawni\w*|\bkryteri\w*|\bmogą (?:się )?ubiegać|\bdla kogo\b|\bwymagani\w*",
        application=r"\bwniosk\w*|\bwniosek\b|\bjak (?:złożyć|aplikować|się ubiegać)|\bskładani\w*",
        deadline=r"\btermin\w* (?:składania|na złożenie)|\bostateczny termin\b|\bdo dnia\b|\bnieprzekraczaln\w*",
        source=(
            "Słownik języka polskiego PWN s.v. stypendium, grant, kwota, wysokość, warunek, wniosek, termin, "
            "zwolnienie; Act of 20 July 2018 art. 79 (zwolnienie z opłat), art. 86 (stypendia)"
        ),
    ),
    "pt": AwardWords(
        noun=r"\bbolsas?\b|\bauxílios? (?:estudantil|financeiro)",
        listing=_listing(
            r"bolsas(?: de estudo)?|bolsas e (?:apoios|auxílios|benefícios)|apoios sociais|auxílios estudantis",
            "e|para|de|do|da|dos|das|a|ao|aos|em",
        ),
        process=(
            r"^\s*(?:como (?:candidatar|se candidatar|solicitar|se inscrever)|candidatura\b|inscrição\b"
            r"|inscrições\b|pedido de\b|perguntas frequentes|informações sobre)"
        ),
        news=r"\b(?:notícias?|comunicados? de imprensa|novidades)\b",
        amount=r"\bvalor\b|\bmontante\b|\bpor (?:mês|ano|semestre)\b|\bmensa(?:l|is)\b",
        coverage=(
            r"\bisenç\w*|\bpropinas?\b|\bmensalidades?\b|\bintegral\b|\bparcial\b|\balojamento\b"
            r"|\bmoradia\b|\bcobre\b|\bcobertura\b"
        ),
        eligibility=(
            r"\brequisitos?\b|\bcondições de (?:acesso|elegibilidade|candidatura)|\belegib\w*"
            r"|\bpodem candidatar|\bdestinatári\w*|\bbeneficiári\w*|\bcritérios?\b"
            r"|\bquem pode (?:candidatar|se candidatar|solicitar)"
        ),
        application=r"\bcandidatura\w*|\bcomo (?:candidatar|se candidatar|solicitar|se inscrever)|\binscriç\w*|\bedital\b",
        deadline=r"\bprazo\w*|\bdata[- ]limite\b|\baté (?:o dia|ao dia|\d)|\bencerramento\b",
        source=(
            "Dicionário Houaiss / Priberam s.v. bolsa (de estudo), valor, montante, requisito, candidatura, "
            "prazo, isenção, propina; Despacho 8442-A/2012 (Regulamento de Atribuição de Bolsas de Estudo, DGES)"
        ),
    ),
    "ru": AwardWords(
        noun=r"стипенди\w*|\bгрант\w*",
        listing=_listing(
            r"стипендии|гранты|стипендии и гранты|гранты и стипендии|стипендиальные программы",
            "и|для|на|в|от|по",
        ),
        process=(
            r"^\s*(?:как (?:подать|получить|оформить)|подача (?:заявок|заявлений|документов)"
            r"|заявка на\b|заявление на\b|часто задаваемые вопросы|вопросы и ответы|информация о\b)"
        ),
        news=r"\b(?:новости|новость|пресс-релиз\w*)\b",
        amount=r"\bразмер\w*|\bсумм\w*|\bв месяц\b|\bежемесячн\w*|\bв год\b|\bрублей\b",
        coverage=(
            r"\bосвобожд\w*|\bскидк\w*|\bоплат\w* обучения|\bстоимост\w* обучения|\bпроживани\w*"
            r"|\bобщежити\w*|\bпокрывает\b"
        ),
        eligibility=(
            r"\bтребовани\w*|\bусловия\b|\bкритери\w*|\bмогут (?:претендовать|подать|получить)"
            r"|\bкто может\b|\bпретендент\w*|\bправо на получение"
        ),
        application=r"\bзаявк\w*|\bзаявлени\w*|\bкак (?:подать|получить|оформить)",
        deadline=r"\bсрок\w* (?:подачи|при[её]ма)|\bдедлайн\w*|\bне позднее\b|\bпри[её]м заявок\b",
        source=(
            "Ozhegov / Большой толковый словарь (БТС) s.v. стипендия, грант, размер, требование, заявка, срок, "
            "освобождение; Federal Law 273-FZ art. 36 (стипендии)"
        ),
    ),
    "sk": AwardWords(
        noun=r"\bštipendi\w*|\bgrant(?:y|u|ov)?\b",
        listing=_listing(
            r"štipendiá|granty|štipendiá a granty|štipendijné programy?", "a|pre|na|vo?|zo?|od"
        ),
        process=(
            r"^\s*(?:ako (?:sa )?(?:prihlásiť|podať|žiadať)|podanie žiadosti|žiados[tť] o\b|prihláška\b"
            r"|často kladené otázky|časté otázky|informácie o\b)"
        ),
        news=r"\b(?:aktuality|aktualita|správy|novinky|tlačová správa)\b",
        amount=r"\bvýšk\w*|\bsum[ayu]\b|\bmesačne\b|\bza mesiac\b|\bročne\b",
        coverage=r"\bodpusten\w*|\bosloboden\w*|\bškolné\w*|\bubytovan\w*|\bživotné náklady",
        eligibility=(
            r"\bpodmienk\w*|\bnárok\w*|\bmôžu (?:sa )?(?:uchádzať|žiadať|prihlásiť)|\bkritéri\w*"
            r"|\burčen\w* pre\b"
        ),
        application=r"\bžiados[tť]\w*|\bprihlášk\w*|\bako (?:sa )?(?:prihlásiť|žiadať|podať)",
        deadline=r"\buzávierk\w*|\btermín\w* (?:podania|na podanie)|\blehot\w*|\bnajneskôr do\b",
        source=(
            "Slovník súčasného slovenského jazyka (JÚĽŠ SAV) s.v. štipendium, grant, výška, podmienka, "
            "žiadosť, uzávierka; Act No. 131/2002 Coll. §92 (školné, odpustenie), §96 (štipendiá)"
        ),
    ),
    "sv": AwardWords(
        noun=r"stipendi\w*",
        listing=_listing(
            r"stipendier|stipendier och (?:bidrag|fonder|priser)|fonder och stipendier",
            "och|för|till|vid|på|i|från",
        ),
        process=r"^\s*(?:så (?:ansöker|söker) du|ansökan\b|ansök\b|sök\b|vanliga frågor|information om)",
        news=r"\b(?:nyheter|nyhet|pressmeddelande\w*)\b",
        amount=r"\bbelopp\w*|\bper (?:månad|år|termin)\b|\bi månaden\b|\bmånatlig\w*|\bkronor\b",
        coverage=r"\bstudieavgift\w*|\bavgiftsbefri\w*|\bbefrielse\b|\blevnadskostnader\b|\btäcker\b",
        eligibility=r"\bvillkor\w*|\bbehörig\w*|\bkrav\b|\bkriteri\w*|\bkan söka\b|\bvem kan söka|\bmålgrupp\w*",
        application=r"\bansökan\b|\bansök\b|\bså (?:ansöker|söker) du\b|\bansökningsformulär\w*",
        deadline=r"\bsista ansökningsdag\w*|\bansökningsperiod\w*|\bsista dag\b|\bsenast\b",
        source=(
            "Svensk ordbok (Svenska Akademien) s.v. stipendium, belopp, behörig, villkor, ansökan, studieavgift; "
            "Förordning (2010:543) om anmälningsavgift och studieavgift; Förordning (2013:871) om stipendier"
        ),
    ),
    "th": AwardWords(
        noun=r"ทุนการศึกษา|ทุนเรียน|ยกเว้นค่าเล่าเรียน",
        listing=r"^\s*(?:ทุนการศึกษา|ประเภททุนการศึกษา|ทุนการศึกษาทั้งหมด)\s*$",
        process=r"วิธีการสมัคร|ขั้นตอนการสมัคร|คำถามที่พบบ่อย",
        news=r"ข่าว",
        amount=r"จำนวนเงิน|มูลค่าทุน|ต่อเดือน|ต่อปี|ทุนละ",
        coverage=r"ค่าเล่าเรียน|ค่าธรรมเนียมการศึกษา|ยกเว้น|ค่าที่พัก|ค่าครองชีพ",
        eligibility=r"คุณสมบัติ|เงื่อนไข|เกณฑ์",
        application=r"การสมัคร|ยื่นใบสมัคร|สมัคร",
        deadline=r"ปิดรับ|วันสุดท้าย|ภายในวันที่",
        source=(
            "พจนานุกรม ฉบับราชบัณฑิตยสถาน พ.ศ. 2554 (Royal Institute Dictionary) s.v. ทุน, คุณสมบัติ, สมัคร, "
            "ค่าเล่าเรียน, ยกเว้น"
        ),
    ),
    "tr": AwardWords(
        # Not "bursa": the dative of "burs" is also the city's name.
        noun=r"\bburs(?:u|un|lar\w*|ları\w*|iyer\w*)?\b|\bhibe\w*",
        listing=_listing(
            r"burslar|burs olanakları|burs i\u0307?mk[âa]nları|burslar ve (?:hibeler|destekler)",
            None,
        ),
        process=(
            r"^\s*(?:nasıl başvurulur|başvuru (?:süreci|koşulları|şartları|formu)|başvuru\b"
            r"|burs başvuru\w*|sıkça sorulan sorular|sss\b)"
        ),
        news=r"\b(?:haberler|haber|basın bülteni|basın açıklaması)\b",
        amount=r"\btutar\w*|\bmiktar\w*|\baylık\b|\bher ay\b|\bayda\b|\btl\b",
        coverage=r"\böğrenim ücret\w*|\bmuaf\w*|\bi\u0307?ndirim\w*|\bharç\w*|\bbarınma\b|\bkonaklama\b|\bkarşıla\w*",
        eligibility=r"\bkoşul\w*|\bşart\w*|\bkriter\w*|\bkimler başvurabilir|\bbaşvurabilir\b|\bhak kazan\w*",
        application=(
            r"\bnasıl başvurulur|\bbaşvuru (?:formu|süreci|işlemleri|yöntemi)|\bbaşvurular\b"
            r"|\bbaşvurunuzu\b|\bbaşvuru yap\w*"
        ),
        deadline=r"\bson başvuru\w*|\bbaşvuru tarih\w*|\bson gün\b|\bsüre\w* (?:sonu|bitimi)",
        source=(
            "TDK Güncel Türkçe Sözlük s.v. burs, hibe, tutar, miktar, koşul, başvuru, muafiyet, öğrenim ücreti; "
            "Law No. 2547 art. 46 (öğrenim ücreti), Law No. 5102 (KYK burs)"
        ),
    ),
    "zh": AwardWords(
        noun=r"奖学金|獎學金|助学金|助學金|学费减免|學雜費減免",
        listing=(
            r"^\s*(?:奖学金|獎學金|奖助学金|獎助學金|学生资助|學生資助|资助政策|奖学金一览|獎學金一覽"
            r"|奖学金信息|獎學金資訊)\s*$"
        ),
        process=r"申请指南|申請指南|申请方法|申請方法|申请流程|申請流程|如何申请|如何申請|常见问题|常見問題",
        news=r"新闻|新聞|快讯|快訊|媒体报道|媒體報導",
        amount=r"奖励金额|金额|金額|每月|每年|每人|万元|萬元|奖励标准|獎勵標準|资助标准|資助標準",
        coverage=r"学费|學費|学杂费|學雜費|减免|減免|免除|住宿|生活费|生活費",
        eligibility=r"申请条件|申請條件|申请资格|申請資格|评选条件|評選條件|资格|資格|条件|條件|对象|對象",
        application=r"申请|申請|报名|報名|推荐|推薦",
        deadline=r"截止|期限",
        source=(
            "现代汉语词典 (7th ed.) s.v. 奖学金, 助学金, 金额, 资格, 申请, 截止, 减免; 教育部重編國語辭典 "
            "(traditional forms); MOE 普通高等学校学生资助政策 (奖学金, 助学金, 学费减免)"
        ),
    ),
}


def _compile(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


def award_words(lang: str) -> CompiledAwardWords | None:
    """The compiled row for a page's primary language subtag, or None (English, unknown)."""
    return _compiled((lang or "").strip().lower().split("-")[0])


@cache
def _compiled(primary: str) -> CompiledAwardWords | None:
    row = DICTIONARY.get(primary)
    if row is None:
        return None
    return CompiledAwardWords(
        noun=_compile(row.noun),
        listing=_compile(row.listing),
        process=_compile(row.process),
        news=_compile(row.news),
        signals={name: _compile(source) for name, source in row.signal_sources().items()},
    )
