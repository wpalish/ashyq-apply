from pathlib import Path
root=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20');repo=root/'work/ashyq-apply'
t=(repo/'backend/tests/test_subject_phrase_capture.py').read_text()
t=t.replace('from app.adapters.discovery import live_discovery','from app.adapters import page_classifier')
t=t.replace('live_discovery.SUBJECT_PHRASE_MATCH','page_classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING').replace('live_discovery, "SUBJECT_PHRASE_MATCH"','page_classifier, "PROGRAMME_IDENTITY_BEFORE_FUNDING"')
t=t.replace('subject_phrase_match','programme_identity_before_funding').replace('subject-phrase-match','programme-identity-before-funding').replace('subject_choice','programme_choice')
(root/'work/search-loop-round6/test_programme_purpose_capture.proposed.py').write_text(t)
print('External capture control template prepared; no repo source/test edits.')
