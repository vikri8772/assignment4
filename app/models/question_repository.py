from datetime import datetime

from app.models.db import IntegrityError
from app.models.question import Answer, Question, QuestionStatus

# Returns a question with who asked it, which order it is about, and who answered it.
# A question whose order is gone is not found, because ABOUT must point to an order.
_RETURN_QUESTION = """
    MATCH (asker:User)-[:ASKED]->(q)-[:ABOUT]->(o:Order)
    OPTIONAL MATCH (admin:User)-[:ANSWERED]->(q)
    RETURN q, asker.id AS askedBy, o.id AS orderId, admin.id AS answeredBy
"""

# Links the admin who answered, if any. Used at the end of add() and update().
_LINK_ANSWERER = """
    FOREACH (a IN CASE WHEN admin IS NULL THEN [] ELSE [admin] END | CREATE (a)-[:ANSWERED]->(q))
    RETURN q.id AS id
"""


class QuestionRepository:
    """Saves and loads Questions as (:Question) nodes: (:User)-[:ASKED]->(q)-[:ABOUT]->(:Order),
    and (:User)-[:ANSWERED]->(q) once an admin has answered. The rest of the app never sees Neo4j."""

    def __init__(self, db):
        self.db = db

    def get_by_id(self, id):
        row = self.db.query_one("MATCH (q:Question {id: $id})" + _RETURN_QUESTION, id=id)
        if row is None:
            return None
        return self._to_question(row)

    def get_by_order(self, order_id):
        # C5: the questions on one order, oldest first, so they read like a conversation.
        rows = self.db.query(
            "MATCH (q:Question)-[:ABOUT]->(:Order {id: $order_id})" + _RETURN_QUESTION + "ORDER BY q.askedAt",
            order_id=order_id,
        )
        return [self._to_question(row) for row in rows]

    def get_open(self):
        # Oldest first: the question that has waited longest is on top.
        rows = self.db.query(
            "MATCH (q:Question {status: $open})" + _RETURN_QUESTION + "ORDER BY q.askedAt",
            open=QuestionStatus.OPEN.value,
        )
        return [self._to_question(row) for row in rows]

    def get_all(self):
        # A4: open questions first, then the newest. (false sorts before true.)
        rows = self.db.query(
            "MATCH (q:Question)" + _RETURN_QUESTION + "ORDER BY q.status = $answered, q.askedAt DESC",
            answered=QuestionStatus.ANSWERED.value,
        )
        return [self._to_question(row) for row in rows]

    def add(self, question):
        # If the customer, the order or the answering admin doesn't exist, nothing is created.
        answer = question.given_answer
        row = self.db.query_one(
            """
            MATCH (asker:User {id: $asked_by}), (o:Order {id: $order_id})
            OPTIONAL MATCH (admin:User {id: $answered_by})
            WITH asker, o, admin
            WHERE $answered_by IS NULL OR admin IS NOT NULL
            CREATE (asker)-[:ASKED]->(q:Question)-[:ABOUT]->(o)
            SET q = $props
            """
            + _LINK_ANSWERER,
            asked_by=question.asked_by,
            order_id=question.order_id,
            answered_by=answer.answered_by if answer else None,
            props=self._properties(question),
        )
        if row is None:
            raise IntegrityError("The question was not saved: the customer, the order or the admin doesn't exist.")

    def update(self, question):
        # Saves what changes when an admin answers (A4).
        answer = question.given_answer
        self.db.query(
            """
            MATCH (q:Question {id: $id})
            OPTIONAL MATCH (admin:User {id: $answered_by})
            SET q.status = $status, q.answerText = $answer_text, q.answeredAt = $answered_at
            WITH q, admin
            CALL (q) { MATCH (:User)-[r:ANSWERED]->(q) DELETE r }
            """
            + _LINK_ANSWERER,
            id=question.id,
            answered_by=answer.answered_by if answer else None,
            status=question.status.value,
            answer_text=answer.text if answer else None,  # null removes the property
            answered_at=answer.answered_at.isoformat() if answer else None,
        )

    def _properties(self, question):
        props = {
            "id": question.id,
            "text": question.text,
            "askedAt": question.asked_at.isoformat(),  # e.g. "2026-10-20T09:15:00"
            "status": question.status.value,
        }
        answer = question.given_answer
        if answer:
            props["answerText"] = answer.text
            props["answeredAt"] = answer.answered_at.isoformat()
        return props

    def _to_question(self, row):
        q = row["q"]
        answer = None
        if q.get("answerText") is not None:
            answer = Answer(
                text=q["answerText"],
                answered_by=row["answeredBy"],
                answered_at=datetime.fromisoformat(q["answeredAt"]),
            )
        return Question(
            id=q["id"],
            order_id=row["orderId"],
            asked_by=row["askedBy"],
            text=q["text"],
            asked_at=datetime.fromisoformat(q["askedAt"]),
            status=QuestionStatus(q["status"]),
            given_answer=answer,
        )
