"""Original pack format/content/version controls; no database or providers."""

import hashlib
import json
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.preparation.catalogue import (
    CONTENT_VERSION,
    LESSONS,
    catalogue,
    get_lesson,
    grade,
    public_lesson,
    request_digest,
)
from app.preparation.learning_pack import (
    PACK_LESSONS,
    PACK_VERSION,
    TRACK_ORDER,
    ChoiceItem,
    ShortItem,
    completed_lesson_refs,
    digest_dispatch,
    grade_dispatch,
    lesson_dispatch,
    normalize_short,
    pack_catalogue,
    use_learning_pack,
)
from app.schemas.preparation import LearningPackStudyAttemptIn, StudyAttemptIn

SHORT_ID = "ielts-reading-completion-1"
FIXED_UUID = UUID("251d4011-4ec6-4c6a-a6f9-3992204861c9")
EXPECTED_KEYS = {
    "sat-quadratic-structure-1": ["b", "d", "a", "c", "b"],
    "sat-data-interpretation-1": ["b", "c", "c", "b", "d"],
    "sat-grammar-transitions-1": ["c", "b", "b", "a", "b"],
    "ielts-reading-headings-1": ["v", "iii", "i", "ii", "iv"],
    "ielts-reading-features-1": ["b", "a", "c", "d", "a"],
    SHORT_ID: [
        "dividers",
        "36",
        "condition sheet",
        "briefing session",
        "download code",
    ],
}


def pack_payload(lesson_id=SHORT_ID):
    lesson = next(item for item in PACK_LESSONS if item.id == lesson_id)
    answers = [
        {
            "question_id": item.id,
            "text" if isinstance(item, ShortItem) else "choice_id": key,
        }
        for item, key in zip(lesson.items, EXPECTED_KEYS[lesson_id], strict=True)
    ]
    return LearningPackStudyAttemptIn(
        attempt_id=FIXED_UUID,
        lesson_id=lesson_id,
        version=PACK_VERSION,
        answers=answers,
    )


@pytest.mark.parametrize("lesson_id", EXPECTED_KEYS)
def test_all_thirty_reviewed_keys_grade_once_with_stored_selected_answers(lesson_id):
    payload = pack_payload(lesson_id)
    answers, feedback, correct = grade_dispatch(payload)
    assert correct == len(answers) == len(feedback) == 5
    assert answers == [answer.model_dump() for answer in payload.answers]
    assert all(item["correct"] and item["explanation"] for item in feedback)
    assert len({answer["question_id"] for answer in answers}) == 5


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda lesson: lesson.id)
def test_original_public_projection_digest_grade_are_exact(lesson):
    assert (
        lesson_dispatch(lesson.id, CONTENT_VERSION).model_dump()
        == public_lesson(get_lesson(lesson.id, CONTENT_VERSION)).model_dump()
    )
    payload = StudyAttemptIn(
        attempt_id=FIXED_UUID,
        lesson_id=lesson.id,
        version=CONTENT_VERSION,
        answers=[
            {"question_id": item.id, "choice_id": item.correct_choice_id} for item in lesson.items
        ],
    )
    canonical = {
        "lesson_id": lesson.id,
        "version": CONTENT_VERSION,
        "answers": sorted(
            [answer.model_dump() for answer in payload.answers],
            key=lambda answer: (answer["question_id"], answer["choice_id"]),
        ),
    }
    frozen_digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert digest_dispatch(payload) == request_digest(payload) == frozen_digest
    assert grade_dispatch(payload) == grade(payload)
    assert all(set(item) == {"question_id", "choice_id"} for item in canonical["answers"])


def test_default_selector_and_original_catalogue_are_preserved():
    assert not use_learning_pack(None) and not use_learning_pack(CONTENT_VERSION)
    assert use_learning_pack(PACK_VERSION)
    assert catalogue().version == CONTENT_VERSION
    assert len(catalogue().lessons) == 3
    with pytest.raises(ValueError, match="Unknown catalogue version"):
        use_learning_pack("invented")


