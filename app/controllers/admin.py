import os
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from app.controllers.auth import admin_required
from app.models.db import get_db
from app.models.food import ALLERGENS, MAX_QUANTITY, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.order import InvalidTransition, OrderStatus, PaymentStatus
from app.models.order_repository import OrderRepository
from app.models.question import MAX_TEXT_LENGTH
from app.models.question_repository import QuestionRepository
from app.models.user_repository import UserRepository

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Highest price an admin can type in, to catch typos like an extra zero.
MAX_PRICE = Decimal("100000")

# A2 Pictures: at most 5 MB, JPG or PNG. The type is read from the first bytes
# of the file itself, because a file name like "cake.png" can be wrong.
MAX_PICTURE_SIZE = 5 * 1024 * 1024
PICTURE_TYPES = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png"}


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
        picture, picture_error = _read_picture()
        if picture_error:
            errors.append(picture_error)
        if errors:
            for error in errors:
                flash(error)
            return _render_item_form(repo, _values_from_form(), status=400)

        # New items start unpublished, so the admin can check them before customers see them.
        item = FoodItem(**fields)
        if picture:
            item.picture_path = _save_picture(picture)
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
        picture, picture_error = _read_picture()
        if picture_error:
            errors.append(picture_error)
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
        if picture:
            # No new file chosen means: keep the current picture.
            old_picture = item.picture_path
            item.picture_path = _save_picture(picture)
        repo.update(item)
        if picture:
            _delete_picture(old_picture)
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


@bp.route("/items/<item_id>/delete", methods=["POST"])
@admin_required
def delete_item(item_id):
    repo = FoodItemRepository(get_db())
    item = _get_item_or_404(repo, item_id)
    # Orders keep pointing to their food items, so an ordered item must stay.
    if repo.is_used_in_orders(item.id):
        flash(f"{item.name} is used in orders, so it can't be deleted. Unpublish it instead.")
        return redirect(url_for("admin.items_overview"))

    repo.delete(item.id)
    _delete_picture(item.picture_path)
    flash(f"{item.name} is deleted.")
    return redirect(url_for("admin.items_overview"))


@bp.errorhandler(413)
def request_too_large(error):
    # Flask stops requests above MAX_CONTENT_LENGTH before our checks run.
    flash("The picture is too large. Choose a JPG or PNG of at most 5 MB.")
    return redirect(request.path)


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


# A2 Pictures. See docs/plans/a2-item-image-sequence.md.


def _read_picture():
    # Checks the uploaded picture. Returns (picture, error): picture is (bytes, extension) or None.
    file = request.files.get("picture")
    if file is None or file.filename == "":
        return None, None  # no new picture chosen

    data = file.read(MAX_PICTURE_SIZE + 1)
    if len(data) > MAX_PICTURE_SIZE:
        return None, "The picture is larger than 5 MB. Choose a smaller one."
    for start, extension in PICTURE_TYPES.items():
        if data.startswith(start):
            return (data, extension), None
    return None, "The picture must be a JPG or PNG file. Choose it again."


def _save_picture(picture):
    # Saves the file under a new unique name and returns its path inside static/.
    data, extension = picture
    filename = f"{uuid4().hex}.{extension}"
    with open(os.path.join(current_app.config["UPLOAD_FOLDER"], filename), "wb") as file:
        file.write(data)
    return f"uploads/{filename}"


def _delete_picture(picture_path):
    # Removes a replaced picture, so old files don't pile up.
    if not picture_path or not picture_path.startswith("uploads/"):
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(picture_path))
    if os.path.exists(path):
        os.remove(path)


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


# A3 Orders. See docs/plans/a3-order-management-sequence.md.


@bp.route("/orders")
@admin_required
def orders():
    # Filters come from the URL, e.g. /admin/orders?status=APPROVED&from=2026-12-01
    status = _parse_status(request.args.get("status", ""))
    from_date = _parse_date(request.args.get("from", ""), "From date")
    to_date = _parse_date(request.args.get("to", ""), "To date")

    orders = OrderRepository(get_db()).find(status, from_date, to_date)
    return render_template(
        "admin/orders.html",
        orders=orders,
        customers=_customers_for(orders),
        statuses=list(OrderStatus),
        status=status,
        from_date=from_date,
        to_date=to_date,
    )


