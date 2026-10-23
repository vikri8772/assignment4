from flask import Blueprint, render_template

from app.controllers.auth import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def items_overview():
    # Placeholder until A1 (food items) is built.
    return render_template("admin/items_overview.html")
