from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.controllers.auth import admin_required
from app.models.db import get_db
from app.models.order import InvalidTransition, OrderStatus, PaymentStatus
from app.models.order_repository import OrderRepository
from app.models.user_repository import UserRepository

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def items_overview():
    # Placeholder until A1 (food items) is built.
    return render_template("admin/items_overview.html")


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