@bp.route("/orders/<order_id>")
@admin_required
def order_detail(order_id):
    order = _get_order_or_404(order_id)
    return _render_order(order)


@bp.route("/orders/<order_id>/status", methods=["POST"])
@admin_required
def change_order_status(order_id):
    repo = OrderRepository(get_db())
    order = _get_order_or_404(order_id)
    try:
        new_status = OrderStatus(request.form.get("status", ""))
        order.change_status(new_status)
    except (ValueError, InvalidTransition) as error:
        # ValueError: not a known status. InvalidTransition: not allowed from the current status.
        flash(str(error) if isinstance(error, InvalidTransition) else "Unknown order status.")
        return _render_order(repo.get_by_id(order_id)), 400

    repo.update(order)
    flash(f"Order status changed to {new_status.label}.")
    return redirect(url_for("admin.order_detail", order_id=order_id))


@bp.route("/orders/<order_id>/payment", methods=["POST"])
@admin_required
def change_payment_status(order_id):
    repo = OrderRepository(get_db())
    order = _get_order_or_404(order_id)
    try:
        new_status = PaymentStatus(request.form.get("status", ""))
        order.change_payment_status(new_status)
    except (ValueError, InvalidTransition) as error:
        flash(str(error) if isinstance(error, InvalidTransition) else "Unknown payment status.")
        return _render_order(repo.get_by_id(order_id)), 400

    repo.update(order)
    flash(f"Payment status changed to {new_status.label}.")
    return redirect(url_for("admin.order_detail", order_id=order_id))


def _get_order_or_404(order_id):
    order = OrderRepository(get_db()).get_by_id(order_id)
    if order is None:
        abort(404)
    return order


def _render_order(order):
    customer = UserRepository(get_db()).get_by_id(order.user_id)
    return render_template("admin/order_detail.html", order=order, customer=customer)


def _customers_for(orders):
    # {user_id: User} for the customers in the list, so the page can show their names.
    users = UserRepository(get_db())
    return {user_id: users.get_by_id(user_id) for user_id in {order.user_id for order in orders}}


def _parse_status(value):
    if not value:
        return None
    try:
        return OrderStatus(value)
    except ValueError:
        flash("Unknown status in the filter. Showing all statuses.")
        return None


def _parse_date(value, field_name):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        flash(f"{field_name} is not a valid date. It was ignored.")
        return None


# A4 Answer questions. See docs/plans/a4-answer-question-sequence.md.


@bp.route("/questions")
@admin_required
def questions():
    questions = QuestionRepository(get_db()).get_all()  # open first, then newest
    users = UserRepository(get_db())
    orders = OrderRepository(get_db())
    return render_template(
        "admin/questions.html",
        questions=questions,
        customers={user_id: users.get_by_id(user_id) for user_id in {q.asked_by for q in questions}},
        orders={order_id: orders.get_by_id(order_id) for order_id in {q.order_id for q in questions}},
    )


@bp.route("/questions/<question_id>")
@admin_required
def question_detail(question_id):
    question = _get_question_or_404(question_id)
    return _render_question(question)


@bp.route("/questions/<question_id>/answer", methods=["POST"])
@admin_required
def answer_question(question_id):
    question = _get_question_or_404(question_id)
    text = request.form.get("text", "").strip()

    # A question can only be answered once (docs/plans/c5-question-status-state.md).
    if question.is_answered():
        flash("This question is already answered.")
        return _render_question(question), 400

    error = None
    if not text:
        error = "Write an answer before you send it."
    elif len(text) > MAX_TEXT_LENGTH:
        error = f"The answer can be at most {MAX_TEXT_LENGTH} characters."
    if error:
        flash(error)
        return _render_question(question, answer_text=text), 400

    question.answer(text, g.user)
    QuestionRepository(get_db()).update(question)
    flash("The answer is saved. The customer sees it on their order page.")
    return redirect(url_for("admin.questions"))


def _get_question_or_404(question_id):
    question = QuestionRepository(get_db()).get_by_id(question_id)
    if question is None:
        abort(404)
    return question


def _render_question(question, answer_text=""):
    return render_template(
        "admin/question_form.html",
        question=question,
        customer=UserRepository(get_db()).get_by_id(question.asked_by),
        order=OrderRepository(get_db()).get_by_id(question.order_id),
        answer_text=answer_text,
        max_answer_length=MAX_TEXT_LENGTH,
    )