def test_legacy_frozen_digest_matches_independent_literal_not_a_pack_projection():
    payload = StudyAttemptIn(
        attempt_id=FIXED_UUID,
        lesson_id="ielts-reading-1",
        version="starter-2026-10-11-v1",
        answers=[
            {"question_id": "ir-1", "choice_id": "b"},
            {"question_id": "ir-2", "choice_id": "c"},
            {"question_id": "ir-3", "choice_id": "a"},
        ],
    )
    assert (
        digest_dispatch(payload)
        == "ee707dd54e851d0df1f8a7db54a78cbd148c0302a136cc1dc7e24dc99cde0c7b"
    )


def test_pack_orders_all_nine_lessons_and_versions_without_answer_keys():
    result = pack_catalogue().model_dump(mode="json")
    assert result["version"] == PACK_VERSION and len(result["lessons"]) == 9
    assert {track["id"]: tuple(track["lesson_ids"]) for track in result["tracks"]} == TRACK_ORDER
    assert [lesson["id"] for lesson in result["lessons"]] == [
        lesson_id for ids in TRACK_ORDER.values() for lesson_id in ids
    ]
    starters = {lesson.id for lesson in LESSONS}
    assert all(
        item["version"] == (CONTENT_VERSION if item["id"] in starters else PACK_VERSION)
        for item in result["lessons"]
    )
    assert result["exams"] == catalogue().model_dump(mode="json")["exams"]
    assert not any(
        f'"{field}":' in json.dumps(result)
        for field in ("correct_choice_id", "accepted_answers", "explanation")
    )


@pytest.mark.parametrize("lesson_id", EXPECTED_KEYS)
def test_initial_lessons_have_five_questions_full_material_and_no_private_keys(
    lesson_id,
):
    result = lesson_dispatch(lesson_id, PACK_VERSION).model_dump(mode="json")
    assert len(result["questions"]) == 5 and result["unofficial"]
    assert len(result["introduction"]) > 1200
    assert (
        "Teacher key" not in result["introduction"]
        and "Instructor answer key" not in result["introduction"]
    )
    assert not any(
        f'"{field}":' in json.dumps(result)
        for field in ("correct_choice_id", "accepted_answers", "explanation")
    )
    if lesson_id == SHORT_ID:
        assert all(
            question["answer_format"] == "short_answer" and question["max_words"] == 2
            for question in result["questions"]
        )
    else:
        assert all(
            "choices" in question and "answer_format" not in question
            for question in result["questions"]
        )


def test_all_question_ids_are_distinct_keys_known_and_explanations_present():
    ids = [item.id for lesson in PACK_LESSONS for item in lesson.items]
    assert len(ids) == len(set(ids)) == 30
    assert all(len(lesson.items) == 5 for lesson in PACK_LESSONS)
    for lesson in PACK_LESSONS:
        for item in lesson.items:
            assert item.prompt and item.explanation
            if isinstance(item, ChoiceItem):
                assert len(item.choices) == len({choice[0] for choice in item.choices})
                assert item.correct_choice_id in {choice[0] for choice in item.choices}
            else:
                assert all(
                    len(normalize_short(answer).split()) <= item.max_words
                    for answer in item.accepted_answers
                )


@pytest.mark.parametrize(
    "lesson_id,version",
    [
        ("sat-math-1", PACK_VERSION),
        (SHORT_ID, CONTENT_VERSION),
        (SHORT_ID, "old"),
        ("unknown", PACK_VERSION),
    ],
)
def test_exact_lesson_version_pairs_required(lesson_id, version):
    with pytest.raises(ValueError):
        lesson_dispatch(lesson_id, version)


@pytest.mark.parametrize(
    "item_index,text",
    [
        (0, "DIVIDERS."),
        (1, "36"),
        (2, "sheet"),
        (2, "  CONDITION\tSHEET . "),
        (3, "briefing"),
        (3, "session"),
        (3, "Briefing  session."),
        (4, "code"),
        (4, "download code"),
    ],
)
def test_all_approved_short_forms_case_whitespace_one_period(item_index, text):
    data = pack_payload().model_dump(mode="json")
    data["answers"][item_index]["text"] = text
    payload = LearningPackStudyAttemptIn.model_validate(data)
    answers, feedback, correct = grade_dispatch(payload)
    assert correct == 5
    assert feedback[item_index]["selected_text"] == payload.answers[item_index].text
    assert answers[item_index]["text"] == payload.answers[item_index].text


