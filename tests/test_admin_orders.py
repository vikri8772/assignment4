from datetime import date
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.models.food import Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.order import GuestGroup, Order, OrderLine, OrderStatus, PaymentStatus
from app.models.order_repository import OrderRepository
from app.models.user import Role, User
from app.models.user_repository import UserRepository

PASSWORD = "testpassord"
WEDDING = Event("Wedding")


@pytest.fixture
def setup(db):
    users = UserRepository(db)
    admin = User(name="Admin", email="admin@example.test", password_hash=generate_password_hash(PASSWORD), role=Role.ADMIN)
    kari = User(name="Kari", email="kari@example.test", password_hash=generate_password_hash(PASSWORD))
    users.add(admin)
    users.add(kari)

    food = FoodItemRepository(db)
    food.add_event(WEDDING)
    soup = FoodItem(name="Fiskesuppe", desc="", price=Decimal("129.00"), min_order=10, events=[WEDDING])
    food.add(soup)

    orders = OrderRepository(db)

    def add_order(event_date, status=OrderStatus.SUBMITTED):
        order = Order(
            user_id=kari.id,
            event=WEDDING,
            event_date=event_date,
            number_of_guests=40,
            delivery_address="Bryggen 1, Bergen",
            lines=[OrderLine(soup.id, soup.name, 40, soup.price)],
            guest_groups=[GuestGroup("Adults", 40, allergy_notes="2 nut allergies")],
            order_status=status,
        )
        orders.add(order)
        return order

    may = add_order(date(2027, 5, 15))
    december = add_order(date(2026, 12, 11), OrderStatus.APPROVED)
    return orders, may, december


def log_in(client, email):
    client.post("/account/login", data={"email": email, "password": PASSWORD})


@pytest.fixture
def admin(client, setup):
    log_in(client, "admin@example.test")
    return client


def test_logged_out_visitor_is_sent_to_login(client, setup):
    response = client.get("/admin/orders")

    assert response.status_code == 302
    assert "/account/login" in response.headers["Location"]


def test_customer_is_not_allowed(client, setup):
    log_in(client, "kari@example.test")

    assert client.get("/admin/orders").status_code == 403
    _, may, _ = setup
    assert client.post(f"/admin/orders/{may.id}/status", data={"status": "APPROVED"}).status_code == 403


def test_list_shows_all_orders_sorted_by_event_date(admin, setup):
    page = admin.get("/admin/orders").get_data(as_text=True)

    assert "2 orders." in page
    assert page.index("2026-12-11") < page.index("2027-05-15")
    assert "Kari" in page


def test_list_filters_by_status(admin, setup):
    page = admin.get("/admin/orders?status=APPROVED").get_data(as_text=True)

    assert "2026-12-11" in page
    assert "2027-05-15" not in page


def test_list_filters_by_event_date(admin, setup):
    page = admin.get("/admin/orders?from=2027-01-01&to=2027-12-31").get_data(as_text=True)

    assert "2027-05-15" in page
    assert "2026-12-11" not in page


def test_bad_filter_values_are_ignored_with_a_message(admin, setup):
    response = admin.get("/admin/orders?status=NONSENSE&from=not-a-date")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "2 orders." in page
    assert "Unknown status in the filter" in page
    assert "From date is not a valid date" in page


def test_order_page_shows_details_and_only_allowed_buttons(admin, setup):
    _, may, _ = setup
    page = admin.get(f"/admin/orders/{may.id}").get_data(as_text=True)

    assert "Bryggen 1, Bergen" in page
    assert "Fiskesuppe" in page
    assert "5160.00 kr" in page  # 40 * 129
    assert "2 nut allergies" in page
    # Submitted: only approve or reject.
    assert "Approve order" in page
    assert "Reject order" in page
    assert "Mark as delivered" not in page
    # Not paid: deposit or invoice, not "paid".
    assert "Deposit paid</button>" in page
    assert "Invoice sent</button>" in page
    assert "Invoice paid</button>" not in page


def test_unknown_order_gives_404(admin, setup):
    assert admin.get("/admin/orders/no-such-id").status_code == 404
    assert admin.post("/admin/orders/no-such-id/status", data={"status": "APPROVED"}).status_code == 404


def test_allowed_status_change_is_saved(admin, setup):
    orders, may, _ = setup

    response = admin.post(f"/admin/orders/{may.id}/status", data={"status": "APPROVED"}, follow_redirects=True)

    assert response.status_code == 200
    assert "Order status changed to Approved." in response.get_data(as_text=True)
    assert orders.get_by_id(may.id).order_status == OrderStatus.APPROVED


def test_status_change_that_is_not_allowed_is_refused(admin, setup):
    orders, may, _ = setup

    response = admin.post(f"/admin/orders/{may.id}/status", data={"status": "DELIVERED"})

    assert response.status_code == 400
    assert "can&#39;t go from Submitted to Delivered" in response.get_data(as_text=True)
    assert orders.get_by_id(may.id).order_status == OrderStatus.SUBMITTED


def test_unknown_status_value_is_refused(admin, setup):
    orders, may, _ = setup

    response = admin.post(f"/admin/orders/{may.id}/status", data={"status": "HACKED"})

    assert response.status_code == 400
    assert orders.get_by_id(may.id).order_status == OrderStatus.SUBMITTED


def test_payment_status_change_is_saved(admin, setup):
    orders, may, _ = setup

    admin.post(f"/admin/orders/{may.id}/payment", data={"status": "INVOICED"})
    admin.post(f"/admin/orders/{may.id}/payment", data={"status": "PAID"})

    saved = orders.get_by_id(may.id)
    assert saved.payment_status == PaymentStatus.PAID
    assert saved.order_status == OrderStatus.SUBMITTED  # payment doesn't change the order status


def test_payment_change_that_is_not_allowed_is_refused(admin, setup):
    orders, may, _ = setup

    response = admin.post(f"/admin/orders/{may.id}/payment", data={"status": "PAID"})

    assert response.status_code == 400
    assert orders.get_by_id(may.id).payment_status == PaymentStatus.NOT_PAID
