"""CQ-1: a programme page whose head names a field combination is a related programme.

Gold knockout 2026-10-19 §3, candidate ticket 1. Every knockout guess on the
development sets had a head that names the requested level and subject plus a
qualifier that makes it something else: "… with Second Major in Business",
"Computer Science (JH)". R2 (``SUBJECT_TITLE_SHAPES``) makes "<related field>
and <field>" related for a closed list of related fields; CQ-1 extends the
shapes to the combination markers themselves and to "with"/"and" joined to
any field that is not an alias of the requested subject.

The tables below are written from a dictionary for every language of
``languages.json`` plus English, before any development page was read
(generalisation 16-Q5, the overfitting guard): the same concepts in every
language, no word taken from a page. A trailing ``*`` marks a stem that takes
inflectional endings. Words in ja/zh/ko/th are matched inside the text, the
rest as whole words; table and head are folded alike (accents stripped,
casefolded), as CH-1's unit table is.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.adapters.discovery import live_discovery as _ld
from app.adapters.page_classifier import PageClassification
from app.adapters.search.ontology import country_languages

#: CQ-1: the verdict for a page whose head names a combination, pinned by
#: tests. "page head " makes it an identity refusal (it frees the slot, and
#: R1's local twin read applies); "names a related programme" makes it R2's
#: related verdict, so discovery records the page as a related programme
#: (``DiscoveryTrace.related_programmes``) and R2b reads the field's own page
#: beside it next. ``{}`` is the qualifier as the head spells it, folded.
HEAD_COMBINATION_VERDICT = (
    "page head names a related programme (combination: {}), not a single-subject programme"
)

#: CQ-1: phrases that alone make a programme a combination of fields — joint
#: honours, double/dual degree, double/second major, combined (two-subject)
#: degrees — per language. Left out on purpose: a "joint degree" between two
#: institutions in one subject (es "titulación conjunta", fi
#: "yhteistutkinto"…) is the same subject; German "dual" alone (a
#: work-integrated study form, not a second degree); Italian "interclasse"
#: (a degree in two classes, often one subject); ja/zh/ko/th forms that fold
#: to a prefix of an ordinary word (th "ปริญญาคู่" folds to "ปรญญาค").
_COMBINATION_MARKERS: dict[str, tuple[str, ...]] = {
    "en": (
        "joint honours",
        "joint honors",
        "joint major",
        "jh",
        "double degree",
        "dual degree",
        "double major",
        "dual major",
        "second major",
        "double honours",
        "double honors",
        "combined",
        "concurrent degree",
    ),
    "ca": ("doble grau", "doble titulació", "doble títol", "doble diploma", "estudis simultanis"),
    "cs": ("dvouobor*", "dvojí diplom*", "dvojit* diplom*"),
    "da": (
        "dobbeltuddannelse*",
        "dobbeltgrad*",
        "dobbeltdiplom*",
        "kombinationsuddannelse*",
        "kombinationsbachelor*",
    ),
    "de": (
        "doppelabschluss*",
        "doppelabschlüsse*",
        "doppelstudium",
        "doppelbachelor*",
        "doppel-bachelor*",
        "zwei-fach-bachelor*",
        "zweifach-bachelor*",
        "zweifachbachelor*",
        "zwei-fächer-bachelor*",
        "2-fach-bachelor*",
        "zweitfach*",
        "kombinationsstudiengang*",
        "kombibachelor*",
        "kombi-bachelor*",
    ),
    "es": (
        "doble grado",
        "dobles grados",
        "doble titulación",
        "doble título",
        "doble licenciatura",
        "doble diploma",
        "doble carrera",
        "estudios simultáneos",
        "programa conjunto de estudios oficiales",
        "pceo",
    ),
    "et": ("topeltkraad*", "topeltdiplom*"),
    "fi": ("kaksoistutkin*", "tuplatutkin*"),
    "fr": (
        "double diplôme*",
        "double licence",
        "double cursus",
        "double majeure",
        "bi-licence",
        "bilicence",
        "bidisciplinaire*",
        "bi-diplôme*",
        "bidiplôme*",
        "double diplomation",
    ),
    "it": ("doppio titolo", "doppia laurea", "doppio diploma", "titolo doppio", "doppio corso"),
    "ja": (
        "ダブルディグリー",
        "ダブル・ディグリー",
        "二重学位",
        "ダブルメジャー",
        "ダブル・メジャー",
        "複数専攻",
    ),
    "kk": ("қос диплом*", "қосдиплом*", "екі диплом*"),
    "ko": ("복수전공", "이중전공", "복수학위", "연계전공", "다전공"),
    "lt": ("dvigub* laipsn*", "dvigub* diplom*"),
    "nb": ("dobbelgrad*", "dobbel grad*", "dobbeltgrad*", "dobbeltdiplom*"),
    "nl": (
        "dubbele bachelor",
        "dubbele graad",
        "dubbele diploma",
        "dubbel diploma",
        "dubbelstudie*",
    ),
    "nn": ("dobbelgrad*", "dobbel grad*", "dobbeltgrad*", "dobbeltdiplom*"),
    "no": ("dobbelgrad*", "dobbel grad*", "dobbeltgrad*", "dobbeltdiplom*"),
    "pl": ("podwójn* dyplom*", "dyplom* podwójn*", "międzykierunkow*", "podwójn* stopni*"),
    "pt": (
        "dupla titulação",
        "duplo diploma",
        "dupla diplomação",
        "dupla licenciatura",
        "duplo grau",
        "grau duplo",
        "dupla graduação",
    ),
    "ru": ("двойн* диплом*", "двух диплом*", "двойн* степен*"),
    "sk": ("dvojit* diplom*", "dvojodbor*", "medziodborov*"),
    "sv": ("dubbelexamen", "dubbla examina", "dubbel examen", "dubbeldiplom*"),
    "th": ("สองปริญญา",),
    "tr": ("çift anadal*", "çift diploma*", "çift diplomalı", "çift derece*"),
    "zh": (
        "双学位",
        "雙學位",
        "双学士",
        "雙學士",
        "双专业",
        "雙專業",
        "双主修",
        "雙主修",
        "第二专业",
        "第二專業",
        "第二主修",
    ),
}

#: CQ-1: the words that name a major and a minor. A head naming one of each
#: is a major/minor pair, a combination; a head naming only one is not (a
#: "Computer Science Major" is the subject). English "major"/"minor" are
#: listed where the language uses them as loans.
_MAJOR_WORDS: dict[str, tuple[str, ...]] = {
    "en": ("major",),
    "ca": ("major",),
    "cs": ("hlavní obor*", "maior"),
    "da": ("centralt fag", "hovedfag*"),
    "de": ("hauptfach*", "kernfach*"),
    "es": ("major",),
    "et": ("peaeriala*",),
    "fi": ("pääaine*",),
    "fr": ("majeure",),
    "it": ("major",),
    "ja": ("主専攻",),
    "kk": ("мейджор*",),
    "ko": ("주전공",),
    "lt": ("pagrindin* studij*",),
    "nb": ("hovedfag*",),
    "nl": ("hoofdvak*",),
    "nn": ("hovudfag*",),
    "no": ("hovedfag*",),
    "pl": ("major",),
    "pt": ("major",),
    "ru": ("мейджор*",),
    "sk": ("hlavn* odbor*",),
    "sv": ("huvudområde*", "huvudämne*"),
    "th": ("วิชาเอก",),
    "tr": ("anadal*",),
    "zh": ("主修",),
}
_MINOR_WORDS: dict[str, tuple[str, ...]] = {
    "en": ("minor",),
    "ca": ("minor",),
    "cs": ("vedlejší obor*",),
    "da": ("sidefag*", "tilvalg*"),
    "de": ("nebenfach*", "beifach*"),
    "es": ("minor",),
    "et": ("kõrvaleriala*",),
    "fi": ("sivuaine*",),
    "fr": ("mineure",),
    "it": ("minor",),
    "ja": ("副専攻",),
    "kk": ("майнор*",),
    "ko": ("부전공",),
    "lt": ("gretutin*",),
    "nb": ("bifag*",),
    "nl": ("bijvak*",),
    "nn": ("bifag*",),
    "no": ("bifag*",),
    "pl": ("minor",),
    "pt": ("minor",),
    "ru": ("майнор*",),
    "sk": ("vedľajš* odbor*",),
    "sv": ("biämne*",),
    "th": ("วิชาโท",),
    "tr": ("yandal*",),
    "zh": ("辅修", "輔修", "副修"),
}

#: CQ-1: the words that join a second field to the subject — "with" and
#: "and" — per language. Read only in English and in the institution's own
#: languages (``languages.json`` for its country): several are one letter
#: (cs/sk "a", it/pt "e", es "y", pl/ca "i") and would join words in any
#: other language's head. Languages written without spaces (ja, zh, ko, th),
#: and the postpositions of fi/et/kk ("kanssa", "-ga", "мен"), join inside a
#: word and have none; their markers above still apply.
_COMBINATION_JOINERS: dict[str, tuple[str, ...]] = {
    "en": ("with", "and"),
    "ca": ("amb", "i"),
    "cs": ("s", "se", "a"),
    "da": ("med", "og"),
    "de": ("mit", "und"),
    "es": ("con", "y", "e"),
    "et": ("ja", "koos"),
    "fi": ("ja",),
    "fr": ("avec", "et"),
    "it": ("con", "e", "ed"),
    "ja": (),
    "kk": ("және",),
    "ko": (),
    "lt": ("ir", "su"),
    "nb": ("med", "og"),
    "nl": ("met", "en"),
    "nn": ("med", "og"),
    "no": ("med", "og"),
    "pl": ("z", "ze", "i", "oraz"),
    "pt": ("com", "e"),
    "ru": ("и", "с", "со"),
    "sk": ("s", "so", "a"),
    "sv": ("med", "och"),
    "th": (),
    "tr": ("ve", "ile"),
    "zh": (),
}

#: CQ-1: what a single-subject programme joins to its subject that is not a
#: field — honours, a year or semester, industry or practice, study abroad
#: or exchange, a foundation or preparatory year, an integrated master's, an
#: admission test, the mode of study, and "technology"/"applications"
#: ("Computer Science and Technology" is the subject's own name in several
#: systems). Words of the title filler (degree, year, honours, track…) are
#: already ignored beside these.
_COMBINATION_COMPLEMENTS: dict[str, tuple[str, ...]] = {
    "en": (
        "honours",
        "honors",
        "hons",
        "distinction",
        "merit",
        "year",
        "years",
        "semester*",
        "sandwich",
        "industry",
        "industrial",
        "placement*",
        "internship*",
        "work",
        "experience",
        "professional",
        "practice",
        "practical",
        "cooperative",
        "abroad",
        "exchange",
        "international",
        "overseas",
        "mobility",
        "foundation",
        "preparatory",
        "integrated",
        "masters",
        "entrance",
        "exam*",
        "admission*",
        "procedure",
        "technology",
        "technologies",
        "application*",
        "online",
        "distance",
        "learning",
        "part-time",
        "full-time",
    ),
    "ca": (
        "pràctiques",
        "intercanvi",
        "estranger",
        "internacional*",
        "mobilitat",
        "semestre*",
        "preparatori*",
        "integrat*",
        "accés",
        "examen*",
        "admissió",
        "tecnologi*",
        "aplicaci*",
        "distància",
        "línia",
    ),
    "cs": (
        "praxe",
        "praxí",
        "stáž*",
        "zahraničí*",
        "výměn*",
        "mezinárodn*",
        "semestr*",
        "rok*",
        "přípravn*",
        "integrovan*",
        "přijím*",
        "zkoušk*",
        "technologi*",
        "aplikac*",
        "dálkov*",
        "vyznamenání*",
    ),
    "da": (
        "praktik*",
        "udland*",
        "udveksling*",
        "international*",
        "semester*",
        "forberedel*",
        "integrere*",
        "optagelse*",
        "adgang*",
        "teknologi*",
        "anvendelse*",
        "deltid",
        "fjernundervisning*",
    ),
    "de": (
        "auszeichnung",
        "praxis*",
        "praktik*",
        "industrie*",
        "ausland*",
        "austausch*",
        "international*",
        "semester",
        "jahr*",
        "vorbereitung*",
        "integriert*",
        "aufnahmeprüfung*",
        "eignungsprüfung*",
        "zulassung*",
        "technologie*",
        "anwendung*",
        "fernstudium",
        "teilzeit",
        "vollzeit",
    ),
    "es": (
        "honores",
        "distinción",
        "práctica*",
        "pasantía*",
        "intercambio",
        "extranjero",
        "internacional*",
        "movilidad",
        "semestre*",
        "propedéutico",
        "preparatorio",
        "integrado",
        "ingreso",
        "examen*",
        "admisión",
        "tecnología*",
        "aplicaci*",
        "distancia",
        "línea",
    ),
    "et": (
        "praktika*",
        "välismaa*",
        "vahetus*",
        "rahvusvaheli*",
        "semest*",
        "aasta*",
        "ettevalmistus*",
        "integreeritud",
        "vastuvõtu*",
        "sisseastumi*",
        "tehnoloogia*",
        "rakendu*",
        "kaugõpe*",
    ),
    "fi": (
        "harjoittelu*",
        "vaihto*",
        "kansainväli*",
        "lukukau*",
        "vuosi*",
        "valmenta*",
        "integroi*",
        "valinta*",
        "pääsykoe*",
        "teknologia*",
        "sovellu*",
        "etäopiskelu*",
    ),
    "fr": (
        "stage*",
        "alternance",
        "apprentissage",
        "étranger",
        "international*",
        "mobilité",
        "échange*",
        "année*",
        "semestre*",
        "préparatoire*",
        "prépa",
        "intégré*",
        "concours",
        "admission",
        "technologie*",
        "application*",
        "distance",
        "ligne",
        "mention",
    ),
    "it": (
        "lode",
        "tirocini*",
        "stage",
        "estero",
        "internazional*",
        "mobilità",
        "scambio",
        "anno",
        "semestre*",
        "propedeutic*",
        "integrat*",
        "ammissione",
        "accesso",
        "test",
        "esame",
        "tecnologi*",
        "applicazion*",
        "distanza",
        "online",
    ),
    "ja": (),
    "kk": (
        "практика*",
        "тағылым*",
        "шетел*",
        "алмасу*",
        "халықаралық*",
        "семестр*",
        "жыл*",
        "дайындық*",
        "біріктірілген*",
        "қабылдау*",
        "емтихан*",
        "технология*",
        "қолдану*",
        "қашықтық*",
        "үздік*",
    ),
    "ko": (),
    "lt": (
        "praktik*",
        "užsien*",
        "tarptautin*",
        "semestr*",
        "metai",
        "metų",
        "parengiam*",
        "integruot*",
        "priėmim*",
        "technologij*",
        "taikym*",
        "nuotolin*",
    ),
    "nb": (
        "praksis*",
        "utland*",
        "utveksling*",
        "internasjonal*",
        "semester",
        "forkurs*",
        "integrert*",
        "opptak*",
        "teknologi*",
        "anvendelse*",
        "deltid",
        "nettbasert*",
    ),
    "nl": (
        "honours",
        "stage*",
        "buitenland*",
        "uitwisseling*",
        "internationa*",
        "jaar",
        "semester",
        "schakel*",
        "toelating*",
        "selectie",
        "technologie*",
        "toepassing*",
        "deeltijd",
        "voltijd",
        "online",
        "afstand*",
    ),
    "nn": (
        "praksis*",
        "utland*",
        "utveksling*",
        "internasjonal*",
        "semester",
        "forkurs*",
        "integrert*",
        "opptak*",
        "teknologi*",
        "deltid",
        "nettbasert*",
    ),
    "no": (
        "praksis*",
        "utland*",
        "utveksling*",
        "internasjonal*",
        "semester",
        "forkurs*",
        "integrert*",
        "opptak*",
        "teknologi*",
        "anvendelse*",
        "deltid",
        "nettbasert*",
    ),
    "pl": (
        "wyróżni*",
        "praktyk*",
        "staż*",
        "zagranic*",
        "wymian*",
        "międzynarodow*",
        "semestr*",
        "rok*",
        "przygotowawcz*",
        "zintegrowan*",
        "rekrutacj*",
        "egzamin*",
        "technologi*",
        "zastosowa*",
        "zdaln*",
    ),
    "pt": (
        "honras",
        "distinção",
        "estágio*",
        "intercâmbio",
        "exterior",
        "estrangeiro",
        "internacional*",
        "mobilidade",
        "semestre*",
        "preparatóri*",
        "integrad*",
        "ingresso",
        "vestibular",
        "exame*",
        "admissão",
        "tecnologia*",
        "aplicaç*",
        "distância",
    ),
    "ru": (
        "отличи*",
        "практик*",
        "стажировк*",
        "рубеж*",
        "обмен*",
        "международн*",
        "семестр*",
        "год*",
        "подготовительн*",
        "интегрирован*",
        "прием*",
        "приём*",
        "экзамен*",
        "вступительн*",
        "технолог*",
        "приложени*",
        "применени*",
        "дистанционн*",
    ),
    "sk": (
        "prax*",
        "stáž*",
        "zahranič*",
        "výmenn*",
        "medzinárodn*",
        "semest*",
        "rok*",
        "prípravn*",
        "integrovan*",
        "prijím*",
        "skúšk*",
        "technológi*",
        "aplikáci*",
        "diaľkov*",
        "vyznamenan*",
    ),
    "sv": (
        "praktik*",
        "utland*",
        "utbyte*",
        "internationell*",
        "termin*",
        "förberedande",
        "integrerad*",
        "antagning*",
        "behörighet*",
        "teknologi*",
        "tillämpning*",
        "distans*",
        "deltid",
        "heltid",
    ),
    "th": (),
    "tr": (
        "onur*",
        "staj*",
        "yurtdışı*",
        "değişim*",
        "uluslararası*",
        "dönem*",
        "yıl*",
        "hazırlık*",
        "entegre",
        "kabul",
        "sınav*",
        "teknoloji*",
        "uygulama*",
        "uzaktan",
    ),
    "zh": (),
}

#: CQ-1: the words that make what follows "with" a specialisation of the
#: programme, not a second field ("Computer Science with a specialisation in
#: …", "Informatik mit Schwerpunkt …", "Informatika se zaměřením na …"). A
#: specialisation is the subject's own track; whether it is the programme is
#: no combination question.
_COMBINATION_TRACK_WORDS: dict[str, tuple[str, ...]] = {
    "en": (
        "specialisation*",
        "specialization*",
        "specialism*",
        "specialising",
        "specializing",
        "concentration*",
        "pathway*",
        "stream*",
        "option*",
        "track*",
        "emphasis",
        "focus",
        "profile",
    ),
    "ca": ("menció*", "especialitat*", "especialització*", "itinerari*", "orientació*", "perfil*"),
    "cs": ("zaměř*", "specializac*", "profil*", "modul*"),
    "da": ("specialisering*", "linje*", "retning*", "profil*", "studieretning*"),
    "de": (
        "schwerpunkt*",
        "studienschwerpunkt*",
        "vertiefung*",
        "studienrichtung*",
        "fachrichtung*",
        "spezialisierung*",
        "ausrichtung*",
        "profil*",
    ),
    "es": (
        "mención*",
        "especialidad*",
        "especialización*",
        "orientación*",
        "itinerario*",
        "énfasis",
        "concentración*",
        "perfil*",
    ),
    "et": ("spetsialiseerumi*", "suun*"),
    "fi": ("suuntautumi*", "opintosuun*", "erikoistumi*", "painotu*"),
    "fr": ("parcours", "option*", "spécialité*", "spécialisation*", "orientation*", "profil*"),
    "it": (
        "curriculum",
        "curricula",
        "indirizzo*",
        "percorso*",
        "orientamento*",
        "specializzazion*",
        "profilo*",
    ),
    "ja": (),
    "kk": ("бейін*", "мамандану*", "траектория*"),
    "ko": (),
    "lt": ("specializacij*", "profil*"),
    "nb": ("spesialisering*", "studieretning*", "fordypning*", "retning*", "profil*"),
    "nl": (
        "specialisatie*",
        "afstudeerrichting*",
        "uitstroomprofiel*",
        "profiel*",
        "richting*",
        "variant*",
    ),
    "nn": ("spesialisering*", "studieretning*", "fordjuping*", "retning*", "profil*"),
    "no": ("spesialisering*", "studieretning*", "fordypning*", "retning*", "profil*"),
    "pl": ("specjalnoś*", "specjalizacj*", "profil*", "ścieżk*", "element*"),
    "pt": (
        "ênfase",
        "habilitaç*",
        "especializaç*",
        "especialidade*",
        "ramo",
        "perfil*",
        "orientaç*",
        "percurso*",
    ),
    "ru": ("профил*", "специализаци*", "направленност*", "трек*", "модул*"),
    "sk": ("zameran*", "špecializáci*", "profil*", "modul*"),
    "sv": ("inriktning*", "specialisering*", "profil*", "fördjupning*"),
    "th": (),
    "tr": ("uzmanlık*", "opsiyon*", "profil*"),
    "zh": (),
}

#: CQ-1: the shortest word that can name a field after a joiner. Shorter
#: words are articles, prepositions and other languages' joiners ("a", "in",
#: "the", "of"), as everywhere discovery counts significant words.
_MIN_FIELD_WORD = 4

Table = tuple[tuple[str, tuple[str, ...]], ...]


def _items(table: dict[str, tuple[str, ...]]) -> Table:
    return tuple(sorted(table.items()))


@lru_cache(maxsize=16)
def _phrase_pattern(table: Table) -> re.Pattern[str] | None:
    """CQ-1: one pattern for every phrase of ``table``, folded like the head.

    A ``*`` may end any word of a phrase ("podwójn* dyplom*"). Phrases in
    ja/zh/ko/th are matched inside the text, the rest as whole words.
    """
    alternatives: set[str] = set()
    for language, phrases in table:
        for phrase in phrases:
            spelled = r"\s+".join(
                re.escape(part.rstrip("*")) + (r"\w*" if part.endswith("*") else "")
                for part in _ld._fold(phrase).split()
            )
            if not spelled:
                continue
            if language in _ld._UNSPACED_UNIT_LANGUAGES:
                alternatives.add(spelled)
            else:
                alternatives.add(rf"(?<!\w){spelled}(?!\w)")
    if not alternatives:
        return None
    return re.compile("|".join(sorted(alternatives, key=len, reverse=True)))


@lru_cache(maxsize=16)
def _word_matcher(tables: tuple[Table, ...]) -> tuple[frozenset[str], tuple[str, ...]]:
    """CQ-1: every word of ``tables`` in every language, folded: whole words and stems."""
    whole: set[str] = set()
    stems: set[str] = set()
    for table in tables:
        for _language, phrases in table:
            for phrase in phrases:
                for part in re.split(r"[\s\-]+", _ld._fold(phrase)):
                    if part.endswith("*"):
                        stems.add(part.rstrip("*"))
                    elif part:
                        whole.add(part)
    return frozenset(whole), tuple(sorted(stems))


def _matches(word: str, matcher: tuple[frozenset[str], tuple[str, ...]]) -> bool:
    whole, stems = matcher
    return word in whole or word.startswith(stems)


def _named(table: dict[str, tuple[str, ...]], folded: str) -> str | None:
    pattern = _phrase_pattern(_items(table))
    found = pattern.search(folded) if pattern is not None else None
    return " ".join(found.group(0).split()) if found else None


def _joined_field(text: str, fields: list[str], languages: tuple[str, ...]) -> str | None:
    """CQ-1: "<joiner> <field>" when ``text`` joins the subject to another field.

    The head is cut into segments at every joiner ("with", "and" and their
    forms in English and the institution's languages); a joiner whose one
    side holds the requested subject (a whole run of the field or one of its
    aliases) and whose other side names a word that is no filler, no
    complement (honours, a year in industry…), no major/minor word, no place
    and no word of the subject's aliases joins a second field. A
    specialisation word on the other side ("with a specialisation in …")
    makes it the subject's own track, not a combination. "<field> and
    Engineering" is the field itself (R2, 19-Q4 as amended).
    """
    joiners = {
        _ld._fold(word)
        for code in ("en", *languages)
        for word in _COMBINATION_JOINERS.get(code, ())
    }
    if not joiners or not fields:
        return None
    names = _ld.with_strong_aliases(fields)
    head = _ld._with_engineering_as_the_field(_ld._without_award(text), names)
    tokens = _ld._shape_tokens(head)
    covered: set[int] = set()
    alias_words: set[str] = set()
    for name in names:
        wanted = _ld._shape_tokens(name)
        alias_words.update(wanted)
        for start in range(len(tokens) - len(wanted) + 1):
            if wanted and tokens[start : start + len(wanted)] == wanted:
                covered.update(range(start, start + len(wanted)))
    if not covered:
        return None
    at = [i for i, token in enumerate(tokens) if token in joiners and i not in covered]
    skip = _word_matcher(
        (_items(_COMBINATION_COMPLEMENTS), _items(_MAJOR_WORDS), _items(_MINOR_WORDS))
    )
    track = _word_matcher((_items(_COMBINATION_TRACK_WORDS),))
    filler = _ld._subject_filler()
    places = _ld._title_places()
    bounds = [-1, *at, len(tokens)]
    for n, joiner in enumerate(at, start=1):
        left = range(bounds[n - 1] + 1, joiner)
        right = range(joiner + 1, bounds[n + 1])
        left_holds = any(i in covered for i in left)
        if left_holds == any(i in covered for i in right):
            continue
        for i in right if left_holds else left:
            word = tokens[i]
            if len(word) < _MIN_FIELD_WORD:
                continue
            if _matches(word, track):
                break
            if word in filler or word in alias_words or word in places or _matches(word, skip):
                continue
            return f"{tokens[joiner]} {word}"
    return None


def combination_named(text: str, fields: list[str], *, country: str = "") -> str | None:
    """CQ-1: the combination qualifier ``text`` names, or ``None``.

    In order: a combination marker (joint honours, JH, double/dual degree,
    second major, combined… in any language of the table); a major word and
    a minor word together; a joiner that joins the subject to another field
    (``_joined_field``). Markers are read in every language at once; joiners
    only in English and the institution's languages.
    """
    folded = _ld._fold(text or "")
    if not folded.strip():
        return None
    marker = _named(_COMBINATION_MARKERS, folded)
    if marker is not None:
        return marker
    major = _named(_MAJOR_WORDS, folded)
    minor = _named(_MINOR_WORDS, folded)
    if major is not None and minor is not None:
        return f"{major} / {minor}"
    return _joined_field(text, fields, tuple(country_languages(country)))


def head_combination_rejects(
    page: PageClassification, fields: list[str], *, country: str = ""
) -> str | None:
    """CQ-1: the related verdict for a page whose head names a combination, or ``None``.

    The head is CH-1's: the page's first ``h1`` and its title's first part
    (the rest of a title is the site). A single-subject page — "with
    Honours", "(Hons)", "with a year in industry" — names no combination.
    """
    parts = _ld._title_parts(page.title or "")
    for text in (page.heading, parts[0] if parts else ""):
        named = combination_named(text or "", fields, country=country)
        if named is not None:
            return HEAD_COMBINATION_VERDICT.format(named)
    return None
