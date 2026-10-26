from app.models.food import MAX_QUANTITY
from app.models.order import OrderLine


class Cart:
    """The customer's cart (C2). It only holds item IDs and quantities, so it fits in the Flask session.
    Names and prices are read from the food items at checkout. See docs/plans/c2-cart-activity.md."""

    def __init__(self, quantities=None):
        self.quantities = dict(quantities or {})  # {food_item_id: quantity}

    @classmethod
    def from_dict(cls, quantities):
        return cls(quantities)

    def to_dict(self):
        return dict(self.quantities)

    def set_quantity(self, item, qty):
        # Quantity 0 removes the item. Any other quantity must be between the item's minimum and 10,000.
        if qty == 0:
            self.remove(item.id)
            return
        if not item.accepts_quantity(qty):
            raise ValueError(f"{item.name}: choose between {item.min_order} and {MAX_QUANTITY:,} pieces.")
        self.quantities[item.id] = qty

    def remove(self, item_id):
        self.quantities.pop(item_id, None)

    def is_empty(self):
        return not self.quantities

    def item_ids(self):
        return list(self.quantities)

    def count(self):
        return len(self.quantities)

    def to_order_lines(self, items):
        # items: the FoodItems in the cart. The name and price are copied, so the order keeps them if the item changes.
        return [OrderLine(item.id, item.name, self.quantities[item.id], item.price) for item in items]
