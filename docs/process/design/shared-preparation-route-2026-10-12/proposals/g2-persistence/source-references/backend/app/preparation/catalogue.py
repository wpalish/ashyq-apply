"""Unimatch-authored original starter items; official resources remain external links.

These tiny formative lessons are not official exam samples, calibrated exams or
score predictors. Content is versioned; changing an item requires a new version.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from app.schemas.preparation import (
    AnswerFeedback,
    Choice,
    ExamSummary,
    LessonSummary,
    PreparationCatalogue,
    PreparationLesson,
    Question,
    StudyAttemptIn,
    TrackId,
    TrackSummary,
)

CONTENT_VERSION = "starter-2026-10-11-v1"
NOTICE = (
    "Original starter practice, not official exam items or a full course. Raw correct/total is "
    "not an IELTS band, SAT score, certificate or admission prediction. Official resources are "
    "external links; test booking and fees are separate. Planned courses have no starter lessons."
)


@dataclass(frozen=True)
class Item:
    id: str
    prompt: str
    choices: tuple[tuple[str, str], ...]
    correct_choice_id: str
    explanation: str


@dataclass(frozen=True)
class Lesson:
    id: str
    track_id: TrackId
    title: str
    introduction: str
    items: tuple[Item, ...]


LESSONS = (
    Lesson(
        "ielts-reading-1",
        "ielts_reading",
        "Reading: stated evidence and inference",
        "Read the original short passage in each question. Select what the text supports. "
        "This practises reading only, without proving test-type acceptance or other skill readiness.",
        (
            Item(
                "ir-1",
                "A town library opened its study room on Sundays for a six-week trial. Visits rose, "
                "but staff have not yet compared running costs. Which statement is supported?",
                (
                    ("a", "Sunday opening is already a permanent policy."),
                    ("b", "Visits increased during the trial."),
                    ("c", "The trial reduced running costs."),
                ),
                "b",
                "The passage explicitly states visits rose. Permanence and cost savings "
                "are not stated; missing evidence is not a positive finding.",
            ),
            Item(
                "ir-2",
                "Two gardens used the same seed mix. Garden A was watered daily, while Garden B "
                "was watered twice a week. The report gives no harvest figures. Can the text "
                "establish that Garden A produced more vegetables?",
                (
                    ("a", "Yes, daily watering proves a larger harvest."),
                    ("b", "No, the text says Garden B produced more."),
                    ("c", "The harvest comparison is not given."),
                ),
                "c",
                "Different watering schedules are reported, but no harvest comparison is "
                "given. Neither a larger nor a smaller harvest is established.",
            ),
            Item(
                "ir-3",
                "The museum expected the roof repair to finish in May. Heavy rain delayed work "
                "and the roof reopened in June. What caused the delay?",
                (
                    ("a", "Heavy rain."),
                    ("b", "A change of museum director."),
                    ("c", "A shortage of visitors."),
                ),
                "a",
                "Heavy rain is the stated cause. The other options add details absent "
                "from the passage.",
            ),
        ),
    ),
    Lesson(
        "sat-math-1",
        "sat_math",
        "Math: linear relations and proportional reasoning",
        "Use a linear equation, a percentage and a rate. These original questions are "
        "formative practice, not an adaptive Digital SAT module.",
        (
            Item(
                "sm-1",
                "A bicycle rental costs 6 units plus 4 units per hour. The total is "
                "22 units. How many hours were rented?",
                (("a", "3"), ("b", "4"), ("c", "7")),
                "b",
                "Solve 6 + 4h = 22: subtract 6 to get 4h = 16, then divide by 4 to get h = 4.",
            ),
            Item(
                "sm-2",
                "A club has 80 members. Exactly 25% volunteer at an event. "
                "How many members volunteer?",
                (("a", "20"), ("b", "25"), ("c", "60")),
                "a",
                "25% is one quarter. One quarter of 80 is 20; 25 is a percentage, not a count.",
            ),
            Item(
                "sm-3",
                "A machine packs 18 boxes in 3 minutes at a constant rate. "
                "At that rate, how many boxes does it pack in 5 minutes?",
                (("a", "20"), ("b", "27"), ("c", "30")),
                "c",
                "The rate is 18 / 3 = 6 boxes per minute. In 5 minutes it packs 6 × 5 = 30.",
            ),
        ),
    ),
    Lesson(
        "sat-rw-1",
        "sat_reading_writing",
        "Reading and Writing: evidence and sentence clarity",
        "Choose a supported inference, a complete sentence and a logical transition. "
        "These original questions are not College Board items or an official section score.",
        (
            Item(
                "sr-1",
                "A survey found that commuters who used a new bus route reported "
                "shorter journeys. It did not measure journeys of people using other routes. "
                "Which conclusion is supported?",
                (
                    ("a", "Every commuter in the city now has a shorter journey."),
                    ("b", "Users of the new route reported shorter journeys."),
                    ("c", "The new route caused all traffic delays to disappear."),
                ),
                "b",
                "The survey reports the experiences of new-route users only. It does not "
                "establish a city-wide effect or that traffic delays disappeared.",
            ),
            Item(
                "sr-2",
                "Choose the complete, grammatically clear sentence.",
                (
                    ("a", "Because the telescope was repaired."),
                    ("b", "The telescope, which the technicians repaired."),
                    ("c", "The technicians repaired the telescope."),
                ),
                "c",
                "Option c has a subject and a finite main verb. Options a and b leave a "
                "dependent construction without a complete main clause.",
            ),
            Item(
                "sr-3",
                "The first design used fewer materials. ___, it was less durable. "
                "Which transition best expresses the contrast?",
                (("a", "However"), ("b", "Therefore"), ("c", "For example")),
                "a",
                "However signals a contrast between a material-saving benefit and a "
                "durability drawback. Therefore claims a causal result not established here.",
            ),
        ),
    ),
)

EXAMS = (
    ExamSummary(
        id="ielts_academic",
        title="IELTS Academic",
        role="language",
        course_status="starter",
        track_ids=["ielts_reading"],
        official_info_urls=["https://ielts.org/take-a-test/test-types/ielts-academic-test"],
        official_practice_urls=[
            "https://ielts.org/take-a-test/preparation-resources/sample-test-questions/academic-test"
        ],
        notice="Starter covers Reading only. Verify overall AND component minima and the "
        "recipient's accepted delivery type/retake/waiver policy. Recognition is not acceptance "
        "of General Training, Online, UKVI or One Skill Retake. Validity is recipient-specific.",
        checked_date="2026-10-11",
    ),
    ExamSummary(
        id="digital_sat",
        title="Digital SAT",
        role="academic",
        course_status="starter",
        track_ids=["sat_math", "sat_reading_writing"],
        official_info_urls=["https://satsuite.collegeboard.org/sat/whats-on-the-test/structure"],
        official_practice_urls=[
            "https://satsuite.collegeboard.org/practice/practice-tests/bluebook",
            "https://satsuite.collegeboard.org/practice/student-question-bank",
        ],
        notice="Original non-adaptive starters, not Bluebook or an official SAT score. Verify "
        "the programme's required/optional/not-considered, score-age and superscore policies; "
        "admission and scholarship requirements can differ. No universal two-year expiry.",
        checked_date="2026-10-11",
    ),
    ExamSummary(
        id="toefl_ibt",
        title="TOEFL iBT",
        role="language",
        course_status="planned",
        track_ids=[],
        official_info_urls=[
            "https://www.ets.org/toefl/test-takers/ibt/scores/understand-scores.html"
        ],
        official_practice_urls=["https://www.ets.org/toefl/test-takers/ibt/prepare.html"],
        notice="No starter course yet. Tests from 21 January 2026 use 1–6 bands with a "
        "transitional comparable overall estimate. Preserve report scale/edition/date/components; "
        "do not invent old section conversions. Recipient acceptance of edition/MyBest/Home "
        "Edition must be checked. Existing profile fields support the legacy scale only.",
        checked_date="2026-10-11",
    ),
    ExamSummary(
        id="det",
        title="Duolingo English Test",
        role="language",
        course_status="planned",
        track_ids=[],
        official_info_urls=[
            "https://blog.englishtest.duolingo.com/how-is-the-duolingo-english-test-scored/"
        ],
        official_practice_urls=[
            "https://blog.englishtest.duolingo.com/duolingo-english-test-readiness/"
        ],
        notice="No starter course yet. Preserve the certificate's component schema and date. "
        "An owner recognition directory does not settle programme/intake or visa acceptance; "
        "a practice estimated range is not a certified result.",
        checked_date="2026-10-11",
    ),
    ExamSummary(
        id="hsk_hskk",
        title="HSK / HSK Speaking (HSKK)",
        role="language",
        course_status="planned",
        track_ids=[],
        official_info_urls=[
            "https://www.chinesetest.cn/HSK",
            "https://www.chinesetest.cn/hskk/",
            "https://old.chinesetest.cn/gonewcontent.do?flag=kdnew&id=51336883",
        ],
        official_practice_urls=["https://www.chinesetest.cn/"],
        notice="No starter course yet. Level, speaking report and booked edition matter. "
        "The announced worldwide HSK3.0 rollout on 13 December 2026 is still future at this "
        "catalogue's check date; a published syllabus does not prove a booked test switched. "
        "Check recipient/version-specific validity; HSK is not a universal China requirement.",
        checked_date="2026-10-11",
    ),
    ExamSummary(
        id="csca",
        title="CSCA",
        role="academic",
        course_status="planned",
        track_ids=[],
        official_info_urls=["https://csca.cn/about/examintro"],
        official_practice_urls=["https://csca.cn/testprep/"],
        notice="No starter course yet. Mathematics, Physics, Chemistry and Professional Chinese "
        "depend on the selected university/programme/route. Distinct from HSK. No universal "
        "China mandate, entry score or score-validity duration is established. 2026 adoption "
        "examples are not 2027 requirements.",
        checked_date="2026-10-11",
    ),
)


def catalogue() -> PreparationCatalogue:
    titles: dict[TrackId, str] = {
        "ielts_reading": "IELTS Reading",
        "sat_math": "SAT Math",
        "sat_reading_writing": "SAT Reading and Writing",
    }
    return PreparationCatalogue(
        version=CONTENT_VERSION,
        tracks=[
            TrackSummary(
                id=track,
                title=title,
                lesson_ids=[lesson.id for lesson in LESSONS if lesson.track_id == track],
            )
            for track, title in titles.items()
        ],
        lessons=[
            LessonSummary(
                id=lesson.id,
                track_id=lesson.track_id,
                title=lesson.title,
                question_count=len(lesson.items),
            )
            for lesson in LESSONS
        ],
        exams=list(EXAMS),
        notice=NOTICE,
    )


def get_lesson(lesson_id: str, version: str) -> Lesson:
    if version != CONTENT_VERSION:
        raise ValueError("Unknown content version")
    for lesson in LESSONS:
        if lesson.id == lesson_id:
            return lesson
    raise ValueError("Unknown lesson")


def public_lesson(lesson: Lesson) -> PreparationLesson:
    return PreparationLesson(
        id=lesson.id,
        track_id=lesson.track_id,
        title=lesson.title,
        version=CONTENT_VERSION,
        introduction=lesson.introduction,
        questions=[
            Question(
                id=item.id,
                prompt=item.prompt,
                choices=[Choice(id=key, text=text) for key, text in item.choices],
            )
            for item in lesson.items
        ],
    )


def request_digest(payload: StudyAttemptIn) -> str:
    """Order-independent payload binding, also works for historical UUID replays."""
    canonical = {
        "lesson_id": payload.lesson_id,
        "version": payload.version,
        "answers": sorted(
            (answer.model_dump() for answer in payload.answers),
            key=lambda answer: (answer["question_id"], answer["choice_id"]),
        ),
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def grade(payload: StudyAttemptIn) -> tuple[list[dict], list[dict], int]:
    lesson = get_lesson(payload.lesson_id, payload.version)
    answers = {answer.question_id: answer.choice_id for answer in payload.answers}
    if len(answers) != len(payload.answers) or set(answers) != {item.id for item in lesson.items}:
        raise ValueError("Answer every question exactly once")
    feedback = []
    for item in lesson.items:
        selected = answers[item.id]
        if selected not in {key for key, _ in item.choices}:
            raise ValueError("Unknown choice for question")
        feedback.append(
            AnswerFeedback(
                question_id=item.id,
                selected_choice_id=selected,
                correct_choice_id=item.correct_choice_id,
                correct=selected == item.correct_choice_id,
                explanation=item.explanation,
            ).model_dump(mode="json")
        )
    canonical_answers = [
        {"question_id": item.id, "choice_id": answers[item.id]} for item in lesson.items
    ]
    return canonical_answers, feedback, sum(item["correct"] for item in feedback)
