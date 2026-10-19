# KB application documents, round 5: Science Tokyo's encrypted guide (CS bachelor, 2026-10-19)

A one-university round for the KB question `documents` (`docs/process/KNOWLEDGE_BASE.md`, "Application
documents"), in the same shape and under the same rules as `topup_documents1` to `topup_documents4`: one item
per document an official page lists for an international applicant to the bachelor's programme, each with its
kind, `required` / `optional` / `conditional` (with the page's condition), the URL and a verbatim quote that
names the document. Target: bachelor's in Computer Science, international applicant, 2027 intake.

Round 4 listed Institute of Science Tokyo (qs2027-097) as unreadable: its 令和9（2027）年度 私費外国人留学生特別選抜
学生募集要項 for the Science and Engineering schools (`r9-guidelines-shihi`, published 2026-10-19) is an
AES-encrypted PDF with an empty user password, and the production `pdf_to_text` returned empty text because
pypdf had no `cryptography` package. With the fix in the same branch (`cryptography==50.0.2` pinned,
`pdf_document.open_reader` decrypting with `""`), the production reader returns 17,129 characters for all 12
pages. The guide was read with the production `Fetcher` with `trust_env_proxy=True` (the production user agent,
robots.txt honoured, the sandbox HTTPS proxy, verified TLS), as `verify_evidence --trust-env-proxy` does; the
link was taken from the official 募集要項 page `https://admissions.isct.ac.jp/ja/013/undergraduate/guideline`
(read the same way). No robots override, no user-agent spoofing, no paid search API. No heldout university was
opened.

## Files

- `core/qs2027-097.json`: `questions_researched: ["documents"]`, `answers` holds only `documents`. A
  documents-only draft is merged into the university's entry and never becomes its base
  (`kb_build._documents_only`). Science Tokyo is already in the KB.
- `core/evidence_check.container-2026-10-19.json`: the container pre-check, run from `backend` as
  `PYTHONPATH=. .venv/bin/python scripts/verify_evidence.py --trust-env-proxy
  evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents5/core --out <report>`. It reads PDFs
  with the same `pdf_to_text`, so it needs the `cryptography` fix (without it every row is
  `quote_found: false`). The file name contains `container`, so `kb_build` skips it. The CI check
  (`benchmark-capture.yml`, `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents5`) is still needed and
  needs the new `requirements.txt` installed on the runner; keep its report at
  `topup_documents5/evidence_check.ci-<date>.json`. Until then these documents stay unknown. No KB rebuild was
  run.

## Rules the drafts follow

Those of rounds 1-4. A document is drafted only if the guide names it; things with no vocabulary kind (the
residence card, the application-fee receipt, the attendance-and-grade certificate of a Japanese-language
school, which would repeat `transcript`, the post-admission health certificate) go in the answer's `notes`.
`conditional` carries the guide's condition; "（任意）" / "提出は任意です" is `optional`.

Quotes are the guide's text as `pdf_to_text` reads it. The PDF's text layer breaks some table cells and
wrapped lines mid-word (`公 的機関`, `ス コ ア レ ポート`); the evidence check compares word runs, so a quote
keeps those breaks as spaces where it spans one, and otherwise starts and ends on a word boundary of the text
layer.

`academic_year`: the guide's cover prints "令和９（2027）年度" and the 募集要項 page lists it under
"2027年度入試（2027年4月入学）", recorded as `2027/2028 (令和9（2027）年度, April 2027 entry)`, as round 3 did for
UTokyo's 2027年度 guide. The guide is for the 2027 intake (Japan's academic year starts in April; there is no
autumn intake on this route), so there is no `cycle_stated` / `cycle_is_intake: false`.

## Results

| seed_id | university | page | items (requirement) |
|---|---|---|---|
| qs2027-097 | Institute of Science Tokyo | 令和9（2027）年度 私費外国人留学生特別選抜 学生募集要項, 理、工、物質理工、情報理工、生命理工、環境・社会理工学院 (PDF, `r9-guidelines-shihi`), IV-4 出願書類等 | 志願票 (application form), 顔写真データ (photo), 成績証明書 (3-year transcript), 卒業証明書等 (diploma), EJU 受験票のコピー (entrance test): required. Passport copy (as the alternative to the residence card), translation (certificates not in English or Chinese), CHSI / VN-NARIC 学歴認証報告書 (high schools in China or Vietnam): conditional. TOEFL iBT / IELTS score report: optional (9) |

The route is the 私費外国人留学生特別選抜 (privately financed international students; Computer Science is
情報理工学院 情報工学系): application 21-23 December 2026, written test 20 January 2027 and interview 10 February
2027, in Japanese. The guide's 渡日前特別推薦 (pre-arrival recommendation, 融合理工学系 only) has its own list and is
not drafted, because it does not lead to Computer Science.

## Container check

`core/evidence_check.container-2026-10-19.json` (1 draft, 15 rows): **9 document rows, 9 official +
quote_found** (outcome `ok`, HTTP 200, 16,334 normalised characters); the other 6 rows are the six
unresearched core questions, `unknown`, no URL. No row was refused by robots.txt, so there is no
robots-override report.
