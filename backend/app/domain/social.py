"""Shared vocabulary and text rules for the social module.

Filtering is the whole point of Discover, so every value people filter on is
stored twice: once as the person typed it, and once as a normalized key. The
key is what the index and the equality test use, which is why "KBTU", "kbtu"
and "K.B.T.U." find each other while the profile still shows what its owner
wrote.
"""

from __future__ import annotations

import re

#: A post is a short message. Long enough for a real question about a
#: programme, short enough that a thread stays readable on a phone.
POST_MAX_CHARS = 500
REPLY_MAX_CHARS = 500
BIO_MAX_CHARS = 280

#: How many universities one profile may target. A shortlist, not a catalogue.
MAX_TARGET_UNIVERSITIES = 10
#: How many #tags one post may carry.
MAX_POST_TAGS = 5

#: A private message is a message, not a file transfer.
MESSAGE_MAX_CHARS = 2000

#: A dot or an apostrophe abbreviates a word; it does not separate two.
_ABBREVIATION_MARKS = re.compile(r"[.'’ʼ`\"]")
#: Everything else that is not a letter or a digit separates words. `\w` is
#: Unicode-aware, which is the point: Kazakh letters (ә, ғ, қ, ң, ө, ұ, ү, һ, і)
#: are outside the а-я range and a narrower class would silently delete them.
_SEPARATORS = re.compile(r"[\W_]+")

#: `#KBTU`, `#Astana`, `#Назарбаев_Университет`. Letters, digits and
#: underscores, in any script, after a single hash.
TAG_PATTERN = re.compile(r"#(\w{2,40})")


def normalize_key(value: str) -> str:
    """Fold a city, university or tag to the form the database indexes.

    Case, punctuation and spacing vary by who is typing; the thing being named
    does not. "K.B.T.U." and "KBTU" are one university, "Нур-Султан" and
    "нур султан" are one city. Returns an empty string for input that carries no
    letters or digits at all, which callers treat as "not provided".
    """
    folded = value.strip().casefold().replace("ё", "е")
    return _SEPARATORS.sub("-", _ABBREVIATION_MARKS.sub("", folded)).strip("-")


def extract_tags(body: str) -> list[str]:
    """Pull the #tags out of a post body, in order, without duplicates.

    Two spellings of one tag collapse to a single tag, because they collapse to
    a single key. The label kept is the first spelling the author used.
    """
    seen: dict[str, str] = {}
    for match in TAG_PATTERN.finditer(body):
        label = match.group(1)
        key = normalize_key(label)
        if key and key not in seen:
            seen[key] = label
    return list(seen.values())[:MAX_POST_TAGS]
