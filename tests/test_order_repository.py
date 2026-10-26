import sqlite3
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.models.food import Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.order import GuestGroup, Order, OrderLine, OrderStatus, PaymentStatus
from app.models.order_repository import OrderRepository
from app.models.user import User
from app.models.user_repository import UserRepository

WEDDING = Event("Wedding")
CONFERENCE = Event("Conference")


@pytest.fixture
def soup(db):
    food = FoodItemRepository(db)
    food.add_event(WEDDING)
    food.add_event(CONFERENCE)
    item = FoodItem(name="Fiskesuppe", desc="", price=Decimal("129.00"), min_order=10, events=[WEDDING])
    food.add(item)
    return item


@pytest.fixture
def kari(db):
    user = User(name="Kari", email="kari@example.test", password_hash="x")
    UserRepository(db).add(user)
    return user


@pytest.fixture
def ola(db):
    user = User(name="Ola", email="ola@example.test", password_hash="x")
    UserRepository(db).add(user)
    return user


@pytest.fixture
def repo(db):
    return OrderRepository(db)


def make_order(user, soup, **changes):
    values = dict(
        user_id=user.id,
        event=WEDDING,
        event_date=date(2027, 5, 15),
        number_of_guests=40,
        delivery_address="Bryggen 1, Bergen",
        lines=[OrderLine(soup.id, soup.name, 40, soup.price)],
        guest_groups=[
            GuestGroup("Adults", 30, allergy_notes="2 nut allergies"),
            GuestGroup("Children", 10, dietary_notes="3 vegetarian"),
        ],
        created_at=datetime(2026, 10, 1, 12, 0),
    )
    values.update(changes)
    return Order(**values)


def test_added_order_comes_back_the_same(repo, kari, soup):
    order = make_order(kari, soup, payment_status=PaymentStatus.DEPOSIT_PAID)
    repo.add(order)

    assert repo.get_by_id(order.id) == order


def test_get_by_id_returns_none_for_unknown_id(repo):
    assert repo.get_by_id("no-such-id") is None


def test_get_by_user_returns_only_that_users_orders_newest_first(repo, kari, ola, soup):
    old = make_order(kari, soup, created_at=datetime(2026, 9, 1, 10, 0))
    new = make_order(kari, soup, created_at=datetime(2026, 10, 1, 10, 0))
    olas = make_order(ola, soup)
    for order in (old, new, olas):
        repo.add(order)

    assert [o.id for o in repo.get_by_user(kari.id)] == [new.id, old.id]
    assert repo.get_by_user("nobody") == []


@pytest.fixture
def three_orders(repo, kari, soup):
    may = make_order(kari, soup, event_date=date(2027, 5, 15))
    march = make_order(kari, soup, event_date=date(2027, 3, 1), order_status=OrderStatus.APPROVED)
    june = make_order(kari, soup, event_date=date(2027, 6, 20), order_status=OrderStatus.APPROVED)
    for order in (may, march, june):
        repo.add(order)
    return march, may, june


def test_find_without_filters_returns_all_sorted_by_event_date(repo, three_orders):
    assert [o.id for o in repo.find()] == [o.id for o in three_orders]


def test_find_by_status(repo, three_orders):
    march, may, june = three_orders

    assert [o.id for o in repo.find(status=OrderStatus.APPROVED)] == [march.id, june.id]
    assert repo.find(status=OrderStatus.DELIVERED) == []


def test_find_by_date_range_includes_both_ends(repo, three_orders):
    march, may, june = three_orders

    assert [o.id for o in repo.find(from_date=date(2027, 5, 15))] == [may.id, june.id]
    assert [o.id for o in repo.find(to_date=date(2027, 5, 15))] == [march.id, may.id]
    assert [o.id for o in repo.find(from_date=date(2027, 4, 1), to_date=date(2027, 5, 31))] == [may.id]


def test_find_with_all_filters(repo, three_orders):
    march, may, june = three_orders

    found = repo.find(status=OrderStatus.APPROVED, from_date=date(2027, 4, 1), to_date=date(2027, 12, 31))

    assert [o.id for o in found] == [june.id]


def test_update_saves_new_statuses(repo, kari, soup):
    order = make_order(kari, soup)
    repo.add(order)

    order.change_status(OrderStatus.APPROVED)
    order.change_payment_status(PaymentStatus.INVOICED)
    repo.update(order)

    saved = repo.get_by_id(order.id)
    assert saved.order_status == OrderStatus.APPROVED
    assert saved.payment_status == PaymentStatus.INVOICED


def test_order_with_unknown_food_item_is_not_saved_at_all(repo, db, kari, soup):
    order = make_order(kari, soup, lines=[OrderLine("no-such-item", "Ghost", 1, Decimal("1"))])

    with pytest.raises(sqlite3.IntegrityError):
        repo.add(order)

    assert repo.find() == []
    assert db.execute("SELECT * FROM guest_group").fetchall() == []


def test_food_item_in_an_order_cannot_be_deleted(repo, db, kari, soup):
    repo.add(make_order(kari, soup))

    with pytest.raises(sqlite3.IntegrityError):
        FoodItemRepository(db).delete(soup.id)
