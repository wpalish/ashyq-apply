"""``stage_summary``: stage-level aggregates with no case id, URL or value (heldout H-1).

Synthetic data only. Two cases, one arm, one repetition: every count in the
output is derived by hand below, and nothing identifying may appear in stdout
or in the ``--out`` file. The leak guard is part of the CLI and is tested too.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.research import stage_summary
from evaluation.research.schema import Dataset

IDS = ("zqalpha", "zqbeta")
GOLD = {"zqalpha": "https://zqalpha.example/en/cs", "zqbeta": "https://zqbeta.example/cs"}
WRONG_PAGE = "https://zqbeta.example/law"
SECRET_TITLE = "Zqsecret Programme Title"
VALUES = ("2027-05-01", "Deadline 1 May 2027", "EUR 9876", "Other Zqplace")


def _scope(case_id: str, **extra: Any) -> dict[str, Any]:
    return {"university": f"{case_id.title()} Institute", "degree": "bachelor", **extra}


def _evidence(case_id: str, url: str, **scope: Any) -> dict[str, Any]:
    return {
        "url": url,
        "excerpt": "Deadline 1 May 2027",
        "scope": scope or _scope(case_id),
        "accessed_on": "2026-10-01",
        "source_type": "official",
    }


def _case(case_id: str) -> dict[str, Any]:
    fees = f"https://{case_id}.example/fees"
    return {
        "id": case_id,
        "dataset_version": "synthetic-1",
        "university": f"{case_id.title()} Institute",
        "domain": f"{case_id}.example",
        "country": "Nowhere",
        "site_types": [],
        "request": _scope(case_id),
        "programme_urls": [GOLD[case_id]],
        "programme_status": "known",
        "programme_evidence": [_evidence(case_id, GOLD[case_id])],
        "labels": [
            {
                "key": "deadline",
                "status": "known",
                "value": "2027-05-01",
                "evidence": [_evidence(case_id, fees)],
            }
        ],
        "review": {
            "status": "human_verified",
            "prepared_by": "t",
            "reviewer": "r",
            "verified_on": "2026-10-01",
            "notes": "synthetic",
        },
    }


def _dataset() -> Dataset:
    return Dataset.model_validate(
        {"version": "synthetic-1", "split": "development", "cases": [_case(i) for i in IDS]}
    )


def _observation(case_id: str) -> dict[str, Any]:
    fees = f"https://{case_id}.example/fees"
    if case_id == "zqalpha":
        predictions = [
            # Correct: right value, the label's scope, supported.
            {
                "key": "deadline",
                "value": "2027-05-01",
                "supported": True,
                "evidence": _evidence(case_id, fees),
            },
            # Unlabelled, and an award key whose award segment must not be printed.
            {
                "key": "scholarships.zqsecretaward.exists",
                "value": True,
                "evidence": _evidence(case_id, fees),
            },
        ]
        return {
            "case_id": case_id,
            "programme_urls": [GOLD[case_id]],
            "programme_page_languages": {GOLD[case_id]: "en"},
            "predictions": predictions,
            "telemetry": {"http_fetches": 10, "search_calls": 2, "latency_seconds": 30.0},
            "page_outcomes": [
                {"category": "fetched-ok", "url": fees, "page_type": "costs"},
                {"category": "classifier-rejected", "url": fees, "page_type": "unknown"},
            ],
        }
    # Right value, wrong university and degree: one wrong-scope claim.
    wrong = _evidence(case_id, fees, university="Other Zqplace", degree="master")
    return {
        "case_id": case_id,
        "programme_urls": [WRONG_PAGE],
        "predictions": [
            {"key": "deadline", "value": "2027-05-01", "supported": True, "evidence": wrong}
        ],
        "telemetry": {"http_fetches": 20, "search_calls": 4, "latency_seconds": 50.0},
        "page_outcomes": [
            {"category": "fetched-ok", "url": fees, "page_type": "general_admissions"},
            {"category": "no-pattern-match", "url": fees, "page_type": "scholarship_index"},
        ],
    }


def _trace(case_id: str) -> dict[str, Any]:
    if case_id == "zqalpha":
        return {
            "manual_seeds": {
                "admissions": "https://zqalpha.example/a",
                "costs": "https://zqalpha.example/c",
            },
            "sitemaps_read": ["https://zqalpha.example/sitemap.xml"],
            "sitemap_urls_seen": 100,
            "sitemap_urls_kept": 7,
            "search_results": [
                {
                    "family": "field_and_degree",
                    "urls": [GOLD[case_id], "https://elsewhere.example/x"],
                },
            ],
            "pages_read": [[GOLD[case_id], ""]],
            "rejected_sample": [
                ["https://zqalpha.example/p", f"page subject '{SECRET_TITLE}' does not match x"],
                ["https://zqalpha.example/q", "search lead unresolved (http_error)"],
            ],
            "rejected_total": 3,
            "errors": ["search identity recovery: checked 2, confirmed 1"],
            "read_ledger": {
                "by_phase": {"discovery": 5, "verify": 4},
                "by_kind": {"core": 3},
                "refusals": [
                    {
                        "url": "https://zqalpha.example/z",
                        "phase": "funding",
                        "kind": "award",
                        "reason": "4 of 60 reads left",
                    }
                ],
            },
        }
    return {
        "manual_seeds": {"admissions": "https://zqbeta.example/a"},
        "search_results": [
            {"family": "local_language", "urls": [WRONG_PAGE]},
            {"family": "field_and_degree", "urls": []},
        ],
        "pages_read": [[GOLD[case_id], "reads as unknown, not a programme page"]],
        "rejected_total": 1,
        "errors": ["search identity recovery: checked 3, confirmed 0"],
        "read_ledger": {"by_phase": {"discovery": 8}},
    }


def _run(root: Path) -> Path:
    for case_id in IDS:
        target = root / f"{case_id}-off" / "20261005T000001Z"
        target.mkdir(parents=True)
        capture = {
            "pipeline_sha": "abc",
            "captured_at": "20261005T000001Z",
            "mode": "synthetic",
            "config": {},
            "observations": [_observation(case_id)],
        }
        (target / "capture.json").write_text(json.dumps(capture))
        raw = {
            "canary": {"institutions": [{"access": "REACHED", "discovery_trace": _trace(case_id)}]}
        }
        (target / f"{case_id}.raw.json").write_text(json.dumps(raw))
    return root


@pytest.fixture()
def paths(tmp_path: Path) -> dict[str, Path]:
    corpus = tmp_path / "corpus.json"
    corpus.write_text(_dataset().model_dump_json())
    return {"run": _run(tmp_path / "run"), "corpus": corpus, "out": tmp_path / "out" / "s.md"}


def _summary(paths: dict[str, Path]) -> dict[str, Any]:
    column: dict[str, Any] = stage_summary.summarize_run(
        _dataset(), stage_summary.load_run(paths["run"])
    )["columns"]["off#1"]
    return column


def test_cli_prints_and_writes_nothing_identifying(
    paths: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    code = stage_summary.main(
        [str(paths["run"]), "--dataset", str(paths["corpus"]), "--out", str(paths["out"])]
    )
    printed = capsys.readouterr().out
    assert code == 0
    assert printed == paths["out"].read_text(encoding="utf-8")
    folded = printed.casefold()
    forbidden = [
        *IDS,
        *(f"{i.title()} Institute" for i in IDS),
        *(f"{i}.example" for i in IDS),
        "http",
        "elsewhere",
        "zqsecret",
        SECRET_TITLE,
        *VALUES,
    ]
    for token in forbidden:
        assert token.casefold() not in folded, token
    assert "| row | off#1 |" in printed


def test_discovery_funnel_and_gold_stage_are_summed_over_cases(paths: dict[str, Path]) -> None:
    s = _summary(paths)
    funnel = s["discovery funnel"]
    assert funnel["cases"] == 2
    assert funnel["seeds"] == 3
    assert funnel["sitemaps_read"] == 1
    assert (funnel["sitemap_urls_seen"], funnel["sitemap_urls_kept"]) == (100, 7)
    assert funnel["reads_in_discovery"] == 13
    assert funnel["discovery_queries"] == 3
    assert funnel["discovery_queries:field_and_degree"] == 2
    assert funnel["discovery_queries:local_language"] == 1
    assert funnel["search_results_returned"] == 3
    assert funnel["search_results_on_official_domain"] == 2
    assert funnel["search_calls_total"] == 6
    assert funnel["identity_recovery_leads_checked"] == 5
    assert funnel["identity_recovery_leads_confirmed"] == 1
    assert funnel["programme_pages_confirmed"] == 2
    assert funnel["confirmed_pages_hit"] == 1
    assert funnel["confirmed_pages_wrong"] == 1
    assert funnel["case_outcome:hit"] == funnel["case_outcome:wrong"] == 1
    gold = s["gold programme page"]
    assert gold["furthest:confirmed"] == 1
    assert gold["furthest:rejected"] == 1
    assert gold["furthest:never"] == 0
    assert gold["gold_returned_by_search"] == 1
    assert gold["gold_read"] == 2
    assert gold["gold_confirmed"] == 1
    assert gold["gold_never_seen"] == 0
    assert gold["returned_by_family:field_and_degree"] == 1


def _replay(paths: dict[str, Path], telemetry: dict[str, dict[str, int]]) -> None:
    for case_id in IDS:
        path = next((paths["run"] / f"{case_id}-off").glob("*/capture.json"))
        capture = json.loads(path.read_text())
        capture["config"]["search_provider"] = "recorded"
        capture["observations"][0]["telemetry"].update(telemetry[case_id])
        path.write_text(json.dumps(capture))


def test_a_replay_counts_its_misses_per_search_kind(
    paths: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """H-1: discovery's misses apart from the topic/scholarship/identity misses."""
    kinds = ("discovery", "topic", "scholarship", "identity")
    _replay(
        paths,
        {
            "zqalpha": {
                "recorded_search_hits": 4,
                "recorded_search_misses": 5,
                **{
                    f"recorded_search_misses_{k}": n
                    for k, n in zip(kinds, (1, 2, 1, 1), strict=True)
                },
            },
            "zqbeta": {
                "recorded_search_hits": 6,
                "recorded_search_misses": 1,
                **{
                    f"recorded_search_misses_{k}": n
                    for k, n in zip(kinds, (0, 0, 1, 0), strict=True)
                },
            },
        },
    )
    funnel = _summary(paths)["discovery funnel"]
    assert funnel["recorded_search_misses"] == 6
    assert {k: funnel[f"recorded_search_misses_{k}"] for k in kinds} == {
        "discovery": 1,
        "topic": 2,
        "scholarship": 2,
        "identity": 1,
    }
    code = stage_summary.main([str(paths["run"]), "--dataset", str(paths["corpus"])])
    printed = capsys.readouterr().out
    assert code == 0
    assert "| recorded_search_misses_discovery | 1 |" in printed
    assert "| recorded_search_misses_identity | 1 |" in printed


