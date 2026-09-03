"""Deadlines as a calendar file.

A deadline in a table is something to remember; a deadline in a calendar is
something that reminds you. The applicant already has every date the pipeline
confirmed - this puts them where they will be seen.

Only dates the product actually confirmed become events. An unknown deadline
produces no event at all rather than a placeholder someone might act on, which
is the same rule the rest of the product follows.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

from app.schemas.result import ProgramResult

#: RFC 5545 wants CRLF, and several calendar clients quietly reject LF-only.
CRLF = "\r\n"
PRODID = "-//ASHYQ Apply//Deadlines//EN"


def _escape(text: str) -> str:
    """RFC 5545 text escaping: backslash, semicolon, comma, newline."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Long lines are folded at 75 octets with a leading space on the rest."""
    if len(line.encode()) <= 75:
        return line
    out, current = [], ""
    for char in line:
        if len((current + char).encode()) > 74:
            out.append(current)
            current = " " + char
        else:
            current += char
    out.append(current)
    return CRLF.join(out)


def _uid(run_id: str, kind: str, key: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{kind}:{key}".encode()).hexdigest()[:24]
    # Stable across exports: re-importing the file updates the event rather
    # than creating a second copy of the same deadline.
    return f"{digest}@ashyq-apply"


def _event(uid: str, day: date, summary: str, description: str, stamp: datetime) -> list[str]:
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp.strftime('%Y%m%dT%H%M%SZ')}",
        # All-day: a deadline is a day, and pinning it to a time would invent
        # an hour no source published.
        f"DTSTART;VALUE=DATE:{day.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{(day + timedelta(days=1)).strftime('%Y%m%d')}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def to_ics(results: list[ProgramResult], *, run_id: str, now: datetime) -> str:
    """A VCALENDAR of every confirmed admission and scholarship deadline."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:ASHYQ Apply deadlines",
    ]

    for result in results:
        if result.admission_deadline:
            source = result.program_url or (result.source_urls[0] if result.source_urls else "")
            lines += _event(
                _uid(run_id, "admission", result.id),
                result.admission_deadline,
                f"Application deadline — {result.program}, {result.university}",
                "\n".join(
                    part
                    for part in (
                        f"{result.program} at {result.university} ({result.country}).",
                        f"Intake: {result.intake}.",
                        f"Published as: {result.admission_deadline_raw}"
                        if result.admission_deadline_raw
                        else "",
                        f"Source: {source}" if source else "",
                        "Confirm on the official page before relying on this date.",
                    )
                    if part
                ),
                now,
            )

        for scholarship in result.scholarships:
            if not scholarship.deadline:
                continue
            lines += _event(
                _uid(run_id, "scholarship", f"{result.id}:{scholarship.name}"),
                scholarship.deadline,
                f"Scholarship deadline — {scholarship.name} ({result.university})",
                "\n".join(
                    part
                    for part in (
                        f"For {result.program} at {result.university}.",
                        f"Classification: {scholarship.classification.value}.",
                        f"Source: {scholarship.source_urls[0]}"
                        if scholarship.source_urls
                        else "",
                        "Confirm on the official page before relying on this date.",
                    )
                    if part
                ),
                now,
            )

    lines.append("END:VCALENDAR")
    return CRLF.join(_fold(line) for line in lines) + CRLF


def upcoming(results: list[ProgramResult], *, today: date, limit: int = 10) -> list[dict]:
    """The next deadlines, soonest first, with past ones marked rather than hidden.

    A deadline that has passed is exactly what an applicant needs to see;
    dropping it would answer the wrong question.
    """
    entries: list[dict] = []
    for result in results:
        if result.admission_deadline:
            entries.append(
                {
                    "kind": "admission",
                    "date": result.admission_deadline.isoformat(),
                    "passed": result.admission_deadline < today,
                    "title": f"{result.program}, {result.university}",
                    "result_id": result.id,
                    "source_url": result.program_url,
                }
            )
        for scholarship in result.scholarships:
            if scholarship.deadline:
                entries.append(
                    {
                        "kind": "scholarship",
                        "date": scholarship.deadline.isoformat(),
                        "passed": scholarship.deadline < today,
                        "title": f"{scholarship.name} — {result.university}",
                        "result_id": result.id,
                        "source_url": (
                            scholarship.source_urls[0] if scholarship.source_urls else None
                        ),
                    }
                )
    entries.sort(key=lambda e: (e["passed"], e["date"]))
    return entries[:limit]
