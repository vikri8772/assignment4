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


# A4 Answer questions


@pytest.fixture
def admin(client, setup):
    log_in(client, "admin@example.test")
    return client


def find_question(db, text):
    return next(q for q in QuestionRepository(db).get_all() if q.text == text)


def admin_urls(db):
    question = find_question(db, "Can the cake be made without milk?")
    return [
        ("get", "/admin/questions"),
        ("get", f"/admin/questions/{question.id}"),
        ("post", f"/admin/questions/{question.id}/answer"),
    ]


def test_admin_pages_redirect_logged_out_visitors(client, db, setup):
    for method, url in admin_urls(db):
        response = getattr(client, method)(url, data={"text": "Yes."})
        assert response.status_code == 302, url
        assert "/account/login" in response.headers["Location"]


def test_admin_pages_give_403_to_customers(kari, db, setup):
    for method, url in admin_urls(db):
        assert getattr(kari, method)(url, data={"text": "Yes."}).status_code == 403, url

    assert not find_question(db, "Can the cake be made without milk?").is_answered()


def test_list_shows_open_questions_first(admin, setup):
    page = admin.get("/admin/questions").get_data(as_text=True)

    # Open, newest first: Ola's (22 Oct), Kari's cake (20 Oct). Then the answered one (21 Oct).
    olas = page.index("Is the wrap packed separately?")
    cake = page.index("Can the cake be made without milk?")
    answered = page.index("Can you deliver at 17:00?")
    assert olas < cake < answered
    assert "Kari" in page and "Ola" in page
    assert "3 questions, 2 open." in page


def test_list_without_questions_shows_a_message(admin, db, setup):
    with db:
        db.execute("DELETE FROM question")

    assert "No questions from customers yet." in admin.get("/admin/questions").get_data(as_text=True)


def test_open_question_shows_the_answer_form(admin, db, setup):
    question = find_question(db, "Can the cake be made without milk?")

    page = admin.get(f"/admin/questions/{question.id}").get_data(as_text=True)

    assert "Can the cake be made without milk?" in page
    assert "kari@example.test" in page
    assert f"/admin/questions/{question.id}/answer" in page


def test_answered_question_shows_the_answer_and_no_form(admin, db, setup):
    question = find_question(db, "Can you deliver at 17:00?")

    page = admin.get(f"/admin/questions/{question.id}").get_data(as_text=True)

    assert "Yes, 17:00 is fine." in page
    assert f"/admin/questions/{question.id}/answer" not in page


def test_answering_saves_the_answer_and_goes_to_the_list(admin, db, setup):
    question = find_question(db, "Can the cake be made without milk?")

    response = admin.post(f"/admin/questions/{question.id}/answer", data={"text": "  Yes, we can.  "})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/questions")
    saved = QuestionRepository(db).get_by_id(question.id)
    assert saved.status == QuestionStatus.ANSWERED
    assert saved.given_answer.text == "Yes, we can."
    assert saved.given_answer.answered_by == UserRepository(db).get_by_email("admin@example.test").id


def test_answering_twice_gives_400_and_keeps_the_first_answer(admin, db, setup):
    question = find_question(db, "Can you deliver at 17:00?")

    response = admin.post(f"/admin/questions/{question.id}/answer", data={"text": "No, sorry."})

    assert response.status_code == 400
    assert "This question is already answered." in response.get_data(as_text=True)
    assert QuestionRepository(db).get_by_id(question.id).given_answer.text == "Yes, 17:00 is fine."


@pytest.mark.parametrize("text", ["", "   ", "x" * (MAX_TEXT_LENGTH + 1)])
def test_empty_or_too_long_answer_gives_400_and_saves_nothing(admin, db, setup, text):
    question = find_question(db, "Can the cake be made without milk?")

    response = admin.post(f"/admin/questions/{question.id}/answer", data={"text": text})

    assert response.status_code == 400
    assert not QuestionRepository(db).get_by_id(question.id).is_answered()


def test_unknown_question_gives_404(admin, setup):
    assert admin.get("/admin/questions/no-such-id").status_code == 404
    assert admin.post("/admin/questions/no-such-id/answer", data={"text": "Yes."}).status_code == 404


def test_customer_sees_the_answer_on_the_order_page(client, db, setup):
    karis_order, _ = setup
    question = find_question(db, "Can the cake be made without milk?")
    log_in(client, "admin@example.test")
    client.post(f"/admin/questions/{question.id}/answer", data={"text": "Yes, we can make it without milk."})
    client.post("/account/logout")

    log_in(client, "kari@example.test")
    page = client.get(f"/account/orders/{karis_order.id}").get_data(as_text=True)

    assert "Yes, we can make it without milk." in page


def test_nav_has_questions_link_only_for_admins(client, setup):
    log_in(client, "kari@example.test")
    assert "/admin/questions" not in client.get("/").get_data(as_text=True)
    client.post("/account/logout")

    log_in(client, "admin@example.test")
    assert "/admin/questions" in client.get("/").get_data(as_text=True)
