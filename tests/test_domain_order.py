from datetime import date
from decimal import Decimal

import pytest

from app.models.food import Event
from app.models.order import InvalidTransition, Order, OrderLine, OrderStatus, PaymentStatus

S = OrderStatus
P = PaymentStatus


def make_order(**changes):
    values = dict(
        user_id="kari",
        event=Event("Wedding"),
        event_date=date(2027, 5, 15),
        number_of_guests=40,
        delivery_address="Bryggen 1, Bergen",
        lines=[
            OrderLine("soup", "Bergensk fiskesuppe", 40, Decimal("129.00")),
            OrderLine("cake", "Bløtkake", 4, Decimal("590.00")),
        ],
    )
    values.update(changes)
    return Order(**values)


def test_new_order_is_submitted_and_not_paid():
    order = make_order()

    assert order.order_status == S.SUBMITTED
    assert order.payment_status == P.NOT_PAID


def test_total_adds_up_all_lines():
    assert make_order().total() == Decimal("7520.00")  # 40 * 129 + 4 * 590


def test_total_of_order_without_lines_is_zero():
    assert make_order(lines=[]).total() == Decimal("0")


def test_belongs_to_only_the_customer_who_ordered():
    order = make_order(user_id="kari")

    assert order.belongs_to("kari")
    assert not order.belongs_to("ola")


def test_labels_are_readable():
    assert S.IN_PREPARATION.label == "In preparation"
    assert P.DEPOSIT_PAID.label == "Deposit paid"


# Every arrow in docs/plans/a3-order-status-state.md.
@pytest.mark.parametrize(
    "start, new",
    [
        (S.SUBMITTED, S.APPROVED),
        (S.SUBMITTED, S.REJECTED),
        (S.APPROVED, S.IN_PREPARATION),
        (S.APPROVED, S.CANCELLED),
        (S.IN_PREPARATION, S.DELIVERED),
        (S.IN_PREPARATION, S.CANCELLED),
    ],
)
def test_allowed_order_status_changes(start, new):
    order = make_order(order_status=start)

    order.change_status(new)

    assert order.order_status == new


@pytest.mark.parametrize(
    "start, new",
    [
        (S.SUBMITTED, S.DELIVERED),  # can't skip approval and preparation
        (S.SUBMITTED, S.SUBMITTED),
        (S.APPROVED, S.SUBMITTED),  # can't go back
        (S.DELIVERED, S.SUBMITTED),
        (S.REJECTED, S.APPROVED),  # final states stay final
        (S.CANCELLED, S.APPROVED),
    ],
)
def test_other_order_status_changes_are_refused(start, new):
    order = make_order(order_status=start)

    with pytest.raises(InvalidTransition):
        order.change_status(new)

    assert order.order_status == start  # unchanged


def test_final_order_statuses_have_no_next_status():
    for status in (S.DELIVERED, S.REJECTED, S.CANCELLED):
        assert make_order(order_status=status).allowed_next_statuses() == []


# Every arrow in docs/plans/a3-payment-status-state.md.
@pytest.mark.parametrize(
    "start, new",
    [
        (P.NOT_PAID, P.DEPOSIT_PAID),
        (P.NOT_PAID, P.INVOICED),
        (P.DEPOSIT_PAID, P.INVOICED),
        (P.INVOICED, P.PAID),
    ],
)
def test_allowed_payment_status_changes(start, new):
    order = make_order(payment_status=start)

    order.change_payment_status(new)

    assert order.payment_status == new


@pytest.mark.parametrize(
    "start, new",
    [
        (P.NOT_PAID, P.PAID),  # must be invoiced first
        (P.DEPOSIT_PAID, P.NOT_PAID),
        (P.INVOICED, P.DEPOSIT_PAID),
        (P.PAID, P.NOT_PAID),
    ],
)
def test_other_payment_status_changes_are_refused(start, new):
    order = make_order(payment_status=start)

    with pytest.raises(InvalidTransition):
        order.change_payment_status(new)

    assert order.payment_status == start


def test_order_and_payment_status_are_independent():
    order = make_order()

    order.change_payment_status(P.DEPOSIT_PAID)

    assert order.order_status == S.SUBMITTED
