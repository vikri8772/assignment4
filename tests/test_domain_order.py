from datetime import date
from decimal import Decimal

import pytest

from app.models.food import Event
from app.models.order import MAX_GUESTS, GuestGroup, InvalidTransition, Order, OrderLine, OrderStatus, PaymentStatus

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


# C3: the checks on a new order. See docs/plans/c3-checkout-sequence.md.

TODAY = date(2027, 1, 10)


def valid_order(**changes):
    changes.setdefault(
        "guest_groups", [GuestGroup("Adults", 30, allergy_notes="2 nut allergies"), GuestGroup("Children", 10)]
    )
    return make_order(**changes)


def test_valid_order_has_no_problems():
    assert valid_order().problems(TODAY) == []


def test_event_today_is_allowed_but_not_in_the_past():
    assert valid_order(event_date=TODAY).problems(TODAY) == []
    assert "past" in valid_order(event_date=date(2027, 1, 9)).problems(TODAY)[0]


@pytest.mark.parametrize("guests", [0, MAX_GUESTS + 1])
def test_number_of_guests_must_be_1_to_10000(guests):
    order = valid_order(number_of_guests=guests, guest_groups=[GuestGroup("All", guests)])

    assert any("number of guests" in p for p in order.problems(TODAY))


@pytest.mark.parametrize("address", ["", "Bgn", "x" * 201])
def test_address_length_is_checked(address):
    assert any("address" in p for p in valid_order(delivery_address=address).problems(TODAY))


def test_order_needs_food():
    assert "The order has no food." in valid_order(lines=[]).problems(TODAY)


def test_order_needs_a_guest_group():
    assert "Add at least one guest group." in make_order(guest_groups=[]).problems(TODAY)


@pytest.mark.parametrize("group", [GuestGroup("", 40), GuestGroup("Adults", 0)])
def test_every_group_needs_a_name_and_guests(group):
    order = make_order(guest_groups=[group])

    assert any("needs a name" in p for p in order.problems(TODAY))


def test_group_sizes_must_add_up_to_the_guests():
    problems = valid_order(number_of_guests=45).problems(TODAY)

    assert problems == ["The guest groups have 40 guests in total, but the order is for 45."]
