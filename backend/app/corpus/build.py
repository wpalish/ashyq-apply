"""Render the demo corpus to disk as HTML and PDF.

The pages are written the way real university pages read - prose, tables, a
sidebar - so demo mode exercises the same extraction rules as a live run
instead of shortcutting to structured data. Every page carries a machine and
human readable fixture banner.

Run with:  python -m app.corpus.build
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.corpus.data import (
    CATALOG_ONLY,
    DEMO_ACADEMIC_YEAR,
    DEMO_INTAKE,
    GOVERNMENT_PAGES,
    UNIVERSITIES,
)

PAGES_DIR = Path(__file__).parent / "pages"

BANNER = (
    '<meta name="unimatch-fixture" content="synthetic">\n'
    '<div class="fixture-banner" role="note">SYNTHETIC DEMO FIXTURE — invented figures for '
    "testing UniMatch. Not real published data. Never quote these values.</div>"
)

_CSS = (
    "body{font-family:Georgia,serif;max-width:52rem;margin:2rem auto;line-height:1.6;color:#222}"
    ".fixture-banner{background:#fff3cd;border:2px solid #d39e00;padding:.6rem;margin-bottom:1.5rem;"
    "font-family:system-ui,sans-serif;font-size:.85rem;font-weight:700}"
    "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:.4rem .6rem;text-align:left}"
    "nav,footer{font-size:.85rem;color:#666}"
)


def _page(title: str, body: str) -> str:
    return (
        f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f"<title>{title}</title><style>{_CSS}</style>{BANNER.splitlines()[0]}</head><body>\n"
        f"{BANNER.split(chr(10), 1)[1]}\n"
        f"<nav>Home &rsaquo; Study &rsaquo; {title}</nav>\n"
        f"<main>{body}</main>\n"
        f"<footer>Page last reviewed for the {DEMO_ACADEMIC_YEAR} academic year.</footer>\n"
        f"</body></html>\n"
    )


def _money(pair: tuple[float, str]) -> str:
    amount, currency = pair
    symbol = {
        "USD": "$",
        "EUR": "EUR ",
        "GBP": "GBP ",
        "CAD": "CAD ",
        "AUD": "AUD ",
        "CHF": "CHF ",
        "SGD": "SGD ",
        "JPY": "JPY ",
    }.get(currency, currency + " ")
    return f"{symbol}{amount:,.0f}"


def _program_page(uni: dict[str, Any], prog: dict[str, Any]) -> str:
    rows = [
        f"<h1>{prog['name']}</h1>",
        f"<p>{uni['name']}, {uni['city']}, {uni['country']}. Entry for the {DEMO_INTAKE} intake.</p>",
        "<h2>Entry requirements</h2>",
    ]

    if prog.get("extra"):
        rows.append(f"<p>{prog['extra']}</p>")
    if prog.get("subjects"):
        subj = ", ".join(prog["subjects"])
        rows.append(f"<p>Applicants must have studied {subj} at upper secondary level.</p>")
    if prog.get("gpa_min"):
        rows.append(
            f"<p>A minimum GPA of {prog['gpa_min']} out of {prog['gpa_scale']} scale is required "
            "for admission to this programme.</p>"
        )

    rows.append("<h3>English language requirements</h3>")
    if prog.get("ielts_overall"):
        sub = (
            f", with no individual component below {prog['ielts_sub']}"
            if prog.get("ielts_sub")
            else ""
        )
        rows.append(
            f"<p>Applicants must hold an IELTS Academic certificate with an overall band of "
            f"{prog['ielts_overall']}{sub}. IELTS General Training is not accepted. "
            "Certificates must have been issued within the last two years.</p>"
        )
    if prog.get("toefl"):
        rows.append(
            f"<p>TOEFL iBT: a minimum total score of {prog['toefl']} is accepted as an alternative.</p>"
        )

    if prog.get("sat_policy"):
        rows.append(f"<h3>Standardised tests</h3><p>{prog['sat_policy']}</p>")
    elif prog.get("sat_min"):
        rows.append(
            f"<h3>Standardised tests</h3><p>SAT: a minimum total score of {prog['sat_min']} is expected. "
            "We superscore across sittings.</p>"
        )

    extras = []
    if prog.get("entrance_exam"):
        extras.append("An entrance examination is required for all applicants.")
    if prog.get("interview"):
        extras.append("Shortlisted applicants must attend an interview.")
    if prog.get("credential_evaluation"):
        extras.append(
            "International transcripts must be submitted with a course-by-course credential "
            "evaluation from a NACES member (WES or ECE)."
        )
    if extras:
        rows.append(
            "<h3>Additional requirements</h3><ul>"
            + "".join(f"<li>{e}</li>" for e in extras)
            + "</ul>"
        )

    if prog.get("deadline"):
        rows.append(
            f"<h2>Key dates</h2><p>The application deadline for the {DEMO_INTAKE} intake is "
            f"{prog['deadline']} at 23:59 {prog.get('deadline_tz', 'local time')}. "
            "Late applications are not considered.</p>"
        )
    rows.append(
        "<h2>Documents</h2><ul>"
        "<li>Certified copy of the secondary school diploma and full transcript (PDF, max 10 MB)</li>"
        "<li>Official English translation of any document not issued in English</li>"
        "<li>Copy of the identity page of your passport</li>"
        "<li>Personal statement, maximum 650 words</li>"
        "<li>One academic reference, submitted directly by the referee</li>"
        "<li>Curriculum vitae, maximum 2 pages</li>"
        "</ul>"
        "<p>An application fee of USD 100 applies. Fee waivers are available on request for "
        "applicants demonstrating financial hardship.</p>"
    )
    if uni.get("careers"):
        rows.append(f"<h2>Careers</h2><p>{uni['careers']}</p>")
    return _page(f"{prog['name']} - {uni['name']}", "".join(rows))


def _admissions_page(uni: dict[str, Any]) -> str:
    prog = uni["programs"][0]
    body = [
        f"<h1>International admissions - {uni['name']}</h1>",
        "<p>General entry information for applicants holding a non-domestic qualification.</p>",
        "<h2>English language</h2>",
    ]
    conflict = prog.get("conflict_admissions_ielts")
    if conflict:
        body.append(
            f"<p>For all bachelor programmes taught in English, applicants must have an IELTS "
            f"Academic score with an overall band of {conflict}. Individual programmes may set "
            "higher requirements.</p>"
        )
    elif prog.get("ielts_overall"):
        body.append(
            f"<p>Applicants must have an IELTS Academic score with an overall band of "
            f"{prog['ielts_overall']}.</p>"
        )
    body.append(
        "<h2>Credential recognition</h2><p>Qualifications are assessed against the national "
        "framework. Applicants holding a qualification from outside the country may be asked to "
        "provide a credential evaluation.</p>"
    )
    if prog.get("deadline"):
        body.append(
            f"<h2>Deadlines</h2><p>Applications close {prog['deadline']} "
            f"({prog.get('deadline_tz', 'local time')}).</p>"
        )
    return _page(f"International admissions - {uni['name']}", "".join(body))


def _costs_page(uni: dict[str, Any]) -> str:
    costs = uni["costs"]
    year = costs.get("year", DEMO_ACADEMIC_YEAR)
    labels = {
        "tuition": "Tuition fee (non-domestic)",
        "mandatory_fees": "Mandatory university fees",
        "housing": "Housing / accommodation",
        "meals": "Meal plan",
        "health_insurance": "Health insurance",
        "books": "Books and study materials",
    }
    rows = "".join(
        f"<tr><td>{labels[k]}</td><td>{_money(v)}</td></tr>"
        for k, v in costs.items()
        if k in labels
    )
    prose = "".join(
        f"<p>{labels[k]} for {year}: {_money(v)} per year.</p>"
        for k, v in costs.items()
        if k in labels
    )
    total = sum(v[0] for k, v in costs.items() if k in labels)
    currency = next((v[1] for k, v in costs.items() if k in labels), "USD")
    return _page(
        f"Cost of attendance - {uni['name']}",
        f"<h1>Cost of attendance {year}</h1>"
        f"<p>Estimated annual costs for an international student at {uni['name']}.</p>"
        f"{prose}"
        f"<table><thead><tr><th>Item</th><th>Amount per year</th></tr></thead><tbody>{rows}"
        f"<tr><td><strong>Estimated total cost</strong></td><td><strong>{_money((total, currency))}</strong></td></tr>"
        f"</tbody></table>"
        f"<p>Figures are indicative and are reviewed annually.</p>",
    )


def _scholarship_page(uni: dict[str, Any], sch: dict[str, Any]) -> str:
    body = [f"<h1>{sch['name']}</h1>", f"<p>{sch['blurb']}</p>"]

    body.append("<h2>Value</h2>")
    if sch.get("amount"):
        year = sch.get("amount_year", DEMO_ACADEMIC_YEAR)
        body.append(f"<p>The award is worth {_money(sch['amount'])} per year for {year}.</p>")
    elif sch.get("percent_tuition"):
        body.append(f"<p>The award covers {sch['percent_tuition']}% of the tuition fee.</p>")
    else:
        body.append("<p>The value of the award is determined individually.</p>")

    cover_labels = {
        "tuition": "Tuition",
        "mandatory_fees": "Mandatory fees",
        "housing": "Housing",
        "meals": "Meal plan",
        "personal": "Living stipend",
        "travel": "Travel",
        "health_insurance": "Health insurance",
        "books": "Books",
    }
    rows = "".join(
        f"<tr><td>{cover_labels.get(k, k)}</td><td>{ {'yes': 'Covered', 'no': 'Not covered', 'partial': 'Partially covered'}.get(v, v) }</td></tr>"
        for k, v in sch.get("coverage", {}).items()
    )
    if rows:
        body.append(
            "<h2>What the award covers</h2>"
            f"<table><thead><tr><th>Cost</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>"
        )

    body.append("<h2>Eligibility</h2>")
    if sch.get("citizenship"):
        body.append(
            f"<p>This award is open only to citizens of {', '.join(sch['citizenship'])}. "
            "Applicants of other nationalities are not eligible.</p>"
        )
    elif sch.get("international") == "yes":
        body.append("<p>International students of any nationality are eligible to apply.</p>")
    elif sch.get("international") == "no":
        body.append("<p>This award is not open to international students.</p>")

    if sch.get("min_scores"):
        for test, score in sch["min_scores"].items():
            body.append(f"<p>Applicants must have an {test.upper()} score of at least {score}.</p>")

    mode_text = {
        "automatic": "No separate application is required. All admitted students are considered automatically.",
        "separate": "A separate scholarship application must be submitted in addition to the admission application.",
        "nomination": "Candidates are nominated by the department. Direct applications are not accepted.",
    }.get(sch.get("mode", "unknown"), "")
    body.append(f"<h2>How to apply</h2><p>{mode_text}</p>")
    if sch.get("essays"):
        body.append(
            "<p>The scholarship application requires two additional essays: a statement of "
            "motivation (maximum 800 words) and a description of your leadership experience "
            "(maximum 500 words).</p>"
        )
    if sch.get("deadline"):
        body.append(
            f"<p>The scholarship deadline is {sch['deadline']}. This is earlier than the admission deadline.</p>"
        )

    body.append("<h2>Duration and renewal</h2>")
    if sch.get("renewable"):
        body.append(
            f"<p>The award is renewable for up to {sch.get('duration', 1)} years of study. "
            f"{sch.get('renewal', 'Renewal conditions apply.')}</p>"
        )
    else:
        body.append("<p>This is a one-time award and is not renewable.</p>")

    stack = {
        "yes": "This award may be held together with other university scholarships.",
        "no": "This award may not be combined with other university scholarships.",
        "unknown": "",
    }.get(sch.get("stackable", "unknown"), "")
    if stack:
        body.append(f"<p>{stack}</p>")
    if sch.get("count"):
        body.append(f"<p>{sch['count']} awards are offered each year.</p>")

    return _page(f"{sch['name']} - {uni['name']}", "".join(body))


def _scholarship_index(uni: dict[str, Any]) -> str:
    items = "".join(
        f'<li><a href="fixture://{uni["slug"]}/scholarship-{i}.html">{s["name"]}</a> — {s["blurb"][:110]}</li>'
        for i, s in enumerate(uni["scholarships"])
    )
    return _page(
        f"Scholarships - {uni['name']}",
        f"<h1>Scholarships for international students</h1><ul>{items}</ul>"
        "<p>Awards are reviewed annually. Always check the individual award page for current terms.</p>",
    )


def build(target: Path | None = None) -> dict[str, int]:
    root = target or PAGES_DIR
    if root.exists():
        for stale in sorted(root.rglob("*"), reverse=True):
            stale.unlink() if stale.is_file() else stale.rmdir()
    root.mkdir(parents=True, exist_ok=True)

    written = 0
    catalog: list[dict[str, Any]] = []
    rankings: list[dict[str, Any]] = []

    for uni in UNIVERSITIES:
        slug = uni["slug"]
        entry = {
            "name": uni["name"],
            "country": uni["country"],
            "city": uni["city"],
            "slug": slug,
            "domain": uni.get("domain", ""),
            "city_size": uni.get("city_size", "unknown"),
            "climate": uni.get("climate", "unknown"),
            "size": uni.get("size", "unknown"),
            "campus": uni.get("campus", "unknown"),
            "workload": uni.get("workload", "unknown"),
            "programs": [
                {
                    "name": p["name"],
                    "field": p["field"],
                    "degree": p["degree"],
                    "url": f"fixture://{slug}/program-{i}.html",
                }
                for i, p in enumerate(uni["programs"])
            ],
            "admissions_url": f"fixture://{slug}/admissions.html",
            "costs_url": f"fixture://{slug}/costs.html",
            "scholarships_url": f"fixture://{slug}/scholarships.html",
            "unreachable": bool(uni.get("unreachable")),
            "exercises": uni.get("exercises", ""),
        }
        catalog.append(entry)
        for r in uni.get("rankings", []):
            rankings.append({"university": uni["name"], "country": uni["country"], **r})

        if uni.get("unreachable"):
            continue  # deliberately no pages: simulates an unreachable site

        d = root / slug
        d.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(uni["programs"]):
            (d / f"program-{i}.html").write_text(_program_page(uni, p), encoding="utf-8")
            written += 1
        (d / "admissions.html").write_text(_admissions_page(uni), encoding="utf-8")
        written += 1
        if uni.get("costs"):
            (d / "costs.html").write_text(_costs_page(uni), encoding="utf-8")
            written += 1
        if uni["scholarships"] and not uni.get("no_scholarship_page"):
            (d / "scholarships.html").write_text(_scholarship_index(uni), encoding="utf-8")
            written += 1
            for i, s in enumerate(uni["scholarships"]):
                (d / f"scholarship-{i}.html").write_text(
                    _scholarship_page(uni, s), encoding="utf-8"
                )
                written += 1

    for e in CATALOG_ONLY:
        catalog.append(
            {
                "name": e["name"],
                "country": e["country"],
                "city": e["city"],
                "slug": "",
                "domain": "",
                "programs": [],
                "unreachable": False,
                "city_size": "unknown",
                "climate": "unknown",
                "size": "unknown",
                "campus": "unknown",
                "workload": "unknown",
                "exercises": "catalogue entry only - no official page available to verify",
            }
        )
        rankings.append(
            {
                "university": e["name"],
                "country": e["country"],
                "source": "QS World University Rankings",
                "year": 2026,
                "position": e["position"],
            }
        )

    (root / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    (root / "rankings.json").write_text(json.dumps(rankings, indent=2), encoding="utf-8")
    written += 2

    gov = root / "government"
    gov.mkdir(exist_ok=True)
    for country, text in GOVERNMENT_PAGES.items():
        slug = country.lower().replace(" ", "-")
        (gov / f"{slug}.html").write_text(
            _page(
                f"Post-study work - {country}",
                f"<h1>Post-study work in {country}</h1><p>{text}</p>",
            ),
            encoding="utf-8",
        )
        written += 1

    _write_fee_pdf(root)
    written += 1
    return {"pages": written, "universities": len(catalog)}


def _write_fee_pdf(root: Path) -> None:
    """A minimal but genuinely parseable PDF fee schedule.

    One university's fees are published only as a PDF, so the PDF path is
    exercised end to end rather than being dead code.
    """
    lines = [
        "University of Groningen - Statement of Tuition and Fees",
        f"Academic year {DEMO_ACADEMIC_YEAR} - SYNTHETIC DEMO FIXTURE",
        "",
        "Tuition fee (non-EEA students): EUR 16,500 per year",
        "Mandatory university fees: EUR 600 per year",
        "Housing (university residence): EUR 7,200 per year",
        "Meal plan: EUR 3,600 per year",
        "Health insurance: EUR 1,450 per year",
        "Total estimated cost of attendance: EUR 29,350 per year",
    ]

    def esc(text: str) -> str:
        # Parentheses and backslashes delimit PDF strings; swap them out.
        return text.replace("\\", "/").replace("(", "[").replace(")", "]")

    stream_text = (
        "BT /F1 11 Tf 40 780 Td 15 TL\n" + "\n".join(f"({esc(ln)}) Tj T*" for ln in lines) + "\nET"
    )
    _emit_pdf(root / "u-groningen" / "fees.pdf", stream_text)


def _emit_pdf(path: Path, stream_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = stream_text.encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


if __name__ == "__main__":
    stats = build()
    print(
        f"Wrote {stats['pages']} fixture pages for {stats['universities']} universities to {PAGES_DIR}"
    )
