from datetime import date, datetime
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.models.food import Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.order import GuestGroup, Order, OrderLine, OrderStatus, PaymentStatus
from app.models.order_repository import OrderRepository
from app.models.user import User
from app.models.user_repository import UserRepository

PASSWORD = "testpassord"
WEDDING = Event("Wedding")
JULEBORD = Event("Julebord")


@pytest.fixture
def setup(db):
    users = UserRepository(db)
    kari = User(name="Kari", email="kari@example.test", password_hash=generate_password_hash(PASSWORD))
    ola = User(name="Ola", email="ola@example.test", password_hash=generate_password_hash(PASSWORD))
    users.add(kari)
    users.add(ola)

    food = FoodItemRepository(db)
    food.add_event(WEDDING)
    food.add_event(JULEBORD)
    soup = FoodItem(name="Fiskesuppe", desc="", price=Decimal("129.00"), min_order=10, events=[WEDDING])
    food.add(soup)

    orders = OrderRepository(db)

    def add_order(user, event, event_date, created_at, **changes):
        order = Order(
            user_id=user.id,
            event=event,
            event_date=event_date,
            number_of_guests=40,
            delivery_address=f"{user.name}s gate 1, Bergen",
            lines=[OrderLine(soup.id, soup.name, 40, soup.price)],
            guest_groups=[GuestGroup("Adults", 40, allergy_notes="2 nut allergies")],
            created_at=created_at,
            **changes,
        )
        orders.add(order)
        return order

    karis_old = add_order(kari, JULEBORD, date(2026, 12, 11), datetime(2026, 9, 1, 10, 0))
    karis_new = add_order(
        kari,
        WEDDING,
        date(2027, 5, 15),
        datetime(2026, 10, 1, 10, 0),
        order_status=OrderStatus.APPROVED,
        payment_status=PaymentStatus.DEPOSIT_PAID,
    )
    olas = add_order(ola, WEDDING, date(2027, 6, 1), datetime(2026, 10, 5, 10, 0))
    return karis_old, karis_new, olas


def log_in(client, email):
    client.post("/account/login", data={"email": email, "password": PASSWORD})


@pytest.fixture
def kari(client, setup):
    log_in(client, "kari@example.test")
    return client


def test_login_is_required(client, setup):
    _, karis_new, _ = setup

    for url in ("/account/orders", f"/account/orders/{karis_new.id}"):
        response = client.get(url)
        assert response.status_code == 302
        assert "/account/login" in response.headers["Location"]


def test_customer_sees_only_own_orders_newest_first(kari, setup):
    karis_old, karis_new, olas = setup

    page = kari.get("/account/orders").get_data(as_text=True)

    assert karis_new.id in page and karis_old.id in page
    assert olas.id not in page
    assert page.index(karis_new.id) < page.index(karis_old.id)  # newest first


def test_list_shows_status_payment_and_total(kari, setup):
    page = kari.get("/account/orders").get_data(as_text=True)

    assert "Approved" in page
    assert "Deposit paid" in page
    assert "Submitted" in page
    assert "5160.00 kr" in page  # 40 * 129


def test_customer_without_orders_sees_a_message(client, db, setup):
    UserRepository(db).add(User(name="Ny", email="ny@example.test", password_hash=generate_password_hash(PASSWORD)))
    log_in(client, "ny@example.test")

    assert "You have no orders yet" in client.get("/account/orders").get_data(as_text=True)


def test_order_page_shows_lines_groups_and_statuses(kari, setup):
    _, karis_new, _ = setup

    page = kari.get(f"/account/orders/{karis_new.id}").get_data(as_text=True)

    assert "Karis gate 1, Bergen" in page
    assert "Fiskesuppe" in page
    assert "2 nut allergies" in page
    assert "Approved" in page
    assert "Deposit paid" in page


def test_order_page_has_no_admin_buttons(kari, setup):
    _, karis_new, _ = setup

    page = kari.get(f"/account/orders/{karis_new.id}").get_data(as_text=True)

    assert "<button" not in page.split("</nav>")[1]  # only the log out button in the nav


def test_someone_elses_order_gives_404(kari, setup):
    _, _, olas = setup

    response = kari.get(f"/account/orders/{olas.id}")

    assert response.status_code == 404
    assert "Olas gate" not in response.get_data(as_text=True)


def test_unknown_order_gives_404(kari, setup):
    assert kari.get("/account/orders/no-such-id").status_code == 404


def test_nav_has_my_orders_link_when_logged_in(client, setup):
    assert "My orders" not in client.get("/").get_data(as_text=True)

    log_in(client, "kari@example.test")

    assert "My orders" in client.get("/").get_data(as_text=True)
