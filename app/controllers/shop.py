from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.models.cart import Cart
from app.models.db import get_db
from app.models.food_item_repository import FoodItemRepository

bp = Blueprint("shop", __name__)


@bp.route("/")
def menu():
    # C1 Menu by event. See docs/plans/c1-menu-sequence.md.
    repo = FoodItemRepository(get_db())
    menu = []
    for event in repo.get_events():
        items = repo.get_published_items(event)
        if items:  # events without published items are not shown
            menu.append((event, items))
    return render_template("shop/menu.html", menu=menu)


# C2 Cart. See docs/plans/c2-cart-activity.md.


@bp.route("/cart")
def cart():
    cart, items = _load_cart()
    lines = cart.to_order_lines(items)
    # Each row is (order line, food item); the item gives the minimum quantity.
    return render_template("shop/cart.html", rows=list(zip(lines, items)), total=_total(lines))


@bp.route("/cart/add", methods=["POST"])
def add_to_cart():
    return _set_quantity_from_form(adding=True)


@bp.route("/cart/update", methods=["POST"])
def update_cart():
    return _set_quantity_from_form(adding=False)


def _load_cart():
    # The cart from the session, and its food items. Items that were unpublished or
    # deleted since they were added are removed, with a message to the customer.
    cart = Cart.from_dict(session.get("cart", {}))
    repo = FoodItemRepository(get_db())
    items = []
    for item_id in cart.item_ids():
        item = repo.get_by_id(item_id)
        if item is None or not item.published:
            cart.remove(item_id)
            flash("An item in your cart is no longer on the menu, so it was removed.")
        else:
            items.append(item)
    session["cart"] = cart.to_dict()
    return cart, items


def _set_quantity_from_form(adding):
    item = FoodItemRepository(get_db()).get_by_id(request.form.get("item_id", ""))
    if item is None or not item.published:
        flash("That item is not on the menu.")
        return redirect(url_for("shop.cart"))

    try:
        qty = int(request.form.get("quantity", ""))
    except ValueError:
        flash(f"{item.name}: enter a whole number.")
        return redirect(url_for("shop.cart"))

    cart = Cart.from_dict(session.get("cart", {}))
    try:
        cart.set_quantity(item, qty)
    except ValueError as error:
        flash(str(error))
        return redirect(url_for("shop.menu") if adding else url_for("shop.cart"))

    session["cart"] = cart.to_dict()
    if adding:
        flash(f"{item.name} ({qty}) is in your cart.")
    return redirect(url_for("shop.cart"))


def _total(lines):
    return sum((line.subtotal() for line in lines), Decimal("0"))
