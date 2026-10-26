from datetime import date, datetime
from decimal import Decimal

from app.models.food import Event
from app.models.order import GuestGroup, Order, OrderLine, OrderStatus, PaymentStatus


class OrderRepository:
    """Saves and loads Orders with their lines and guest groups. The rest of the app never sees the tables."""

    def __init__(self, db):
        self.db = db

    def get_by_id(self, id):
        row = self.db.execute("SELECT * FROM orders WHERE id = ?", (id,)).fetchone()
        if row is None:
            return None
        return self._to_order(row)

    def get_by_user(self, user_id):
        # C4: a customer's own orders, newest first.
        rows = self.db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        return [self._to_order(row) for row in rows]

    def find(self, status=None, from_date=None, to_date=None):
        # A3: all orders, sorted by event date. Each filter is optional.
        sql = "SELECT * FROM orders WHERE 1 = 1"
        params = []
        if status is not None:
            sql += " AND order_status = ?"
            params.append(status.value)
        if from_date is not None:
            sql += " AND event_date >= ?"
            params.append(from_date.isoformat())
        if to_date is not None:
            sql += " AND event_date <= ?"
            params.append(to_date.isoformat())
        sql += " ORDER BY event_date, created_at"
        rows = self.db.execute(sql, params).fetchall()
        return [self._to_order(row) for row in rows]

    def add(self, order):
        # The order, its lines and its groups are saved together, or not at all.
        with self.db:
            self.db.execute(
                """
                INSERT INTO orders (id, user_id, event_name, event_date, number_of_guests,
                                    delivery_address, created_at, order_status, payment_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.id,
                    order.user_id,
                    order.event.name,
                    order.event_date.isoformat(),
                    order.number_of_guests,
                    order.delivery_address,
                    order.created_at.isoformat(),
                    order.order_status.value,
                    order.payment_status.value,
                ),
            )
            self.db.executemany(
                """
                INSERT INTO order_line (order_id, position, food_item_id, item_name, quantity, unit_price)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (order.id, i, line.food_item_id, line.item_name, line.quantity, str(line.unit_price))
                    for i, line in enumerate(order.lines)
                ],
            )
            self.db.executemany(
                """
                INSERT INTO guest_group (order_id, position, group_name, number_of_guests, allergy_notes, dietary_notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (order.id, i, g.group_name, g.number_of_guests, g.allergy_notes, g.dietary_notes)
                    for i, g in enumerate(order.guest_groups)
                ],
            )

    def update(self, order):
        # Saves the fields that can change after an order is made, such as the two statuses (A3).
        with self.db:
            self.db.execute(
                """
                UPDATE orders
                SET event_date = ?, number_of_guests = ?, delivery_address = ?, order_status = ?, payment_status = ?
                WHERE id = ?
                """,
                (
                    order.event_date.isoformat(),
                    order.number_of_guests,
                    order.delivery_address,
                    order.order_status.value,
                    order.payment_status.value,
                    order.id,
                ),
            )

    def _to_order(self, row):
        # Turns one orders row, plus its lines and groups, into an Order.
        id = row["id"]
        lines = self.db.execute(
            "SELECT * FROM order_line WHERE order_id = ? ORDER BY position", (id,)
        ).fetchall()
        groups = self.db.execute(
            "SELECT * FROM guest_group WHERE order_id = ? ORDER BY position", (id,)
        ).fetchall()
        return Order(
            id=id,
            user_id=row["user_id"],
            event=Event(row["event_name"]),
            event_date=date.fromisoformat(row["event_date"]),
            number_of_guests=row["number_of_guests"],
            delivery_address=row["delivery_address"],
            created_at=datetime.fromisoformat(row["created_at"]),
            order_status=OrderStatus(row["order_status"]),
            payment_status=PaymentStatus(row["payment_status"]),
            lines=[
                OrderLine(
                    food_item_id=r["food_item_id"],
                    item_name=r["item_name"],
                    quantity=r["quantity"],
                    unit_price=Decimal(r["unit_price"]),
                )
                for r in lines
            ],
            guest_groups=[
                GuestGroup(
                    group_name=r["group_name"],
                    number_of_guests=r["number_of_guests"],
                    allergy_notes=r["allergy_notes"],
                    dietary_notes=r["dietary_notes"],
                )
                for r in groups
            ],
        )
