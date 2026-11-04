from datetime import date, datetime
from decimal import Decimal

from app.models.db import IntegrityError
from app.models.food import Event
from app.models.order import GuestGroup, Order, OrderLine, OrderStatus, PaymentStatus

# Returns an order with its customer, event, lines and guest groups.
# Lines and groups are sorted by position, the order the customer added them.
_RETURN_ORDER = """
    MATCH (u:User)-[:PLACED]->(o)-[:FOR_EVENT]->(e:Event)
    RETURN o, u.id AS userId, e.name AS event,
           COLLECT {
               MATCH (o)-[c:CONTAINS]->(f:FoodItem)
               RETURN {foodItemId: f.id, itemName: c.itemName, quantity: c.quantity, unitPrice: c.unitPrice}
               ORDER BY c.position
           } AS lines,
           COLLECT {
               MATCH (o)-[h:HAS_GROUP]->(g:GuestGroup)
               RETURN g {.*} ORDER BY h.position
           } AS groups
"""


class OrderRepository:
    """Saves and loads Orders as (:Order) nodes with CONTAINS links to food items and HAS_GROUP links
    to guest groups. The rest of the app never sees Neo4j. See docs/plans/neo4j-graph-model.md."""

    def __init__(self, db):
        self.db = db

    def get_by_id(self, id):
        row = self.db.query_one("MATCH (o:Order {id: $id})" + _RETURN_ORDER, id=id)
        if row is None:
            return None
        return self._to_order(row)

    def get_by_user(self, user_id):
        # C4: a customer's own orders, newest first.
        rows = self.db.query(
            "MATCH (:User {id: $user_id})-[:PLACED]->(o:Order)" + _RETURN_ORDER + "ORDER BY o.createdAt DESC",
            user_id=user_id,
        )
        return [self._to_order(row) for row in rows]

    def find(self, status=None, from_date=None, to_date=None):
        # A3: all orders, sorted by event date. Each filter is optional.
        # Dates are ISO strings ("2027-05-15"), which compare and sort like dates.
        conditions = ["true"]
        if status is not None:
            conditions.append("o.orderStatus = $status")
        if from_date is not None:
            conditions.append("o.eventDate >= $from_date")
        if to_date is not None:
            conditions.append("o.eventDate <= $to_date")
        rows = self.db.query(
            "MATCH (o:Order) WHERE " + " AND ".join(conditions) + _RETURN_ORDER + "ORDER BY o.eventDate, o.createdAt",
            status=status.value if status else None,
            from_date=from_date.isoformat() if from_date else None,
            to_date=to_date.isoformat() if to_date else None,
        )
        return [self._to_order(row) for row in rows]

    def add(self, order):
        # One statement: the order, its lines and its groups are saved together, or not at all.
        # If the customer, the event or one of the food items doesn't exist, no row is left
        # after the WHERE, so nothing is created (like a foreign key in SQLite).
        item_ids = list(dict.fromkeys(line.food_item_id for line in order.lines))
        row = self.db.query_one(
            """
            MATCH (u:User {id: $user_id}), (e:Event {name: $event})
            OPTIONAL MATCH (f:FoodItem) WHERE f.id IN $item_ids
            WITH u, e, collect(f) AS items
            WHERE size(items) = size($item_ids)
            CREATE (u)-[:PLACED]->(o:Order)-[:FOR_EVENT]->(e)
            SET o = $props
            FOREACH (line IN $lines |
                FOREACH (f IN [item IN items WHERE item.id = line.foodItemId] |
                    CREATE (o)-[:CONTAINS {position: line.position, itemName: line.itemName,
                                           quantity: line.quantity, unitPrice: line.unitPrice}]->(f)))
            FOREACH (group IN $groups |
                CREATE (o)-[:HAS_GROUP {position: group.position}]->(:GuestGroup {
                    groupName: group.groupName, numberOfGuests: group.numberOfGuests,
                    allergyNotes: group.allergyNotes, dietaryNotes: group.dietaryNotes}))
            RETURN o.id AS id
            """,
            user_id=order.user_id,
            event=order.event.name,
            item_ids=item_ids,
            props=self._properties(order),
            lines=[
                {
                    "position": i,
                    "foodItemId": line.food_item_id,
                    "itemName": line.item_name,
                    "quantity": line.quantity,
                    "unitPrice": str(line.unit_price),  # Decimal as text
                }
                for i, line in enumerate(order.lines)
            ],
            groups=[
                {
                    "position": i,
                    "groupName": g.group_name,
                    "numberOfGuests": g.number_of_guests,
                    "allergyNotes": g.allergy_notes,
                    "dietaryNotes": g.dietary_notes,
                }
                for i, g in enumerate(order.guest_groups)
            ],
        )
        if row is None:
            raise IntegrityError("The order was not saved: the customer, the event or a food item doesn't exist.")

    def update(self, order):
        # Saves the fields that can change after an order is made, such as the two statuses (A3).
        self.db.query(
            """
            MATCH (o:Order {id: $id})
            SET o.eventDate = $event_date, o.numberOfGuests = $number_of_guests,
                o.deliveryAddress = $delivery_address,
                o.orderStatus = $order_status, o.paymentStatus = $payment_status
            """,
            id=order.id,
            event_date=order.event_date.isoformat(),
            number_of_guests=order.number_of_guests,
            delivery_address=order.delivery_address,
            order_status=order.order_status.value,
            payment_status=order.payment_status.value,
        )

    def _properties(self, order):
        return {
            "id": order.id,
            "eventDate": order.event_date.isoformat(),  # e.g. "2027-05-15"
            "numberOfGuests": order.number_of_guests,
            "deliveryAddress": order.delivery_address,
            "createdAt": order.created_at.isoformat(),  # e.g. "2026-10-25T14:30:00"
            "orderStatus": order.order_status.value,
            "paymentStatus": order.payment_status.value,
        }

    def _to_order(self, row):
        o = row["o"]
        return Order(
            id=o["id"],
            user_id=row["userId"],
            event=Event(row["event"]),
            event_date=date.fromisoformat(o["eventDate"]),
            number_of_guests=o["numberOfGuests"],
            delivery_address=o["deliveryAddress"],
            created_at=datetime.fromisoformat(o["createdAt"]),
            order_status=OrderStatus(o["orderStatus"]),
            payment_status=PaymentStatus(o["paymentStatus"]),
            lines=[
                OrderLine(
                    food_item_id=line["foodItemId"],
                    item_name=line["itemName"],
                    quantity=line["quantity"],
                    unit_price=Decimal(line["unitPrice"]),
                )
                for line in row["lines"]
            ],
            guest_groups=[
                GuestGroup(
                    group_name=g["groupName"],
                    number_of_guests=g["numberOfGuests"],
                    allergy_notes=g["allergyNotes"],
                    dietary_notes=g["dietaryNotes"],
                )
                for g in row["groups"]
            ],
        )
