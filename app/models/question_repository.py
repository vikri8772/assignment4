from datetime import datetime

from app.models.question import Answer, Question, QuestionStatus


class QuestionRepository:
    """Saves and loads Questions with their answers. The rest of the app never sees the table."""

    def __init__(self, db):
        self.db = db

    def get_by_id(self, id):
        row = self.db.execute("SELECT * FROM question WHERE id = ?", (id,)).fetchone()
        if row is None:
            return None
        return self._to_question(row)

    def get_by_order(self, order_id):
        # C5: the questions on one order, oldest first, so they read like a conversation.
        rows = self.db.execute(
            "SELECT * FROM question WHERE order_id = ? ORDER BY asked_at", (order_id,)
        ).fetchall()
        return [self._to_question(row) for row in rows]

    def get_open(self):
        # Oldest first: the question that has waited longest is on top.
        rows = self.db.execute(
            "SELECT * FROM question WHERE status = ? ORDER BY asked_at", (QuestionStatus.OPEN.value,)
        ).fetchall()
        return [self._to_question(row) for row in rows]

    def get_all(self):
        # A4: open questions first, then the newest.
        rows = self.db.execute(
            "SELECT * FROM question ORDER BY status = ?, asked_at DESC", (QuestionStatus.ANSWERED.value,)
        ).fetchall()
        return [self._to_question(row) for row in rows]

    def add(self, question):
        answer = question.given_answer
        with self.db:
            self.db.execute(
                """
                INSERT INTO question (id, order_id, asked_by, text, asked_at, status,
                                      answer_text, answered_by, answered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question.id,
                    question.order_id,
                    question.asked_by,
                    question.text,
                    question.asked_at.isoformat(),
                    question.status.value,
                    answer.text if answer else None,
                    answer.answered_by if answer else None,
                    answer.answered_at.isoformat() if answer else None,
                ),
            )

    def update(self, question):
        # Saves what changes when an admin answers (A4).
        answer = question.given_answer
        with self.db:
            self.db.execute(
                """
                UPDATE question
                SET status = ?, answer_text = ?, answered_by = ?, answered_at = ?
                WHERE id = ?
                """,
                (
                    question.status.value,
                    answer.text if answer else None,
                    answer.answered_by if answer else None,
                    answer.answered_at.isoformat() if answer else None,
                    question.id,
                ),
            )

    def _to_question(self, row):
        answer = None
        if row["answer_text"] is not None:
            answer = Answer(
                text=row["answer_text"],
                answered_by=row["answered_by"],
                answered_at=datetime.fromisoformat(row["answered_at"]),
            )
        return Question(
            id=row["id"],
            order_id=row["order_id"],
            asked_by=row["asked_by"],
            text=row["text"],
            asked_at=datetime.fromisoformat(row["asked_at"]),
            status=QuestionStatus(row["status"]),
            given_answer=answer,
        )
