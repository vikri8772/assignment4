from decimal import Decimal

import pytest

from app.models.food import Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.user import Role, User
from app.models.user_repository import UserRepository

WEDDING = Event("Wedding")


@pytest.fixture
def food(db):
    repo = FoodItemRepository(db)
    repo.add_event(WEDDING)
    return repo


@pytest.fixture
def soup(food):
    item = FoodItem(
        name="Fiskesuppe",
        desc="Fish soup.",
        price=Decimal("129.00"),
        min_order=10,
        events=[WEDDING],
        published=True,
    )
    food.add(item)
    return item


@pytest.fixture
def stew(food):
    item = FoodItem(
        name="Hjortegryte",
        desc="Venison stew.",
        price=Decimal("289.00"),
        min_order=10,
        events=[WEDDING],
    )
    food.add(item)
    return item


def log_in_as(client, db, role):
    # Puts the user straight into the session, so the tests don't need passwords.
    user = User(name=role.name.title(), email=f"{role.name.lower()}@example.test", password_hash="x", role=role)
    UserRepository(db).add(user)
    with client.session_transaction() as session:
        session["user_id"] = user.id


def test_customer_gets_403(client, db):
    log_in_as(client, db, Role.CUSTOMER)

    assert client.get("/admin/").status_code == 403


def test_visitor_is_sent_to_login(client, db):
    response = client.get("/admin/")

    assert response.status_code == 302
    assert "/account/login" in response.headers["Location"]


def test_list_shows_all_items_with_status(client, db, soup, stew):
    log_in_as(client, db, Role.ADMIN)

    page = client.get("/admin/").get_data(as_text=True)

    assert "Fiskesuppe" in page and "Hjortegryte" in page
    assert "Published" in page and "Not published" in page


def test_publish_shows_item_on_menu(client, db, food, stew):
    log_in_as(client, db, Role.ADMIN)

    response = client.post(f"/admin/items/{stew.id}/publish")

    assert response.status_code == 302
    assert food.get_by_id(stew.id).published
    assert "Hjortegryte" in client.get("/").get_data(as_text=True)


def test_unpublish_hides_item_from_menu(client, db, food, soup):
    log_in_as(client, db, Role.ADMIN)

    # Follow the redirect like a browser does, so the flash message is shown on the admin list.
    page = client.post(f"/admin/items/{soup.id}/unpublish", follow_redirects=True).get_data(as_text=True)

    assert "Fiskesuppe is unpublished" in page
    assert not food.get_by_id(soup.id).published
    assert "Fiskesuppe" not in client.get("/").get_data(as_text=True)


def test_publish_unknown_item_gives_404(client, db, food):
    log_in_as(client, db, Role.ADMIN)

    assert client.post("/admin/items/does-not-exist/publish").status_code == 404
    assert client.post("/admin/items/does-not-exist/unpublish").status_code == 404


def test_customer_cannot_publish(client, db, food, stew):
    log_in_as(client, db, Role.CUSTOMER)

    assert client.post(f"/admin/items/{stew.id}/publish").status_code == 403
    assert not food.get_by_id(stew.id).published
