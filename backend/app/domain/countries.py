"""Countries, and the groups awards restrict themselves to.

An award page says "open to citizens of the European Union". The applicant says
"Germany". Deciding whether one satisfies the other by asking if "Germany"
appears inside "European Union" answers no — which is how a German citizen came
to be refused an EU-only award — and would answer yes to any country whose name
happened to be a substring of a group's.

Membership is a fact about the world, so it is written down. Three answers are
possible and the third matters: ``None`` means the question could not be
resolved, and an unresolved question is never a refusal.

The membership lists carry an `as of` date. They change — the United Kingdom
left the European Union — and a table that cannot say when it was true is a
table nobody can check.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

#: When the membership lists below were last reviewed against the official
#: sources. Anything decided from them is only as current as this date.
MEMBERSHIP_AS_OF = "2026-08-29"

#: ISO 3166-1 alpha-2 -> the name to show a reader.
COUNTRY_NAMES: dict[str, str] = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia",
    "CY": "Cyprus", "CZ": "Czechia", "DK": "Denmark", "EE": "Estonia",
    "FI": "Finland", "FR": "France", "DE": "Germany", "GR": "Greece",
    "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LV": "Latvia",
    "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta", "NL": "Netherlands",
    "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SK": "Slovakia",
    "SI": "Slovenia", "ES": "Spain", "SE": "Sweden",
    "IS": "Iceland", "LI": "Liechtenstein", "NO": "Norway", "CH": "Switzerland",
    "GB": "United Kingdom", "US": "United States", "CA": "Canada",
    "AU": "Australia", "NZ": "New Zealand", "ZA": "South Africa",
    "IN": "India", "PK": "Pakistan", "BD": "Bangladesh", "LK": "Sri Lanka",
    "NG": "Nigeria", "KE": "Kenya", "GH": "Ghana", "TZ": "Tanzania",
    "SG": "Singapore", "MY": "Malaysia", "TH": "Thailand", "VN": "Vietnam",
    "ID": "Indonesia", "PH": "Philippines", "BN": "Brunei", "KH": "Cambodia",
    "LA": "Laos", "MM": "Myanmar",
    "CN": "China", "HK": "Hong Kong", "JP": "Japan", "KR": "South Korea",
    "TW": "Taiwan", "TR": "Turkey", "RU": "Russia", "UA": "Ukraine",
    "KZ": "Kazakhstan", "UZ": "Uzbekistan", "KG": "Kyrgyzstan", "AZ": "Azerbaijan",
    "GE": "Georgia", "AM": "Armenia", "BY": "Belarus", "MD": "Moldova",
    "BR": "Brazil", "MX": "Mexico", "AR": "Argentina", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru", "EG": "Egypt", "MA": "Morocco",
    "SA": "Saudi Arabia", "AE": "United Arab Emirates", "QA": "Qatar",
    "KW": "Kuwait", "IL": "Israel", "IR": "Iran", "IQ": "Iraq",
    "JO": "Jordan", "LB": "Lebanon", "NP": "Nepal", "RS": "Serbia",
    "AL": "Albania", "MK": "North Macedonia", "BA": "Bosnia and Herzegovina",
    "ME": "Montenegro", "XK": "Kosovo",
    # The rest of the Commonwealth. Absent before, which meant a Rwandan or
    # Mozambican applicant was not recognised as being from anywhere, and 41 of
    # the 56 member states could not be confirmed as members at all.
    "AG": "Antigua and Barbuda", "BS": "The Bahamas", "BB": "Barbados",
    "BZ": "Belize", "BW": "Botswana", "CM": "Cameroon", "DM": "Dominica",
    "SZ": "Eswatini", "FJ": "Fiji", "GA": "Gabon", "GM": "The Gambia",
    "GD": "Grenada", "GY": "Guyana", "JM": "Jamaica", "KI": "Kiribati",
    "LS": "Lesotho", "MW": "Malawi", "MV": "Maldives", "MU": "Mauritius",
    "MZ": "Mozambique", "NA": "Namibia", "NR": "Nauru",
    "PG": "Papua New Guinea", "RW": "Rwanda", "KN": "Saint Kitts and Nevis",
    "LC": "Saint Lucia", "VC": "Saint Vincent and the Grenadines",
    "WS": "Samoa", "SC": "Seychelles", "SL": "Sierra Leone",
    "SB": "Solomon Islands", "TG": "Togo", "TO": "Tonga",
    "TT": "Trinidad and Tobago", "TV": "Tuvalu", "UG": "Uganda",
    "VU": "Vanuatu", "ZM": "Zambia",
    # Common origins for international applicants that were also missing.
    "CV": "Cabo Verde", "CI": "Côte d\u2019Ivoire", "SN": "Senegal",
    "ET": "Ethiopia", "ZW": "Zimbabwe", "TN": "Tunisia", "DZ": "Algeria",
    "TM": "Turkmenistan", "TJ": "Tajikistan", "MN": "Mongolia", "BT": "Bhutan",
    "CY_": "",
}
COUNTRY_NAMES.pop("CY_", None)

#: Other ways a page or an applicant writes a country: official long forms,
#: historical names, demonyms and common abbreviations.
_ALIASES: dict[str, str] = {
    "deutschland": "DE", "brd": "DE", "german": "DE", "germans": "DE",
    "holland": "NL", "the netherlands": "NL", "nederland": "NL", "dutch": "NL",
    "uk": "GB", "u.k.": "GB", "great britain": "GB", "britain": "GB",
    "england": "GB", "scotland": "GB", "wales": "GB", "british": "GB",
    "northern ireland": "GB",
    "usa": "US", "u.s.a.": "US", "u.s.": "US", "america": "US",
    "united states of america": "US", "american": "US",
    "czech republic": "CZ", "czech": "CZ",
    "republic of korea": "KR", "korea, republic of": "KR", "korea": "KR",
    "south korean": "KR", "korean": "KR",
    "republic of kazakhstan": "KZ", "kazakh": "KZ", "kazakhstani": "KZ",
    "russian federation": "RU", "russian": "RU",
    "people's republic of china": "CN", "prc": "CN", "chinese": "CN",
    "hong kong sar": "HK", "hong kong s.a.r.": "HK",
    "republic of ireland": "IE", "eire": "IE", "irish": "IE",
    "republic of turkiye": "TR", "turkiye": "TR", "türkiye": "TR", "turkish": "TR",
    "hellenic republic": "GR", "greek": "GR",
    "swiss confederation": "CH", "swiss": "CH", "schweiz": "CH", "suisse": "CH",
    "french": "FR", "france metropolitaine": "FR",
    "espana": "ES", "spanish": "ES", "italian": "IT", "polish": "PL",
    "portuguese": "PT", "austrian": "AT", "belgian": "BE", "swedish": "SE",
    "danish": "DK", "finnish": "FI", "norwegian": "NO", "icelandic": "IS",
    "indian": "IN", "pakistani": "PK", "bangladeshi": "BD", "nigerian": "NG",
    "kenyan": "KE", "singaporean": "SG", "malaysian": "MY", "thai": "TH",
    "vietnamese": "VN", "indonesian": "ID", "filipino": "PH",
    "japanese": "JP", "taiwanese": "TW", "brazilian": "BR", "mexican": "MX",
    "canadian": "CA", "australian": "AU", "new zealander": "NZ",
    "south african": "ZA", "egyptian": "EG", "ukrainian": "UA",
    "viet nam": "VN", "uae": "AE", "emirati": "AE",
    # Official long forms and former names. A page that writes the long form
    # and an applicant who writes the short one must reach the same country.
    "united kingdom of great britain and northern ireland": "GB",
    "brunei darussalam": "BN",
    # Renamed states. Both names are in circulation — an applicant's own
    # documents may carry the older one long after the country changed it.
    "swaziland": "SZ", "kingdom of eswatini": "SZ",
    "burma": "MM", "republic of the union of myanmar": "MM",
    "ivory coast": "CI", "cote divoire": "CI", "republic of cote divoire": "CI",
    "cape verde": "CV", "republic of cabo verde": "CV",
    "macedonia": "MK", "fyrom": "MK",
    "bahamas": "BS", "gambia": "GM",
    "st kitts and nevis": "KN", "st lucia": "LC",
    "st vincent and the grenadines": "VC",
    "papua new guinean": "PG", "trinidadian": "TT",
    "tanzanian": "TZ", "ugandan": "UG", "zambian": "ZM", "rwandan": "RW",
    "mozambican": "MZ", "namibian": "NA", "botswanan": "BW", "malawian": "MW",
    "maltese": "MT", "cypriot": "CY", "bruneian": "BN", "jamaican": "JM",
    "mauritian": "MU", "fijian": "FJ", "samoan": "WS", "tongan": "TO",
}

@dataclass(frozen=True)
class Bloc:
    """A group an award may restrict itself to.

    `complete` is the field that matters. A list known to hold every member can
    answer "no, that country is not in it". A list that is merely a good start
    cannot, and must say it does not know — otherwise a gap in the data becomes
    a confident refusal of a real applicant.

    That is not hypothetical: the Commonwealth held 15 of its 56 members, and
    Cyprus, Malta and Brunei were told they did not qualify for Commonwealth
    awards. Every list below is complete as of `as_of`, and `source` is where
    to check it.
    """

    name: str
    members: frozenset[str]
    source: str
    as_of: str
    complete: bool = True

    def __contains__(self, code: str) -> bool:
        return code in self.members


#: Groups an award may restrict itself to. Each carries the official source its
#: membership was taken from, so a reader can check it rather than trust it.
BLOCS: dict[str, Bloc] = {
    # The 27 member states. The United Kingdom is deliberately absent.
    "European Union": Bloc(
        name="European Union",
        members=frozenset({
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
            "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
            "RO", "SK", "SI", "ES", "SE",
        }),
        source="https://european-union.europa.eu/principles-countries-history/eu-countries_en",
        as_of=MEMBERSHIP_AS_OF,
    ),
    # The EU plus Iceland, Liechtenstein and Norway. Switzerland is *not* in it:
    # it is in EFTA and in Schengen, and awards routinely conflate the three.
    "European Economic Area": Bloc(
        name="European Economic Area",
        members=frozenset({
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
            "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
            "RO", "SK", "SI", "ES", "SE", "IS", "LI", "NO",
        }),
        source="https://www.efta.int/eea",
        as_of=MEMBERSHIP_AS_OF,
    ),
    "EFTA": Bloc(
        name="EFTA",
        members=frozenset({"IS", "LI", "NO", "CH"}),
        source="https://www.efta.int/about-efta/the-efta-states",
        as_of=MEMBERSHIP_AS_OF,
    ),
    # Ireland and Cyprus are in the EU and not in Schengen; Switzerland, Norway
    # and Iceland are in Schengen without being in the EU. Bulgaria and Romania
    # completed accession in 2025.
    "Schengen area": Bloc(
        name="Schengen area",
        members=frozenset({
            "AT", "BE", "BG", "HR", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
            "HU", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
            "SI", "ES", "SE", "IS", "LI", "NO", "CH",
        }),
        source="https://home-affairs.ec.europa.eu/policies/schengen-borders-and-visa/schengen-area_en",
        as_of=MEMBERSHIP_AS_OF,
    ),
    "Nordic countries": Bloc(
        name="Nordic countries",
        members=frozenset({"DK", "FI", "IS", "NO", "SE"}),
        source="https://www.norden.org/en/information/countries-and-regions",
        as_of=MEMBERSHIP_AS_OF,
    ),
    # All 56 member states. Membership is not a colonial-history list: Rwanda,
    # Mozambique, Gabon and Togo joined without one, and Cyprus and Malta are
    # members while being in the EU. Guessing from history is how the previous
    # 15-name list came to exist.
    "Commonwealth": Bloc(
        name="Commonwealth",
        members=frozenset({
            "AG", "AU", "BS", "BD", "BB", "BZ", "BW", "BN", "CM", "CA", "CY",
            "DM", "SZ", "FJ", "GA", "GM", "GH", "GD", "GY", "IN", "JM", "KE",
            "KI", "LS", "MW", "MY", "MV", "MT", "MU", "MZ", "NA", "NR", "NZ",
            "NG", "PK", "PG", "RW", "KN", "LC", "VC", "WS", "SC", "SL", "SG",
            "SB", "ZA", "LK", "TZ", "TG", "TO", "TT", "TV", "UG", "GB", "VU",
            "ZM",
        }),
        source="https://thecommonwealth.org/our-member-countries",
        as_of=MEMBERSHIP_AS_OF,
    ),
    "ASEAN": Bloc(
        name="ASEAN",
        members=frozenset({
            "BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "VN",
        }),
        source="https://asean.org/member-states/",
        as_of=MEMBERSHIP_AS_OF,
    ),
}

#: What a page may call each group. Kept apart from country aliases so that
#: "Europe" can be recognised as a group we deliberately do not resolve.
_BLOC_ALIASES: dict[str, str] = {
    "eu": "European Union", "european union": "European Union",
    "eu member states": "European Union", "eu countries": "European Union",
    "eu/eea": "European Economic Area",
    "eea": "European Economic Area", "european economic area": "European Economic Area",
    "eea countries": "European Economic Area",
    "efta": "EFTA", "european free trade association": "EFTA",
    "schengen": "Schengen area", "schengen area": "Schengen area",
    "nordic": "Nordic countries", "nordic countries": "Nordic countries",
    "commonwealth": "Commonwealth", "the commonwealth": "Commonwealth",
    "commonwealth countries": "Commonwealth",
    "asean": "ASEAN",
}

_BLOC_ALIASES_NORMALISED: dict[str, str] = {}

#: Groups a page might name that this table deliberately will not resolve,
#: because they have no single agreed membership. They produce `None`, which
#: means "ask", not "no".
AMBIGUOUS_GROUPS = frozenset({
    "europe", "european", "european countries", "the west", "western europe",
    "eastern europe", "developing countries", "the global south", "africa",
    "asia", "latin america", "middle east", "overseas", "abroad",
    "international", "third countries", "non-eu", "outside the eu",
})


def _normalise(value: str) -> str:
    """Lower-case, strip accents and punctuation, collapse whitespace."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"[’']", "", text)
    text = re.sub(r"[^a-z0-9. ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_BY_NAME: dict[str, str] = {}
for _code, _name in COUNTRY_NAMES.items():
    _BY_NAME[_normalise(_name)] = _code
    _BY_NAME[_code.lower()] = _code
# Aliases go through the same normalisation as lookups, or an alias written
# with punctuation ("Korea, Republic of") can never be found.
_BY_NAME.update({_normalise(k): v for k, v in _ALIASES.items()})
#: Three-letter codes, generated rather than typed, for the ones we name.
_ALPHA3 = {
    "DEU": "DE", "NLD": "NL", "GBR": "GB", "USA": "US", "KAZ": "KZ",
    "FRA": "FR", "ESP": "ES", "ITA": "IT", "POL": "PL", "SWE": "SE",
    "NOR": "NO", "FIN": "FI", "DNK": "DK", "ISL": "IS", "CHE": "CH",
    "AUT": "AT", "BEL": "BE", "IRL": "IE", "PRT": "PT", "GRC": "GR",
    "CZE": "CZ", "CAN": "CA", "AUS": "AU", "NZL": "NZ", "ZAF": "ZA",
    "IND": "IN", "CHN": "CN", "JPN": "JP", "KOR": "KR", "SGP": "SG",
    "TUR": "TR", "RUS": "RU", "UKR": "UA", "BRA": "BR", "MEX": "MX",
}
_BY_NAME.update({_normalise(k): v for k, v in _ALPHA3.items()})
_BLOC_ALIASES_NORMALISED.update({_normalise(k): v for k, v in _BLOC_ALIASES.items()})
_BLOC_ALIASES_NORMALISED.update({_normalise(k): k for k in BLOCS})


def bloc_phrases() -> dict[str, str]:
    """Every phrase that names a group, mapped to the group's canonical name.

    Exported so nothing else has to keep its own list. The scholarship
    extractor did, with six entries against this module's many, and a page
    restricting an award to "citizens of EFTA countries" produced no
    restriction at all — which tells a student an award is open when it is
    restricted to four countries.
    """
    return dict(_BLOC_ALIASES_NORMALISED)


def canonical_country(value: str | None) -> str | None:
    """The ISO alpha-2 code for a country name, code, alias or demonym.

    Returns ``None`` for anything that is not one country — including group
    names, which is deliberate: a group is not a country and must not be
    silently treated as one.
    """
    if not value:
        return None
    key = _normalise(value)
    if not key:
        return None
    if key in _BY_NAME:
        return _BY_NAME[key]
    # "the republic of x", "x (country)" and similar wrappers.
    stripped = re.sub(r"^(the |republic of |kingdom of |state of )+", "", key).strip()
    return _BY_NAME.get(stripped)


def canonical_bloc(value: str | None) -> str | None:
    """The canonical name of a group, if this table resolves it."""
    if not value:
        return None
    key = _normalise(value)
    return _BLOC_ALIASES_NORMALISED.get(key) or (value if value in BLOCS else None)


def country_satisfies(applicant: str | None, restriction: str | None) -> bool | None:
    """Whether an applicant's country satisfies one published restriction.

    Three answers. ``True`` and ``False`` are decisions; ``None`` means the
    question could not be resolved — an unrecognised country, or a group with
    no agreed membership — and an unresolved question is never a refusal.
    """
    code = canonical_country(applicant)
    if code is None:
        return None

    bloc = canonical_bloc(restriction)
    if bloc is not None:
        group = BLOCS[bloc]
        if code in group:
            return True
        # Only a list known to hold every member may deny one. An incomplete
        # list answering False turns a gap in our data into a refusal of a real
        # applicant — which is exactly what happened to Cyprus, Malta and
        # Brunei against a Commonwealth list holding 15 of 56 names.
        return False if group.complete else None

    if _normalise(restriction or "") in AMBIGUOUS_GROUPS:
        return None

    other = canonical_country(restriction)
    if other is None:
        return None
    return code == other


def describe_restriction(restriction: str) -> str:
    """A sentence a reader can check, for the evidence panel."""
    bloc = canonical_bloc(restriction)
    if bloc is not None:
        group = BLOCS[bloc]
        return (
            f"{group.name} ({len(group.members)} member states as of "
            f"{group.as_of}, per {group.source})"
        )
    code = canonical_country(restriction)
    if code is not None:
        return COUNTRY_NAMES.get(code, restriction)
    return f"{restriction} (this group's membership is not resolved here)"
