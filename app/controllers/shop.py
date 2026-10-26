from datetime import date
from decimal import Decimal

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from app.controllers.auth import login_required
from app.models.cart import Cart
from app.models.db import get_db
from app.models.food import Event
from app.models.food_item_repository import FoodItemRepository
from app.models.order import GuestGroup, Order
from app.models.order_repository import OrderRepository

bp = Blueprint("shop", __name__)

# How many guest group rows the order form shows. Empty rows are ignored (C3).
GUEST_GROUP_ROWS = 5


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


# C3 Order form. See docs/plans/c3-order-form-activity.md and c3-checkout-sequence.md.


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    # Admins don't order food themselves (same rule as "My orders").
    if g.user.is_admin():
        return redirect(url_for("admin.orders"))

    cart, items = _load_cart()
    if cart.is_empty():
        flash("Your cart is empty. Add food from the menu first.")
        return redirect(url_for("shop.cart"))

    lines = cart.to_order_lines(items)
    events = FoodItemRepository(get_db()).get_events()

    if request.method == "POST":
        order, errors = _order_from_form(lines, events)
        if order is not None:
            errors = order.problems(date.today())
        if errors:
            for error in errors:
                flash(error)
            return _render_checkout(lines, events, request.form), 400

        OrderRepository(get_db()).add(order)
        session.pop("cart", None)
        flash("Thank you! Your order is submitted. We will confirm it soon.")
        # The order page in "My orders" (C4) is the order confirmation.
        return redirect(url_for("account.my_order_detail", order_id=order.id))

    return _render_checkout(lines, events, {})


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


def _order_from_form(lines, events):
    # Turns the order form into an Order. Returns (order, []) or (None, errors)
    # when a field can't even be read, such as a date that isn't a date.
    form = request.form
    errors = []

    event = Event(form.get("event", ""))
    if event not in events:
        errors.append("Choose an event type.")

    try:
        event_date = date.fromisoformat(form.get("event_date", ""))
    except ValueError:
        errors.append("Enter the event date.")

    number_of_guests = _whole_number(form.get("number_of_guests", ""))
    if number_of_guests is None:
        errors.append("Enter the number of guests as a whole number.")

    groups = []
    for i in range(GUEST_GROUP_ROWS):
        name = form.get(f"group_name_{i}", "").strip()
        guests = form.get(f"group_guests_{i}", "").strip()
        allergies = form.get(f"group_allergies_{i}", "").strip()
        diets = form.get(f"group_diets_{i}", "").strip()
        if not (name or guests or allergies or diets):
            continue  # an empty row
        group_guests = _whole_number(guests)
        if group_guests is None:
            errors.append(f"Guest group {i + 1}: enter the number of guests as a whole number.")
            continue
        groups.append(GuestGroup(name, group_guests, allergy_notes=allergies, dietary_notes=diets))

    if errors:
        return None, errors

    order = Order(
        user_id=g.user.id,
        event=event,
        event_date=event_date,
        number_of_guests=number_of_guests,
        delivery_address=form.get("delivery_address", "").strip(),
        lines=lines,
        guest_groups=groups,
    )
    return order, []


def _whole_number(text):
    try:
        return int(text)
    except ValueError:
        return None


def _total(lines):
    return sum((line.subtotal() for line in lines), Decimal("0"))


def _render_checkout(lines, events, form):
    return render_template(
        "shop/checkout.html",
        lines=lines,
        total=_total(lines),
        events=events,
        form=form,
        group_rows=range(GUEST_GROUP_ROWS),
        today=date.today().isoformat(),
    )
