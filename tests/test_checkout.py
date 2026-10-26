from datetime import date, timedelta
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.models.food import Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.order_repository import OrderRepository
from app.models.user import Role, User
from app.models.user_repository import UserRepository

# C3 Order form. See docs/plans/c3-order-form-activity.md and c3-checkout-sequence.md.

PASSWORD = "testpassord"
WEDDING = Event("Wedding")
NEXT_MONTH = (date.today() + timedelta(days=30)).isoformat()


@pytest.fixture
def setup(db):
    users = UserRepository(db)
    kari = User(name="Kari", email="kari@example.test", password_hash=generate_password_hash(PASSWORD))
    admin = User(
        name="Admin", email="admin@example.test", password_hash=generate_password_hash(PASSWORD), role=Role.ADMIN
    )
    users.add(kari)
    users.add(admin)

    food = FoodItemRepository(db)
    food.add_event(WEDDING)
    soup = FoodItem(name="Fiskesuppe", desc="", price=Decimal("129.00"), min_order=10, events=[WEDDING], published=True)
    food.add(soup)
    return kari, soup


def log_in(client, email):
    return client.post("/account/login?next=/checkout", data={"email": email, "password": PASSWORD})


def add_soup(client, soup, quantity=40):
    client.post("/cart/add", data={"item_id": soup.id, "quantity": str(quantity)})


def order_form(**changes):
    form = {
        "event": "Wedding",
        "event_date": NEXT_MONTH,
        "number_of_guests": "40",
        "delivery_address": "Bryggen 1, Bergen",
        "group_name_0": "Adults",
        "group_guests_0": "30",
        "group_allergies_0": "2 nut allergies",
        "group_name_1": "Children",
        "group_guests_1": "10",
        "group_diets_1": "3 vegetarians",
    }
    form.update(changes)
    return form


def test_logged_out_customer_logs_in_and_keeps_the_cart(client, setup):
    _, soup = setup
    add_soup(client, soup)

    response = client.get("/checkout")
    assert "/account/login" in response.headers["Location"]

    response = log_in(client, "kari@example.test")
    assert response.headers["Location"] == "/checkout"
    page = client.get("/checkout").get_data(as_text=True)
    assert "Fiskesuppe" in page and "5160.00 kr" in page  # 40 * 129, the cart is kept


def test_empty_cart_goes_back_to_the_cart(client, setup):
    log_in(client, "kari@example.test")

    response = client.get("/checkout")

    assert response.headers["Location"] == "/cart"


def test_admin_is_sent_to_the_admin_orders(client, setup):
    log_in(client, "admin@example.test")

    response = client.get("/checkout")

    assert response.headers["Location"] == "/admin/orders"


def test_valid_order_is_saved_and_shown_as_confirmation(client, db, setup):
    kari, soup = setup
    add_soup(client, soup)
    log_in(client, "kari@example.test")

    response = client.post("/checkout", data=order_form())

    [order] = OrderRepository(db).get_by_user(kari.id)
    assert response.headers["Location"] == f"/account/orders/{order.id}"
    assert order.event == WEDDING
    assert order.event_date.isoformat() == NEXT_MONTH
    assert order.number_of_guests == 40
    assert [(line.item_name, line.quantity, line.unit_price) for line in order.lines] == [
        ("Fiskesuppe", 40, Decimal("129.00"))
    ]
    assert [(g.group_name, g.number_of_guests, g.allergy_notes, g.dietary_notes) for g in order.guest_groups] == [
        ("Adults", 30, "2 nut allergies", ""),
        ("Children", 10, "", "3 vegetarians"),
    ]

    # The cart is empty, and the order page (C4) confirms the order.
    with client.session_transaction() as session:
        assert session.get("cart") is None
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Your order is submitted" in page
    assert "2 nut allergies" in page
    assert order.id in client.get("/account/orders").get_data(as_text=True)


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"event_date": "2020-01-01"}, "can&#39;t be in the past"),
        ({"group_guests_1": "5"}, "The guest groups have 35 guests in total, but the order is for 40."),
        ({"number_of_guests": "many"}, "Enter the number of guests as a whole number."),
        ({"event": "Funeral"}, "Choose an event type."),
        ({"delivery_address": "Bgn"}, "delivery address must be 5 to 200 characters"),
        ({"group_name_0": "", "group_guests_0": "", "group_allergies_0": "", "group_name_1": "", "group_guests_1": "", "group_diets_1": ""},
         "Add at least one guest group."),
    ],
)
def test_invalid_order_shows_errors_and_saves_nothing(client, db, setup, changes, message):
    kari, soup = setup
    add_soup(client, soup)
    log_in(client, "kari@example.test")

    response = client.post("/checkout", data=order_form(**changes))

    assert response.status_code == 400
    page = response.get_data(as_text=True)
    assert message in page
    assert 'value="Bryggen 1, Bergen"' in page or "delivery_address" in changes  # the form keeps what was typed
    assert OrderRepository(db).get_by_user(kari.id) == []
    with client.session_transaction() as session:
        assert session["cart"] == {soup.id: 40}  # the cart is kept