@pytest.mark.parametrize(
    "item_index,text",
    [
        (0, "foam dividers"),
        (0, "divider"),
        (0, "dividers.."),
        (0, "dividers extra"),
        (1, "thirty six"),
        (2, "inventory"),
        (2, "the condition sheet"),
        (3, "written test"),
        (4, "memory stick"),
        (4, "codeword"),
        (4, "code!"),
    ],
)
def test_short_grader_rejects_wrong_details_fuzzy_substrings_and_over_word_limit(item_index, text):
    data = pack_payload().model_dump(mode="json")
    data["answers"][item_index]["text"] = text
    _, feedback, correct = grade_dispatch(LearningPackStudyAttemptIn.model_validate(data))
    assert correct == 4 and not feedback[item_index]["correct"]


@pytest.mark.parametrize(
    "failure",
    ["missing", "duplicate", "unknown_question", "wrong_format", "unknown_choice"],
)
def test_invalid_question_sets_and_formats_fail_without_keys(failure):
    data = pack_payload("sat-quadratic-structure-1").model_dump(mode="json")
    if failure == "missing":
        data["answers"].pop()
    elif failure == "duplicate":
        data["answers"][1] = data["answers"][0]
    elif failure == "unknown_question":
        data["answers"][0]["question_id"] = "not-in-lesson"
    elif failure == "wrong_format":
        data["answers"][0] = {
            "question_id": data["answers"][0]["question_id"],
            "text": "b",
        }
    else:
        data["answers"][0]["choice_id"] = "unknown"
    with pytest.raises(ValueError) as exc:
        grade_dispatch(LearningPackStudyAttemptIn.model_validate(data))
    assert "correct_choice_id" not in str(exc.value) and "explanation" not in str(exc.value)


@pytest.mark.parametrize(
    "answer", [{"text": "x" * 101}, {"text": ""}, {"text": "code", "choice_id": "a"}]
)
def test_short_input_bounds_and_exclusive_answer_shape(answer):
    data = pack_payload().model_dump(mode="json")
    data["answers"][0] = {"question_id": data["answers"][0]["question_id"], **answer}
    with pytest.raises(ValidationError):
        LearningPackStudyAttemptIn.model_validate(data)


def test_short_digest_reorder_replay_and_raw_payload_conflicts():
    payload = pack_payload()
    reordered = payload.model_copy(update={"answers": list(reversed(payload.answers))})
    assert digest_dispatch(reordered) == digest_dispatch(payload)
    data = payload.model_dump(mode="json")
    data["answers"][2]["text"] = "sheet"
    assert digest_dispatch(LearningPackStudyAttemptIn.model_validate(data)) != digest_dispatch(
        payload
    )
    assert grade_dispatch(LearningPackStudyAttemptIn.model_validate(data))[2] == 5


def test_first_pack_receipt_preserves_raw_text_and_input_order_without_normalizing_storage():
    data = pack_payload().model_dump(mode="json")
    data["answers"][2]["text"] = "  CONDITION\tSHEET .  "
    data["answers"].reverse()
    submitted = LearningPackStudyAttemptIn.model_validate(data)
    answers, feedback, correct = grade_dispatch(submitted)
    assert answers == data["answers"] and correct == 5
    assert feedback[2]["selected_text"] == "  CONDITION\tSHEET .  "
    assert feedback[2]["correct"]
    data["answers"][0]["text"] = "   "
    with pytest.raises(ValidationError):
        LearningPackStudyAttemptIn.model_validate(data)


def test_completions_require_the_exact_registered_pair_and_do_not_imply_mastery():
    rows = [
        ("sat-math-1", CONTENT_VERSION),
        (SHORT_ID, PACK_VERSION),
        (SHORT_ID, CONTENT_VERSION),
        ("sat-math-1", PACK_VERSION),
        ("unknown", PACK_VERSION),
        (SHORT_ID, PACK_VERSION),
    ]
    refs = [ref.model_dump() for ref in completed_lesson_refs(rows)]
    assert refs == [
        {"lesson_id": SHORT_ID, "version": PACK_VERSION},
        {"lesson_id": "sat-math-1", "version": CONTENT_VERSION},
    ]
