from decimal import Decimal

import pytest

from app.models.food import Diet, Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.user import Role, User
from app.models.user_repository import UserRepository

WEDDING = Event("Wedding")
JULEBORD = Event("Julebord")
VEGAN = Diet("Vegan")


@pytest.fixture
def food(db):
    repo = FoodItemRepository(db)
    repo.add_event(WEDDING)
    repo.add_event(JULEBORD)
    repo.add_diet(VEGAN)
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


# Create and edit (step 3)

VALID_FORM = {
    "name": "Rakfisk",
    "desc": "Seasonal, November only.",
    "price": "210,50",  # Norwegian decimal comma
    "min_order": "8",
    "events": ["Julebord"],
    "diets": ["Vegan"],
    "allergens": ["fish", "mustard"],
}


def test_new_item_form_shows_checklists(client, db, food):
    log_in_as(client, db, Role.ADMIN)

    page = client.get("/admin/items/new").get_data(as_text=True)

    assert 'value="Julebord"' in page
    assert 'value="Vegan"' in page
    assert 'value="crustaceans"' in page


def test_create_item_saves_it_unpublished(client, db, food):
    log_in_as(client, db, Role.ADMIN)

    response = client.post("/admin/items/new", data=VALID_FORM)

    assert response.status_code == 302
    [item] = food.get_all()
    assert item.name == "Rakfisk"
    assert item.price == Decimal("210.50")
    assert item.min_order == 8
    assert item.events == [JULEBORD]
    assert item.diets == [VEGAN]
    assert item.allergens == ["fish", "mustard"]
    assert not item.published


def test_unknown_event_and_allergen_are_ignored(client, db, food):
    log_in_as(client, db, Role.ADMIN)

    form = VALID_FORM | {"events": ["Julebord", "Moon party"], "allergens": ["fish", "kryptonite"]}
    client.post("/admin/items/new", data=form)

    [item] = food.get_all()
    assert item.events == [JULEBORD]
    assert item.allergens == ["fish"]


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"name": "  "}, "Name is required"),
        ({"price": "0"}, "Price must be"),
        ({"price": "-5"}, "Price must be"),
        ({"price": "abc"}, "Price must be"),
        ({"price": "12.345"}, "Price must be"),
        ({"price": "NaN"}, "Price must be"),
        ({"price": "1e30"}, "Price must be"),
        ({"min_order": "0"}, "Minimum order must be"),
        ({"min_order": "2.5"}, "Minimum order must be"),
        ({"min_order": "100000"}, "Minimum order must be"),
        ({"events": []}, "Choose at least one event"),
    ],
)
def test_invalid_item_is_not_saved(client, db, food, changes, message):
    log_in_as(client, db, Role.ADMIN)

    response = client.post("/admin/items/new", data=VALID_FORM | changes)

    assert response.status_code == 400
    assert message in response.get_data(as_text=True)
    assert food.get_all() == []


def test_form_keeps_what_admin_typed_after_error(client, db, food):
    log_in_as(client, db, Role.ADMIN)

    page = client.post("/admin/items/new", data=VALID_FORM | {"price": "0"}).get_data(as_text=True)

    assert 'value="Rakfisk"' in page
    assert 'value="mustard" checked' in page


def test_edit_form_shows_current_values(client, db, soup):
    log_in_as(client, db, Role.ADMIN)

    page = client.get(f"/admin/items/{soup.id}/edit").get_data(as_text=True)

    assert "Edit Fiskesuppe" in page
    assert 'value="129.00"' in page
    assert 'value="Wedding" checked' in page


def test_edit_saves_changes(client, db, food, soup):
    log_in_as(client, db, Role.ADMIN)

    response = client.post(f"/admin/items/{soup.id}/edit", data=VALID_FORM | {"name": "Fiskesuppe", "price": "149"})

    assert response.status_code == 302
    item = food.get_by_id(soup.id)
    assert item.price == Decimal("149.00")
    assert item.events == [JULEBORD]
    assert item.published  # editing doesn't change whether the item is published


def test_invalid_edit_changes_nothing(client, db, food, soup):
    log_in_as(client, db, Role.ADMIN)

    response = client.post(f"/admin/items/{soup.id}/edit", data=VALID_FORM | {"name": ""})

    assert response.status_code == 400
    assert food.get_by_id(soup.id).name == "Fiskesuppe"


def test_edit_unknown_item_gives_404(client, db, food):
    log_in_as(client, db, Role.ADMIN)

    assert client.get("/admin/items/does-not-exist/edit").status_code == 404
    assert client.post("/admin/items/does-not-exist/edit", data=VALID_FORM).status_code == 404


def test_customer_cannot_create_items(client, db, food):
    log_in_as(client, db, Role.CUSTOMER)

    assert client.post("/admin/items/new", data=VALID_FORM).status_code == 403
    assert food.get_all() == []
