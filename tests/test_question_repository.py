from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.food import Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.order import GuestGroup, Order, OrderLine
from app.models.order_repository import OrderRepository
from app.models.question import Answer, Question, QuestionStatus
from app.models.question_repository import QuestionRepository
from app.models.user import Role, User
from app.models.user_repository import UserRepository

WEDDING = Event("Wedding")


@pytest.fixture
def users(db):
    repo = UserRepository(db)
    admin = User(name="Admin", email="admin@example.test", password_hash="x", role=Role.ADMIN)
    kari = User(name="Kari", email="kari@example.test", password_hash="x")
    repo.add(admin)
    repo.add(kari)
    return admin, kari


@pytest.fixture
def orders(db, users):
    # Two orders for Kari, so questions can be on different orders.
    _, kari = users
    food = FoodItemRepository(db)
    food.add_event(WEDDING)
    soup = FoodItem(name="Fiskesuppe", desc="", price=Decimal("129.00"), min_order=10, events=[WEDDING])
    food.add(soup)

    repo = OrderRepository(db)
    result = []
    for event_date in (date(2027, 5, 15), date(2027, 6, 1)):
        order = Order(
            user_id=kari.id,
            event=WEDDING,
            event_date=event_date,
            number_of_guests=40,
            delivery_address="Bryggen 1, Bergen",
            lines=[OrderLine(soup.id, soup.name, 40, soup.price)],
            guest_groups=[GuestGroup("Adults", 40)],
        )
        repo.add(order)
        result.append(order)
    return result


@pytest.fixture
def repo(db):
    return QuestionRepository(db)


def make_question(order, user, asked_at, text="Can the cake be made without milk?"):
    return Question(order_id=order.id, asked_by=user.id, text=text, asked_at=asked_at)


def test_open_question_round_trip(repo, users, orders):
    _, kari = users
    question = make_question(orders[0], kari, datetime(2026, 10, 20, 9, 15))

    repo.add(question)

    assert repo.get_by_id(question.id) == question


def test_answered_question_round_trip(repo, users, orders):
    admin, kari = users
    question = make_question(orders[0], kari, datetime(2026, 10, 20, 9, 15))
    question.answer("Yes, we can.", admin)

    repo.add(question)
    saved = repo.get_by_id(question.id)

    assert saved.status == QuestionStatus.ANSWERED
    assert saved.given_answer == question.given_answer


def test_unknown_id_returns_none(repo):
    assert repo.get_by_id("no-such-id") is None


def test_get_by_order_returns_only_that_order_oldest_first(repo, users, orders):
    _, kari = users
    newer = make_question(orders[0], kari, datetime(2026, 10, 21, 12, 0))
    older = make_question(orders[0], kari, datetime(2026, 10, 20, 9, 15))
    other_order = make_question(orders[1], kari, datetime(2026, 10, 19, 8, 0))
    for question in (newer, older, other_order):
        repo.add(question)

    assert [q.id for q in repo.get_by_order(orders[0].id)] == [older.id, newer.id]


def test_get_open_skips_answered_questions(repo, users, orders):
    admin, kari = users
    open_question = make_question(orders[0], kari, datetime(2026, 10, 20, 9, 15))
    answered = make_question(orders[0], kari, datetime(2026, 10, 21, 9, 15))
    answered.answer("Yes.", admin)
    repo.add(open_question)
    repo.add(answered)

    assert [q.id for q in repo.get_open()] == [open_question.id]


def test_get_all_puts_open_first_then_newest(repo, users, orders):
    admin, kari = users
    old_open = make_question(orders[0], kari, datetime(2026, 10, 1, 9, 0))
    new_open = make_question(orders[1], kari, datetime(2026, 10, 5, 9, 0))
    new_answered = make_question(orders[0], kari, datetime(2026, 10, 10, 9, 0))
    new_answered.answer("Yes.", admin)
    old_answered = make_question(orders[1], kari, datetime(2026, 9, 1, 9, 0))
    old_answered.answer("No.", admin)
    for question in (old_open, new_answered, old_answered, new_open):
        repo.add(question)

    assert [q.id for q in repo.get_all()] == [new_open.id, old_open.id, new_answered.id, old_answered.id]


def test_update_saves_the_answer(repo, users, orders):
    admin, kari = users
    question = make_question(orders[0], kari, datetime(2026, 10, 20, 9, 15))
    repo.add(question)

    question.answer("Yes, we can.", admin)
    repo.update(question)
    saved = repo.get_by_id(question.id)

    assert saved.is_answered()
    assert saved.given_answer == Answer("Yes, we can.", admin.id, question.given_answer.answered_at)


def test_deleting_an_order_deletes_its_questions(db, repo, users, orders):
    _, kari = users
    question = make_question(orders[0], kari, datetime(2026, 10, 20, 9, 15))
    repo.add(question)

    # OrderRepository has no delete yet, so the test removes the order with SQL.
    with db:
        db.execute("DELETE FROM orders WHERE id = ?", (orders[0].id,))

    assert repo.get_by_id(question.id) is None
