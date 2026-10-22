from flask import Blueprint, render_template

bp = Blueprint("shop", __name__)


@bp.route("/")
def menu():
    # Placeholder until C1 (menu by event type) is built.
    return render_template("shop/menu.html")
