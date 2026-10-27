from datetime import datetime

import pytest

from app.models.question import AlreadyAnswered, Question, QuestionStatus
from app.models.user import Role, User

ADMIN = User(name="Admin", email="admin@example.test", password_hash="x", role=Role.ADMIN)


def make_question():
    return Question(order_id="order1", asked_by="kari", text="Can the cake be made without milk?")


def test_new_question_is_open_and_not_answered():
    question = make_question()

    assert question.status == QuestionStatus.OPEN
    assert not question.is_answered()
    assert question.given_answer is None


def test_answer_saves_text_admin_and_time():
    question = make_question()
    before = datetime.now().replace(microsecond=0)

    question.answer("Yes, we can.", ADMIN)

    assert question.is_answered()
    assert question.status == QuestionStatus.ANSWERED
    assert question.given_answer.text == "Yes, we can."
    assert question.given_answer.answered_by == ADMIN.id
    assert question.given_answer.answered_at >= before


def test_question_can_not_be_answered_twice():
    question = make_question()
    question.answer("Yes, we can.", ADMIN)

    with pytest.raises(AlreadyAnswered):
        question.answer("No, sorry.", ADMIN)

    assert question.given_answer.text == "Yes, we can."  # the first answer is kept


def test_new_questions_get_different_ids():
    assert make_question().id != make_question().id


def test_status_labels():
    assert QuestionStatus.OPEN.label == "Open"
    assert QuestionStatus.ANSWERED.label == "Answered"
