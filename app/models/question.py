from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from app.models.user import User


class QuestionStatus(Enum):
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"

    @property
    def label(self) -> str:
        return self.value.capitalize()  # ANSWERED -> "Answered"


# Longest question or answer, checked by the controllers (C5, A4).
MAX_TEXT_LENGTH = 1000


class AlreadyAnswered(Exception):
    """A question can only be answered once, see docs/plans/c5-question-status-state.md."""


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


@dataclass
class Answer:
    text: str
    answered_by: str  # the admin's user id
    answered_at: datetime = field(default_factory=_now)


@dataclass
class Question:
    order_id: str
    asked_by: str  # the customer's user id
    text: str
    asked_at: datetime = field(default_factory=_now)
    status: QuestionStatus = QuestionStatus.OPEN
    # Not called "answer", because that is the name of the method below.
    given_answer: Answer | None = None
    id: str = field(default_factory=lambda: uuid4().hex)

    def is_answered(self) -> bool:
        return self.status == QuestionStatus.ANSWERED

    def answer(self, text: str, admin: User):
        if self.is_answered():
            raise AlreadyAnswered("This question is already answered.")
        self.given_answer = Answer(text=text, answered_by=admin.id)
        self.status = QuestionStatus.ANSWERED
