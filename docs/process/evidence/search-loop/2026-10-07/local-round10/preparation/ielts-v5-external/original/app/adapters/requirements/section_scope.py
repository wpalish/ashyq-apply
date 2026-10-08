"""Exclude explicitly non-degree sections from full-degree requirements.

Keep the DOM for the table reader and separate contiguous prose regions for
the regex reader. Joining either IR blocks or text across a removed section
can create a requirement the source never stated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import Comment, NavigableString, Tag

from app.adapters.extraction import readable_text
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import content_for_reading

_HEADINGS = {f"h{level}": level for level in range(1, 7)}
_LOCAL_CONTEXT = {"aside", "nav", "header", "footer", "table", "td", "th"}
_NON_DEGREE = re.compile(
    r"\b(?:student\s+exchange|exchange\s+(?:students?|programmes?|programs?|studies|admissions?)"
    r"|exchange(?=\s+(?:and|or|[&,/])\s+(?:visiting|non[- ]?degree)\b)"
    r"|visiting\s+students?|non[- ]?degree(?:\s+(?:students?|programmes?|programs?|admissions?))?)\b",
    re.I,
)
_FULL_DEGREE = re.compile(
    r"\b(?:bachelor|master|doctoral|undergraduate|graduate|postgraduate|first[- ]year"
    r"|freshm[ae]n|degree"
    r"|regular\s+students?)\b",
    re.I,
)
_JOINT = re.compile(r"\b(?:and|or)\b|[,&/]", re.I)
_NOT_AUDIENCE = re.compile(
    r"\b(?:not(?:\s+for)?|except(?:\s+for)?|excluding|excludes?"
    r"|(?:do|does)\s+not\s+apply\s+to)\s*$",
    re.I,
)
_EXCLUDED_AUDIENCE = re.compile(r"^\s*(?:(?:are|is)\s+)?excluded\b", re.I)
_NON_DEGREE_WORD = re.compile(r"\bnon[- ]?degree\b", re.I)


@dataclass(frozen=True)
class RequirementSections:
    html: str
    prose: tuple[str, ...]
    excluded_sections: int = 0


def full_degree_sections(html: str, original_text: str) -> RequirementSections:
    """Read only sections that are not explicitly for non-degree students.

    An unmarked page keeps its original HTML/text. A joint heading does not
    establish an exclusively non-degree audience, so it stays unchanged.
    Sidebar/navigation heading scope stays inside that container.
    """
    root = content_for_reading(parse_html(html))
    marker = "requirements-excluded-section"
    while marker in html:
        marker += "-boundary"
    excluded = 0

    def visit(node: Tag, active: int | None = None) -> int | None:
        nonlocal excluded
        for child in list(node.children):
            if isinstance(child, Tag):
                if child.name in _LOCAL_CONTEXT:
                    if active is not None:
                        child.decompose()
                    else:
                        visit(child)
                    continue
                level = _HEADINGS.get(child.name)
                if level is not None:
                    if active is not None and level <= active:
                        active = None
                    heading = child.get_text(" ", strip=True)
                    audience = _NON_DEGREE.search(heading)
                    non_degree = (
                        audience is not None
                        and not _NOT_AUDIENCE.search(heading[: audience.start()].rstrip(" (["))
                        and not _EXCLUDED_AUDIENCE.search(heading[audience.end() :])
                    )
                    # "degree" inside "non-degree" is not a second audience.
                    degree_heading = _NON_DEGREE_WORD.sub(
                        lambda match: " " * len(match.group()), heading
                    )
                    joint = False
                    if audience is not None:
                        for degree in _FULL_DEGREE.finditer(degree_heading):
                            between = (
                                heading[degree.end() : audience.start()]
                                if degree.end() <= audience.start()
                                else heading[audience.end() : degree.start()]
                            )
                            if _JOINT.search(between) and not _FULL_DEGREE.search(between):
                                joint = True
                                break
                    if active is None and non_degree and not joint:
                        active = level
                        excluded += 1
                        child.replace_with(Comment(marker))
                    elif active is not None:
                        child.decompose()
                    continue
                active = visit(child, active)
            elif isinstance(child, NavigableString) and active is not None:
                child.extract()
        return active

    visit(root)
    if not excluded:
        return RequirementSections(html, (original_text,))
    serialized = str(root)
    boundary = f"<!--{marker}-->"
    prose = tuple(text for part in serialized.split(boundary) if (text := readable_text(part)))
    return RequirementSections(serialized.replace(boundary, ""), prose, excluded)
