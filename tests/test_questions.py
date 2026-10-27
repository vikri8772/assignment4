from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from werkzeug.security import generate_password_hash

from app.models.food import Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.order import GuestGroup, Order, OrderLine
from app.models.order_repository import OrderRepository
from app.models.question import MAX_TEXT_LENGTH, Question, QuestionStatus
from app.models.question_repository import QuestionRepository
from app.models.user import Role, User
from app.models.user_repository import UserRepository

PASSWORD = "testpassord"
WEDDING = Event("Wedding")


@pytest.fixture
def setup(db):
    users = UserRepository(db)
    admin = User(name="Admin", email="admin@example.test", password_hash=generate_password_hash(PASSWORD), role=Role.ADMIN)
    kari = User(name="Kari", email="kari@example.test", password_hash=generate_password_hash(PASSWORD))
    ola = User(name="Ola", email="ola@example.test", password_hash=generate_password_hash(PASSWORD))
    for user in (admin, kari, ola):
        users.add(user)

    food = FoodItemRepository(db)
    food.add_event(WEDDING)
    soup = FoodItem(name="Fiskesuppe", desc="", price=Decimal("129.00"), min_order=10, events=[WEDDING])
    food.add(soup)

    orders = OrderRepository(db)

    def add_order(user):
        order = Order(
            user_id=user.id,
            event=WEDDING,
            event_date=date(2027, 5, 15),
            number_of_guests=40,
            delivery_address=f"{user.name}s gate 1, Bergen",
            lines=[OrderLine(soup.id, soup.name, 40, soup.price)],
            guest_groups=[GuestGroup("Adults", 40)],
        )
        orders.add(order)
        return order

    karis_order = add_order(kari)
    olas_order = add_order(ola)

    questions = QuestionRepository(db)
    karis_question = Question(karis_order.id, kari.id, "Can the cake be made without milk?", datetime(2026, 10, 20, 9, 0))
    answered = Question(karis_order.id, kari.id, "Can you deliver at 17:00?", datetime(2026, 10, 21, 9, 0))
    answered.answer("Yes, 17:00 is fine.", admin)
    olas_question = Question(olas_order.id, ola.id, "Is the wrap packed separately?", datetime(2026, 10, 22, 9, 0))
    for question in (karis_question, answered, olas_question):
        questions.add(question)

    return karis_order, olas_order


def log_in(client, email):
    client.post("/account/login", data={"email": email, "password": PASSWORD})


@pytest.fixture
def kari(client, setup):
    log_in(client, "kari@example.test")
    return client


def questions_on(db, order):
    return QuestionRepository(db).get_by_order(order.id)


# C5 Questions about an order


def test_asking_requires_login(client, db, setup):
    karis_order, _ = setup

    response = client.post(f"/account/orders/{karis_order.id}/questions", data={"text": "Hello?"})

    assert response.status_code == 302
    assert "/account/login" in response.headers["Location"]
    assert len(questions_on(db, karis_order)) == 2


def test_order_page_shows_questions_and_answers(kari, setup):
    karis_order, _ = setup

    page = kari.get(f"/account/orders/{karis_order.id}").get_data(as_text=True)

    assert "Can the cake be made without milk?" in page
    assert "Not answered yet." in page
    assert "Can you deliver at 17:00?" in page
    assert "Yes, 17:00 is fine." in page
    assert "Is the wrap packed separately?" not in page  # Ola's question


def test_order_without_questions_shows_a_message(kari, db, setup):
    karis_order, _ = setup
    # A second order for Kari, with the same contents but no questions.
    empty_order = replace(karis_order, id=uuid4().hex)
    OrderRepository(db).add(empty_order)

    page = kari.get(f"/account/orders/{empty_order.id}").get_data(as_text=True)

    assert "No questions about this order yet." in page
    assert "Can the cake be made without milk?" not in page


def test_asking_a_question_saves_it_as_open(kari, db, setup):
    karis_order, _ = setup

    response = kari.post(f"/account/orders/{karis_order.id}/questions", data={"text": "  Is there parking?  "})

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/account/orders/{karis_order.id}")
    new = questions_on(db, karis_order)[-1]
    assert new.text == "Is there parking?"
    assert new.status == QuestionStatus.OPEN
    page = kari.get(response.headers["Location"]).get_data(as_text=True)
    assert "Your question is sent" in page
    assert "Is there parking?" in page


@pytest.mark.parametrize("text", ["", "   ", "x" * (MAX_TEXT_LENGTH + 1)])
def test_empty_or_too_long_question_gives_400_and_saves_nothing(kari, db, setup, text):
    karis_order, _ = setup

    response = kari.post(f"/account/orders/{karis_order.id}/questions", data={"text": text})

    assert response.status_code == 400
    assert len(questions_on(db, karis_order)) == 2


def test_too_long_question_keeps_the_text(kari, setup):
    karis_order, _ = setup
    text = "x" * (MAX_TEXT_LENGTH + 1)

    page = kari.post(f"/account/orders/{karis_order.id}/questions", data={"text": text}).get_data(as_text=True)

    assert f"at most {MAX_TEXT_LENGTH} characters" in page
    assert text in page


def test_question_of_max_length_is_accepted(kari, db, setup):
    karis_order, _ = setup

    response = kari.post(f"/account/orders/{karis_order.id}/questions", data={"text": "x" * MAX_TEXT_LENGTH})

    assert response.status_code == 302
    assert len(questions_on(db, karis_order)) == 3


def test_asking_on_someone_elses_order_gives_404(kari, db, setup):
    _, olas_order = setup

    response = kari.post(f"/account/orders/{olas_order.id}/questions", data={"text": "Hello?"})

    assert response.status_code == 404
    assert len(questions_on(db, olas_order)) == 1


def test_asking_on_unknown_order_gives_404(kari, db, setup):
    response = kari.post("/account/orders/no-such-id/questions", data={"text": "Hello?"})

    assert response.status_code == 404
    assert len(QuestionRepository(db).get_all()) == 3
