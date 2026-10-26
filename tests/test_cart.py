from decimal import Decimal

import pytest

from app.models.cart import Cart
from app.models.food import Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.order import OrderLine

WEDDING = Event("Wedding")
SOUP = FoodItem(name="Fiskesuppe", desc="", price=Decimal("129.00"), min_order=10, id="soup")
CAKE = FoodItem(name="Bløtkake", desc="", price=Decimal("590.00"), min_order=2, id="cake")


# The Cart domain class (C2). See docs/plans/c2-cart-activity.md.


def test_new_cart_is_empty():
    assert Cart().is_empty()


def test_set_quantity_adds_and_changes_an_item():
    cart = Cart()
    cart.set_quantity(SOUP, 10)
    cart.set_quantity(SOUP, 25)

    assert cart.to_dict() == {"soup": 25}


@pytest.mark.parametrize("qty", [9, 10_001, -1])
def test_quantity_outside_minimum_and_10000_is_refused(qty):
    cart = Cart()

    with pytest.raises(ValueError, match="between 10 and 10,000"):
        cart.set_quantity(SOUP, qty)
    assert cart.is_empty()


def test_quantity_0_removes_the_item():
    cart = Cart({"soup": 10, "cake": 2})
    cart.set_quantity(SOUP, 0)

    assert cart.to_dict() == {"cake": 2}


def test_cart_survives_a_round_trip_through_a_dict():
    cart = Cart.from_dict({"soup": 10})

    assert cart.to_dict() == {"soup": 10}
    assert cart.count() == 1


def test_to_order_lines_copies_name_and_price():
    cart = Cart({"soup": 40, "cake": 4})

    assert cart.to_order_lines([SOUP, CAKE]) == [
        OrderLine("soup", "Fiskesuppe", 40, Decimal("129.00")),
        OrderLine("cake", "Bløtkake", 4, Decimal("590.00")),
    ]


# The cart pages (C2).


@pytest.fixture
def food(db):
    repo = FoodItemRepository(db)
    repo.add_event(WEDDING)
    soup = FoodItem(name="Fiskesuppe", desc="", price=Decimal("129.00"), min_order=10, events=[WEDDING], published=True)
    hidden = FoodItem(name="Hjortegryte", desc="", price=Decimal("289.00"), min_order=10, events=[WEDDING])
    repo.add(soup)
    repo.add(hidden)
    return repo, soup, hidden


def cart_in_session(client):
    with client.session_transaction() as session:
        return session.get("cart", {})


def test_menu_has_add_to_cart_button(client, food):
    page = client.get("/").get_data(as_text=True)

    assert "Add to cart" in page


def test_add_to_cart_and_show_the_total(client, food):
    _, soup, _ = food

    response = client.post("/cart/add", data={"item_id": soup.id, "quantity": "20"})

    assert response.headers["Location"] == "/cart"
    assert cart_in_session(client) == {soup.id: 20}
    page = client.get("/cart").get_data(as_text=True)
    assert "Fiskesuppe" in page and "2580.00 kr" in page  # 20 * 129
    assert "Cart (1)" in page


def test_quantity_below_minimum_is_refused(client, food):
    _, soup, _ = food

    client.post("/cart/add", data={"item_id": soup.id, "quantity": "9"})

    assert cart_in_session(client) == {}
    page = client.get("/").get_data(as_text=True)
    assert "choose between 10 and 10,000" in page


def test_quantity_that_is_not_a_number_is_refused(client, food):
    _, soup, _ = food

    response = client.post("/cart/add", data={"item_id": soup.id, "quantity": "ten"})

    assert response.status_code == 302
    assert cart_in_session(client) == {}


def test_change_and_remove_an_item(client, food):
    _, soup, _ = food
    client.post("/cart/add", data={"item_id": soup.id, "quantity": "10"})

    client.post("/cart/update", data={"item_id": soup.id, "quantity": "30"})
    assert cart_in_session(client) == {soup.id: 30}

    client.post("/cart/update", data={"item_id": soup.id, "quantity": "0"})
    assert cart_in_session(client) == {}


def test_unpublished_item_cannot_be_added(client, food):
    _, _, hidden = food

    client.post("/cart/add", data={"item_id": hidden.id, "quantity": "10"})

    assert cart_in_session(client) == {}


def test_item_unpublished_after_adding_is_removed_from_cart(client, food):
    repo, soup, _ = food
    client.post("/cart/add", data={"item_id": soup.id, "quantity": "10"})
    soup.unpublish()
    repo.update(soup)

    page = client.get("/cart").get_data(as_text=True)

    assert "no longer on the menu" in page
    assert cart_in_session(client) == {}
