from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.controllers.auth import admin_required
from app.models.db import get_db
from app.models.food import ALLERGENS, MAX_QUANTITY, FoodItem
from app.models.food_item_repository import FoodItemRepository

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Highest price an admin can type in, to catch typos like an extra zero.
MAX_PRICE = Decimal("100000")


# A1 Food items. See docs/plans/a1-manage-items-sequence.md and a1-edit-item-sequence.md.


@bp.route("/")
@admin_required
def items_overview():
    items = FoodItemRepository(get_db()).get_all()
    return render_template("admin/items_overview.html", items=items)


@bp.route("/items/new", methods=["GET", "POST"])
@admin_required
def new_item():
    repo = FoodItemRepository(get_db())
    if request.method == "POST":
        fields, errors = _read_item_form(repo)
        if errors:
            for error in errors:
                flash(error)
            return _render_item_form(repo, _values_from_form(), status=400)

        # New items start unpublished, so the admin can check them before customers see them.
        item = FoodItem(**fields)
        repo.add(item)
        flash(f"{item.name} is saved. Publish it to show it on the menu.")
        return redirect(url_for("admin.items_overview"))

    return _render_item_form(repo, _values_from_item(None))


@bp.route("/items/<item_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_item(item_id):
    repo = FoodItemRepository(get_db())
    item = _get_item_or_404(repo, item_id)
    if request.method == "POST":
        fields, errors = _read_item_form(repo)
        if errors:
            for error in errors:
                flash(error)
            return _render_item_form(repo, _values_from_form(), item, status=400)

        item.name = fields["name"]
        item.desc = fields["desc"]
        item.price = fields["price"]
        item.min_order = fields["min_order"]
        item.events = fields["events"]
        item.diets = fields["diets"]
        item.allergens = fields["allergens"]
        repo.update(item)
        flash(f"{item.name} is saved.")
        return redirect(url_for("admin.items_overview"))

    return _render_item_form(repo, _values_from_item(item), item)


@bp.route("/items/<item_id>/publish", methods=["POST"])
@admin_required
def publish_item(item_id):
    repo = FoodItemRepository(get_db())
    item = _get_item_or_404(repo, item_id)
    item.publish()
    repo.update(item)
    flash(f"{item.name} is published and shown on the menu.")
    return redirect(url_for("admin.items_overview"))


@bp.route("/items/<item_id>/unpublish", methods=["POST"])
@admin_required
def unpublish_item(item_id):
    repo = FoodItemRepository(get_db())
    item = _get_item_or_404(repo, item_id)
    item.unpublish()
    repo.update(item)
    flash(f"{item.name} is unpublished and hidden from the menu.")
    return redirect(url_for("admin.items_overview"))


def _get_item_or_404(repo, item_id):
    item = repo.get_by_id(item_id)
    if item is None:
        abort(404)
    return item


def _read_item_form(repo):
    # Checks the item form. Returns the fields for a FoodItem, and a list of error messages.
    form = request.form
    name = form.get("name", "").strip()
    desc = form.get("desc", "").strip()

    errors = []
    if not name:
        errors.append("Name is required.")

    try:
        # Accept both "129.50" and the Norwegian "129,50".
        price = Decimal(form.get("price", "").strip().replace(",", "."))
        price_ok = price.is_finite() and 0 < price <= MAX_PRICE and price.as_tuple().exponent >= -2
    except InvalidOperation:
        price_ok = False
    if price_ok:
        price = price.quantize(Decimal("0.01"))  # always two decimals, e.g. 129.00
    else:
        price = None
        errors.append(f"Price must be a number above 0 and at most {MAX_PRICE} NOK, with at most 2 decimals.")

    try:
        min_order = int(form.get("min_order", ""))
    except ValueError:
        min_order = 0
    if not 1 <= min_order <= MAX_QUANTITY:
        errors.append(f"Minimum order must be a whole number from 1 to {MAX_QUANTITY}.")

    # Only names from the checklists are used, so a changed form can't add unknown events.
    events = [event for event in repo.get_events() if event.name in form.getlist("events")]
    if not events:
        errors.append("Choose at least one event.")
    diets = [diet for diet in repo.get_diets() if diet.name in form.getlist("diets")]
    allergens = [allergen for allergen in ALLERGENS if allergen in form.getlist("allergens")]

    fields = {
        "name": name,
        "desc": desc,
        "price": price,
        "min_order": min_order,
        "events": events,
        "diets": diets,
        "allergens": allergens,
    }
    return fields, errors


# The form shows "values": what is saved (when it opens) or what the admin typed (after an error).


def _values_from_item(item):
    if item is None:
        return {"name": "", "desc": "", "price": "", "min_order": "", "events": [], "diets": [], "allergens": []}
    return {
        "name": item.name,
        "desc": item.desc,
        "price": str(item.price),
        "min_order": str(item.min_order),
        "events": [event.name for event in item.events],
        "diets": [diet.name for diet in item.diets],
        "allergens": item.allergens,
    }


def _values_from_form():
    form = request.form
    return {
        "name": form.get("name", ""),
        "desc": form.get("desc", ""),
        "price": form.get("price", ""),
        "min_order": form.get("min_order", ""),
        "events": form.getlist("events"),
        "diets": form.getlist("diets"),
        "allergens": form.getlist("allergens"),
    }


def _render_item_form(repo, values, item=None, status=200):
    page = render_template(
        "admin/item_form.html",
        item=item,
        values=values,
        events=repo.get_events(),
        diets=repo.get_diets(),
        allergens=ALLERGENS,
    )
    return page, status
