from flask import Blueprint, abort, flash, redirect, render_template, url_for

from app.controllers.auth import admin_required
from app.models.db import get_db
from app.models.food_item_repository import FoodItemRepository

bp = Blueprint("admin", __name__, url_prefix="/admin")


# A1 Food items. See docs/plans/a1-manage-items-sequence.md.


@bp.route("/")
@admin_required
def items_overview():
    items = FoodItemRepository(get_db()).get_all()
    return render_template("admin/items_overview.html", items=items)


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
