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
}

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
}

#: Groups an award may restrict itself to, as of MEMBERSHIP_AS_OF.
BLOCS: dict[str, frozenset[str]] = {
    # The 27 member states. The United Kingdom is deliberately absent.
    "European Union": frozenset({
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
        "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
        "SI", "ES", "SE",
    }),
    # The EU plus Iceland, Liechtenstein and Norway. Switzerland is *not* in it.
    "European Economic Area": frozenset({
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR",
        "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK",
        "SI", "ES", "SE", "IS", "LI", "NO",
    }),
    "EFTA": frozenset({"IS", "LI", "NO", "CH"}),
    # Ireland is in the EU but not in Schengen; Switzerland, Norway and Iceland
    # are in Schengen without being in the EU.
    "Schengen area": frozenset({
        "AT", "BE", "BG", "HR", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
        "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES",
        "SE", "IS", "LI", "NO", "CH",
    }),
    "Nordic countries": frozenset({"DK", "FI", "IS", "NO", "SE"}),
    "Commonwealth": frozenset({
        "GB", "CA", "AU", "NZ", "ZA", "IN", "PK", "BD", "LK", "NG", "KE",
        "GH", "TZ", "SG", "MY",
    }),
    "ASEAN": frozenset({"BN", "KH", "ID", "LA", "MY", "MM", "PH", "SG", "TH", "VN"}),
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
        return code in BLOCS[bloc]

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
        members = BLOCS[bloc]
        return (
            f"{bloc} ({len(members)} member states as of {MEMBERSHIP_AS_OF})"
        )
    code = canonical_country(restriction)
    if code is not None:
        return COUNTRY_NAMES.get(code, restriction)
    return f"{restriction} (this group's membership is not resolved here)"
