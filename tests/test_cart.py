from decimal import Decimal

import pytest

from app.models.cart import Cart
from app.models.food import FoodItem
from app.models.order import OrderLine

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
