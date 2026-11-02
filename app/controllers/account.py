from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.controllers.auth import login_required
from app.models.db import get_db
from app.models.order_repository import OrderRepository
from app.models.question import MAX_TEXT_LENGTH, Question
from app.models.question_repository import QuestionRepository
from app.models.user import User
from app.models.user_repository import UserRepository

bp = Blueprint("account", __name__, url_prefix="/account")

MIN_PASSWORD_LENGTH = 8


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = UserRepository(get_db()).get_by_email(email)

        if user is None or not check_password_hash(user.password_hash, password):
            # Same message for both cases, so nobody can test which e-mails exist.
            flash("Wrong e-mail or password.")
            return render_template("account/login.html", email=email), 400

        # Only user_id is set, so the cart in the session survives the login (C3).
        session["user_id"] = user.id
        return redirect(_safe_next_url())

    return render_template("account/login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        users = UserRepository(get_db())

        errors = []
        if not name:
            errors.append("Name is required.")
        if "@" not in email:
            errors.append("Enter a valid e-mail address.")
        elif users.get_by_email(email) is not None:
            errors.append("An account with this e-mail already exists.")
        if len(password) < MIN_PASSWORD_LENGTH:
            errors.append(f"The password must be at least {MIN_PASSWORD_LENGTH} characters.")

        if errors:
            for error in errors:
                flash(error)
            return render_template("account/register.html", name=name, email=email), 400

        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        users.add(user)
        session["user_id"] = user.id
        flash(f"Welcome, {user.name}!")
        return redirect(_safe_next_url())

    return render_template("account/register.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("shop.menu"))


# C4 My orders. See docs/plans/c4-my-orders-sequence.md.


@bp.route("/orders")
@login_required
def my_orders():
    # Admins don't order food themselves, so they are sent to the list of all orders (A3).
    if g.user.is_admin():
        return redirect(url_for("admin.orders"))
    orders = OrderRepository(get_db()).get_by_user(g.user.id)
    return render_template("account/orders.html", orders=orders)


@bp.route("/orders/<order_id>")
@login_required
def my_order_detail(order_id):
    order = _get_own_order_or_404(order_id)
    return _render_my_order(order)


# C5 Questions about an order. See docs/plans/c5-qa-sequence.md.


@bp.route("/orders/<order_id>/questions", methods=["POST"])
@login_required
def ask_question(order_id):
    order = _get_own_order_or_404(order_id)
    text = request.form.get("text", "").strip()

    error = None
    if not text:
        error = "Write your question before you send it."
    elif len(text) > MAX_TEXT_LENGTH:
        error = f"The question can be at most {MAX_TEXT_LENGTH} characters."
    if error:
        flash(error)
        return _render_my_order(order, question_text=text), 400

    QuestionRepository(get_db()).add(Question(order_id=order.id, asked_by=g.user.id, text=text))
    flash("Your question is sent. We will answer it here.")
    return redirect(url_for("account.my_order_detail", order_id=order.id))


def _get_own_order_or_404(order_id):
    order = OrderRepository(get_db()).get_by_id(order_id)
    # Same 404 for a missing order and someone else's order, so nobody can find out which order IDs exist.
    if order is None or not order.belongs_to(g.user.id):
        abort(404)
    return order


def _render_my_order(order, question_text=""):
    questions = QuestionRepository(get_db()).get_by_order(order.id)
    return render_template(
        "account/order_detail.html",
        order=order,
        questions=questions,
        question_text=question_text,
        max_question_length=MAX_TEXT_LENGTH,
    )


def _safe_next_url():
    # Only go back to pages on this site, never to another website.
    next_url = request.args.get("next", "")
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return url_for("shop.menu")
