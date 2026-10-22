from flask import Blueprint, render_template

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
def items_overview():
    # Placeholder until A1 (food items) is built.
    # Step 6 adds the check that only admins can open this page.
    return render_template("admin/items_overview.html")
