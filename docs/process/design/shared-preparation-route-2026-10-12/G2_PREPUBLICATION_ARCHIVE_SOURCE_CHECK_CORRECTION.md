# Correction to G2 prepublication archive check

**2026-10-12 · READ ONLY · replaces the archive-mismatch conclusion only**

The preserved `G2_PREPUBLICATION_ARCHIVE_SOURCE_CHECK.md` and its seal contain an erroneous archive-mismatch conclusion. I resolved each `INDEX.json` entry against the external `product-platform/2026-10-12` stage instead of the archive root named by the index:

`work/unimatch-calendar-materials/docs/process/design/shared-preparation-route-2026-10-12/`

The specific `g2-execution/backend-full/expected-native-source-pins.json` in the archive is **66,848 bytes**, SHA-256 `641f198e5bffbdf688c0010be7b11db47c796fe732cc5a4ee8db647dff63a7fb`, exactly as indexed and exactly as the Git HEAD blob. The later external stage helper is **67,552 bytes**, SHA-256 `0c13a397c86d053c84de2efb8438dd7b3060e4d6719c4c872ff8fd1464a87794`; it is a different file outside the archive. Its later change does not indicate archive replacement.

The correct archive-root result is **844/844 indexed entries matching SHA-256 and byte size**, with 844 unique relative paths and no missing member, at INDEX SHA-256 `c0467b2ef6758246d48b0935ebea7b83e7d463f838e23175897a783cf737536e`. No archive file needs replacement on account of the earlier report. The old report and seal remain intact as an audit trail; use `G2_PREPUBLICATION_ARCHIVE_SOURCE_CHECK_V2.md` for the current exact qualification and its Git portability limit.

The source-pin conclusion in the old report was correct: 33/33 application files match the separate source-pin file. The INDEX `status` text describes a historical point and may receive a future status update; this correction does not rewrite that text or claim publication.