def test_a_replay_captured_before_h1_has_no_per_kind_rows(paths: dict[str, Path]) -> None:
    _replay(
        paths,
        {case_id: {"recorded_search_hits": 3, "recorded_search_misses": 2} for case_id in IDS},
    )
    funnel = _summary(paths)["discovery funnel"]
    assert funnel["recorded_search_misses"] == 4
    assert not [k for k in funnel if k.startswith("recorded_search_misses_")]


def test_refusals_count_categories_only(paths: dict[str, Path]) -> None:
    refusals = _summary(paths)["refusals"]
    assert refusals["lead_rejected_sample:subject_mismatch"] == 1
    assert refusals["lead_rejected_sample:search_lead_unresolved:web_error"] == 1
    assert refusals["read_refused:reads_as:unknown"] == 1
    assert refusals["leads_rejected_total"] == 4
    assert refusals["page_outcome:fetched_ok"] == 2
    assert refusals["page_outcome:classifier_rejected"] == 1
    assert refusals["budget_refused:funding:award"] == 1


def test_languages_evidence_claims_and_scope_dimensions(paths: dict[str, Path]) -> None:
    s = _summary(paths)
    languages = s["languages"]
    assert languages["confirmed_html_lang:en"] == 1
    assert languages["confirmed_html_lang:unrecorded"] == 1
    assert languages["confirmed_url_hint:en"] == 1
    assert languages["gold_returned_html_lang:en"] == 1
    assert languages["gold_returned_url_hint:en"] == 1
    evidence = s["evidence"]
    assert evidence["pages:costs"] == 1
    assert evidence["pages:requirements"] == 1
    assert evidence["pages:scholarships"] == 1
    assert evidence["pages:other"] == 1
    assert evidence["pages_fetched_ok:costs"] == evidence["pages_fetched_ok:requirements"] == 1
    assert evidence["reads_by_phase:discovery"] == 13
    claims = s["claims"]
    assert claims["claims"] == 3
    assert claims["by_type:deadline"] == 2
    assert claims["by_type:scholarships.*.exists"] == 1
    assert claims["matched_to_label"] == 2
    assert claims["verdict:correct"] == 1
    assert claims["verdict:wrong_scope"] == 1
    assert claims["verdict:unlabelled"] == 1
    assert claims["known_labels"] == 2
    scope = s["wrong scope by dimension"]
    assert scope == {"wrong_scope_claims": 1, "dimension:university": 1, "dimension:degree": 1}
    budget = s["budget and time"]
    assert budget["reads_per_case:mean"] == 15.0
    assert budget["reads_per_case:max"] == 20.0
    assert budget["queries_per_case:mean"] == 3.0
    assert budget["seconds_per_case:max"] == 50.0


