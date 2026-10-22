from flask import Blueprint, render_template

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.route("/login")
def login():
    # Placeholder until login is built in step 6.
    return render_template("account/login.html")
