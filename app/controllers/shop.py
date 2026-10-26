from flask import Blueprint, render_template

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