def test_the_guard_aborts_when_an_identifier_reaches_the_output(
    paths: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for leaked in ("row zqbeta here", "see https://x", "Zqalpha Institute", "zqalpha.example"):
        monkeypatch.setattr(stage_summary, "render", lambda _summary, text=leaked: text)
        code = stage_summary.main(
            [str(paths["run"]), "--dataset", str(paths["corpus"]), "--out", str(paths["out"])]
        )
        captured = capsys.readouterr()
        assert code == 2
        assert captured.out == ""
        assert "zq" not in captured.err.casefold()
        assert not paths["out"].exists()


def test_leak_check_matches_case_ids_as_whole_words_only() -> None:
    dataset = _dataset().model_copy(
        update={"cases": [_dataset().cases[0].model_copy(update={"id": "um"})]}
    )
    assert stage_summary.leak_check("reads_per_case:maximum", dataset) == []
    assert stage_summary.leak_check("case um failed", dataset) == ["case_id"]
    assert stage_summary.leak_check("x:um:y", dataset) == ["case_id"]


@pytest.mark.parametrize(
    ("reason", "category"),
    [
        (f"page subject '{SECRET_TITLE}' does not match requested fields", "subject_mismatch"),
        ("page names a campus abroad (zqcity), not the institution's own", "campus_abroad"),
        ("reads as program_catalog, not a programme page", "reads_as:program_catalog"),
        ("page names degree level master, not bachelor", "degree_level:master"),
        ("search lead unresolved (http_error)", "search_lead_unresolved:web_error"),
        ("something new about Zqalpha Institute", "other"),
    ],
)
def test_refusal_reasons_become_a_fixed_vocabulary(reason: str, category: str) -> None:
    assert stage_summary.refusal_category(reason) == category


def test_language_codes_and_claim_types_are_sanitised() -> None:
    assert stage_summary.language_code("pt-BR") == "pt-br"
    assert stage_summary.language_code("Zqalpha Institute") == "other"
    assert stage_summary.url_language_hint("https://x.example/p?lang=nl") == "nl"
    assert stage_summary.url_language_hint("https://x.example/programmes/cs") == "none"
    assert stage_summary.claim_type("scholarships.Zq Award.exists") == "scholarships.*.exists"
    assert stage_summary.claim_type("ielts.overall") == "ielts.overall"


# --- ES-1: evidence-reach rows ---------------------------------------------

#: Details as the stages write them; the URL and the title must never surface.
_ES1_OUTCOMES = [
    {
        "category": "fetched-ok",
        "url": "https://zqalpha.example/funding",
        "page_type": "scholarship_index",
        "detail": "read as a funding index; 0 award links, 0 queued within the award budget",
    },
    {
        "category": "fetched-ok",
        "url": "https://zqalpha.example/funding/intl",
        "page_type": "scholarship_index",
        "detail": "read as a funding index; 5 award links, 3 queued within the award budget"
        "; 2 awards read from its own sections",
    },
    {
        "category": "classifier-rejected",
        "url": "https://zqalpha.example/funding/deep",
        "page_type": "scholarship_index",
        "detail": "index page beyond the index budget; not followed"
        "; 3 awards read from its own sections",
    },
    {
        "category": "fetch-failed",
        "url": "https://zqalpha.example/guide.pdf",
        "detail": "PDF without a text layer",
    },
    {
        "category": "fetched-ok",
        "url": "https://zqalpha.example/fees-table",
        "page_type": "costs",
        "detail": "PDF, 4 pages",
    },
    {
        # A detail quoting a URL and a title: only its category may count.
        "category": "classifier-rejected",
        "url": "https://zqalpha.example/zqsecret",
        "page_type": "scholarship_award",
        "detail": "read as a funding index; 0 award links at https://zqalpha.example/x "
        f"'{SECRET_TITLE}'",
    },
]

_ES1_DIAGNOSTICS = [
    "https://zqalpha.example/funding: 4 award links on another host not followed "
    "(1 on the same site).",
    "https://zqalpha.example/funding: classified as scholarship_index; read as a funding index.",
]


def _with_es1(paths: dict[str, Path]) -> None:
    """Add the ES-1 outcomes to zqalpha's capture, its diagnostics to its trace."""
    root = paths["run"] / "zqalpha-off"
    capture_path = next(root.glob("*/capture.json"))
    capture = json.loads(capture_path.read_text())
    capture["observations"][0]["page_outcomes"] += _ES1_OUTCOMES
    capture_path.write_text(json.dumps(capture))
    raw_path = next(root.glob("*/*.raw.json"))
    raw = json.loads(raw_path.read_text())
    raw["canary"]["institutions"][0]["discovery_trace"]["run_diagnostics"] = _ES1_DIAGNOSTICS
    raw_path.write_text(json.dumps(raw))
    beta = next((paths["run"] / "zqbeta-off").glob("*/*.raw.json"))
    raw = json.loads(beta.read_text())
    raw["canary"]["institutions"][0]["discovery_trace"]["selected"] = {
        "scholarships": ["https://zqbeta.example/funding"]
    }
    beta.write_text(json.dumps(raw))


def test_evidence_reach_categories_are_counted_from_details_and_diagnostics(
    paths: dict[str, Path],
) -> None:
    _with_es1(paths)
    evidence = _summary(paths)["evidence"]
    assert evidence["funding_index_zero_links"] == 2
    assert evidence["index_beyond_budget"] == 1
    assert evidence["award_sections_read"] == 5
    assert evidence["award_links_dropped_off_host"] == 4
    assert evidence["award_links_dropped_off_host_same_site"] == 1
    # zqalpha's discovery selected no scholarships page; zqbeta's did.
    assert evidence["funding_entry_none"] == 1
    assert evidence["pdf_met:other"] == 1
    assert evidence["pdf_met:costs"] == 1
    assert evidence["pages_fetched_ok:scholarships"] == 2


def test_a_detail_with_a_url_and_a_title_prints_its_category_only(
    paths: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _with_es1(paths)
    assert stage_summary.main([str(paths["run"]), "--dataset", str(paths["corpus"])]) == 0
    printed = capsys.readouterr().out
    folded = printed.casefold()
    for token in (*IDS, "http", "zqsecret", SECRET_TITLE, "funding/intl", "guide", "pdf,"):
        assert token.casefold() not in folded, token
    assert "| funding_index_zero_links | 2 |" in printed
    assert "| award_links_dropped_off_host | 4 |" in printed


def test_an_unrecognised_detail_counts_nothing() -> None:
    assert stage_summary.evidence_categories("award page; 3 claims read") == []
    assert stage_summary.evidence_categories(f"{SECRET_TITLE}: 12 award links") == []
    assert stage_summary.evidence_categories(None) == []


def _reach_dataset() -> Dataset:
    """zqalpha knows four more labels: HTML reached through a URL variant, HTML
    not reached, PDF-only reached, and an award's exists label not reached."""
    raw = _dataset().model_dump(mode="json")
    alpha = raw["cases"][0]
    alpha["labels"] += [
        {
            "key": "tuition",
            "status": "known",
            "value": "EUR 9876",
            "evidence": [
                _evidence("zqalpha", "https://zqalpha.example/fees-table/index.html"),
                _evidence("zqalpha", "https://zqalpha.example/fees-old.pdf"),
            ],
        },
        {
            "key": "ielts.overall",
            "status": "known",
            "value": 6.5,
            "evidence": [_evidence("zqalpha", "https://zqalpha.example/english")],
        },
        {
            "key": "gpa",
            "status": "known",
            "value": 3.0,
            "evidence": [_evidence("zqalpha", "https://zqalpha.example/fees-table.pdf")],
        },
        {
            "key": "scholarships.zqsecretaward.exists",
            "status": "known",
            "value": True,
            "evidence": [_evidence("zqalpha", "https://zqalpha.example/award")],
        },
    ]
    return Dataset.model_validate(raw)


def test_evidence_reach_is_dataset_aware_and_keeps_pdfs_apart(
    paths: dict[str, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _with_es1(paths)
    capture_path = next((paths["run"] / "zqalpha-off").glob("*/capture.json"))
    capture = json.loads(capture_path.read_text())
    capture["observations"][0]["page_outcomes"].append(
        {"category": "fetched-ok", "url": "https://zqalpha.example/fees-table.pdf"}
    )
    capture_path.write_text(json.dumps(capture))
    dataset = _reach_dataset()
    column = stage_summary.summarize_run(dataset, stage_summary.load_run(paths["run"]))["columns"][
        "off#1"
    ]
    evidence = column["evidence"]
    # Both deadline labels: their fees page was fetched ok in both cases.
    assert evidence["evidence_reach:deadline"] == "2/2"
    # The HTML form of the fees table was fetched; the PDF beside it stays out
    # of the HTML denominator, and a label with any HTML evidence is HTML.
    assert evidence["evidence_reach:tuition"] == "1/1"
    assert evidence["evidence_reach:ielts_overall"] == "0/1"
    assert evidence["evidence_reach:scholarship_exists"] == "0/1"
    assert evidence["evidence_reach_pdf:gpa"] == "1/1"
    assert "evidence_reach:gpa" not in evidence
    assert not [k for k in evidence if k.startswith("_reach_")]
    corpus = paths["corpus"]
    corpus.write_text(dataset.model_dump_json())
    assert stage_summary.main([str(paths["run"]), "--dataset", str(corpus)]) == 0
    printed = capsys.readouterr().out
    assert "| evidence_reach:scholarship_exists | 0/1 |" in printed
    assert "zqsecret" not in printed.casefold()


@pytest.mark.parametrize(
    ("key", "question"),
    [
        ("tuition", "tuition"),
        ("deadline.eu_national", "deadline"),
        ("english_evidence.toefl_ibt.minimum", "english_evidence"),
        ("scholarships.Zq Award.exists", "scholarship_exists"),
        ("scholarships.zq.applicability.international", "scholarship_international"),
        ("documents.scholarship.zqsecretaward.essay.required", "other"),
    ],
)
def test_reach_questions_are_a_fixed_vocabulary(key: str, question: str) -> None:
    assert stage_summary.reach_question(key) == question


@pytest.mark.parametrize("summary_only", [False, True])
def test_the_scorecard_ignores_the_run_diagnostics(
    paths: dict[str, Path], capsys: pytest.CaptureFixture[str], summary_only: bool
) -> None:
    from evaluation.research import scorecard

    args = [str(paths["run"]), "--dataset", str(paths["corpus"])]
    args += ["--summary-only"] if summary_only else []
    assert scorecard.main(args) == 0
    before = capsys.readouterr().out
    raw_path = next((paths["run"] / "zqalpha-off").glob("*/*.raw.json"))
    raw = json.loads(raw_path.read_text())
    raw["canary"]["institutions"][0]["discovery_trace"]["run_diagnostics"] = _ES1_DIAGNOSTICS
    raw_path.write_text(json.dumps(raw))
    assert scorecard.main(args) == 0
    assert capsys.readouterr().out == before


def test_the_award_link_drop_is_counted_and_the_links_are_unchanged() -> None:
    from app.adapters.scholarship import web_scholarships as ws

    html = (
        "<html><body><main>"
        '<a href="/scholarships/merit">Merit scholarship</a>'
        '<a href="https://awards.zqalpha.example/scholarships/global">Global scholarship</a>'
        '<a href="https://grants.elsewhere.example/scholarships/zq">National scholarships</a>'
        '<a href="https://awards.zqalpha.example/scholarships/global">Global again</a>'
        '<a href="https://awards.zqalpha.example/contact">Contact</a>'
        "</main></body></html>"
    )
    base = "https://www.zqalpha.example/funding"
    links, dropped = ws._award_links_counted(html, base)
    assert links == ws._award_links(html, base)
    assert links == ["https://www.zqalpha.example/scholarships/merit"]
    assert dropped == [
        "https://awards.zqalpha.example/scholarships/global",
        "https://grants.elsewhere.example/scholarships/zq",
    ]
    line = ws._off_host_line(base, dropped)
    assert stage_summary.evidence_categories(line) == [
        ("award_links_dropped_off_host", 2),
        ("award_links_dropped_off_host_same_site", 1),
    ]


def test_the_canary_keeps_only_this_sites_prose_lines() -> None:
    from types import SimpleNamespace

    from scripts import canary_discovery

    run = SimpleNamespace(
        errors=[
            "https://www.zqalpha.example/funding: 2 award links on another host not followed "
            "(1 on the same site).",
            "page fetched-ok: https://zqalpha.example/f (page_type scholarship_index): x",
            "https://zqbeta.example/funding: 1 award links on another host not followed "
            "(0 on the same site).",
            "No official scholarship page is known for Zqalpha Institute",
        ],
        unknowns=["https://zqalpha.example/p: does not state a deadline"],
    )
    kept = canary_discovery.run_diagnostics(run, "zqalpha.example")  # type: ignore[arg-type]
    assert kept == [run.errors[0], run.unknowns[0]]
