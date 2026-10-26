from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import uuid4

from app.models.food import Event


class OrderStatus(Enum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    IN_PREPARATION = "IN_PREPARATION"
    DELIVERED = "DELIVERED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").capitalize()  # IN_PREPARATION -> "In preparation"


class PaymentStatus(Enum):
    NOT_PAID = "NOT_PAID"
    DEPOSIT_PAID = "DEPOSIT_PAID"
    INVOICED = "INVOICED"
    PAID = "PAID"

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").capitalize()


# The allowed changes, copied from docs/plans/a3-order-status-state.md.
# A status that is missing here is final.
ORDER_TRANSITIONS = {
    OrderStatus.SUBMITTED: [OrderStatus.APPROVED, OrderStatus.REJECTED],
    OrderStatus.APPROVED: [OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED],
    OrderStatus.IN_PREPARATION: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
}

# Copied from docs/plans/a3-payment-status-state.md.
PAYMENT_TRANSITIONS = {
    PaymentStatus.NOT_PAID: [PaymentStatus.DEPOSIT_PAID, PaymentStatus.INVOICED],
    PaymentStatus.DEPOSIT_PAID: [PaymentStatus.INVOICED],
    PaymentStatus.INVOICED: [PaymentStatus.PAID],
}


class InvalidTransition(Exception):
    """A status change that the state machine does not allow."""


@dataclass
class GuestGroup:
    # Allergies are stored per group, not per named guest (GDPR note in the data pack).
    group_name: str
    number_of_guests: int
    allergy_notes: str = ""
    dietary_notes: str = ""


@dataclass
class OrderLine:
    food_item_id: str
    item_name: str  # copied from the food item, so the order keeps its name if the item changes
    quantity: int
    unit_price: Decimal  # the price when the order was made

    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Order:
    user_id: str
    event: Event
    event_date: date
    number_of_guests: int
    delivery_address: str
    lines: list[OrderLine] = field(default_factory=list)
    guest_groups: list[GuestGroup] = field(default_factory=list)
    order_status: OrderStatus = OrderStatus.SUBMITTED
    payment_status: PaymentStatus = PaymentStatus.NOT_PAID
    created_at: datetime = field(default_factory=lambda: datetime.now().replace(microsecond=0))
    id: str = field(default_factory=lambda: uuid4().hex)

    def belongs_to(self, user_id: str) -> bool:
        return self.user_id == user_id

    def total(self) -> Decimal:
        return sum((line.subtotal() for line in self.lines), Decimal("0"))

    def allowed_next_statuses(self) -> list[OrderStatus]:
        return list(ORDER_TRANSITIONS.get(self.order_status, []))

    def change_status(self, new_status: OrderStatus):
        if new_status not in self.allowed_next_statuses():
            raise InvalidTransition(f"An order can't go from {self.order_status.label} to {new_status.label}.")
        self.order_status = new_status

    def allowed_next_payment_statuses(self) -> list[PaymentStatus]:
        return list(PAYMENT_TRANSITIONS.get(self.payment_status, []))

    def change_payment_status(self, new_status: PaymentStatus):
        if new_status not in self.allowed_next_payment_statuses():
            raise InvalidTransition(f"Payment can't go from {self.payment_status.label} to {new_status.label}.")
        self.payment_status = new_status
