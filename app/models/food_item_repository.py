from decimal import Decimal

from app.models.food import Diet, Event, FoodItem


class FoodItemRepository:
    """Saves and loads FoodItems. The rest of the app never sees the tables."""

    def __init__(self, db):
        self.db = db

    def get_all(self):
        rows = self.db.execute("SELECT * FROM food_item ORDER BY name").fetchall()
        return [self._to_food_item(row) for row in rows]

    def get_by_id(self, id):
        row = self.db.execute("SELECT * FROM food_item WHERE id = ?", (id,)).fetchone()
        if row is None:
            return None
        return self._to_food_item(row)

    def get_published_items(self, event):
        rows = self.db.execute(
            """
            SELECT food_item.* FROM food_item
            JOIN food_item_event ON food_item_event.food_item_id = food_item.id
            WHERE food_item.published = 1 AND food_item_event.event_name = ?
            ORDER BY food_item.name
            """,
            (event.name,),
        ).fetchall()
        return [self._to_food_item(row) for row in rows]

    def add(self, item):
        # "with self.db" saves everything together, or nothing if something fails.
        with self.db:
            self.db.execute(
                """
                INSERT INTO food_item (id, name, description, price, min_order, picture_path, published)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (item.id, item.name, item.desc, str(item.price), item.min_order, item.picture_path, item.published),
            )
            self._save_lists(item)

    def update(self, item):
        with self.db:
            self.db.execute(
                """
                UPDATE food_item
                SET name = ?, description = ?, price = ?, min_order = ?, picture_path = ?, published = ?
                WHERE id = ?
                """,
                (item.name, item.desc, str(item.price), item.min_order, item.picture_path, item.published, item.id),
            )
            # Simplest way to update the lists: remove the old links and save the new ones.
            self.db.execute("DELETE FROM food_item_event WHERE food_item_id = ?", (item.id,))
            self.db.execute("DELETE FROM food_item_diet WHERE food_item_id = ?", (item.id,))
            self.db.execute("DELETE FROM food_item_allergen WHERE food_item_id = ?", (item.id,))
            self._save_lists(item)

    def delete(self, id):
        # The links to events, diets and allergens are deleted too (ON DELETE CASCADE).
        with self.db:
            self.db.execute("DELETE FROM food_item WHERE id = ?", (id,))

    # is_used_in_orders(id) is added when the order tables exist (see docs/plans/skeleton-plan.md).

    # Events and diets are fixed lists, created by seed.py.

    def get_events(self):
        rows = self.db.execute("SELECT name FROM event ORDER BY name").fetchall()
        return [Event(row["name"]) for row in rows]

    def add_event(self, event):
        with self.db:
            self.db.execute("INSERT INTO event (name) VALUES (?)", (event.name,))

    def get_diets(self):
        rows = self.db.execute("SELECT name FROM diet ORDER BY name").fetchall()
        return [Diet(row["name"]) for row in rows]

    def add_diet(self, diet):
        with self.db:
            self.db.execute("INSERT INTO diet (name) VALUES (?)", (diet.name,))

    def _save_lists(self, item):
        self.db.executemany(
            "INSERT INTO food_item_event (food_item_id, event_name) VALUES (?, ?)",
            [(item.id, event.name) for event in item.events],
        )
        self.db.executemany(
            "INSERT INTO food_item_diet (food_item_id, diet_name) VALUES (?, ?)",
            [(item.id, diet.name) for diet in item.diets],
        )
        self.db.executemany(
            "INSERT INTO food_item_allergen (food_item_id, allergen) VALUES (?, ?)",
            [(item.id, allergen) for allergen in item.allergens],
        )

    def _to_food_item(self, row):
        # Turns one food_item row, plus its rows in the link tables, into a FoodItem.
        id = row["id"]
        events = self.db.execute(
            "SELECT event_name FROM food_item_event WHERE food_item_id = ? ORDER BY event_name", (id,)
        ).fetchall()
        diets = self.db.execute(
            "SELECT diet_name FROM food_item_diet WHERE food_item_id = ? ORDER BY diet_name", (id,)
        ).fetchall()
        allergens = self.db.execute(
            "SELECT allergen FROM food_item_allergen WHERE food_item_id = ? ORDER BY allergen", (id,)
        ).fetchall()
        return FoodItem(
            id=id,
            name=row["name"],
            desc=row["description"],
            price=Decimal(row["price"]),
            min_order=row["min_order"],
            picture_path=row["picture_path"],
            published=bool(row["published"]),
            events=[Event(r["event_name"]) for r in events],
            diets=[Diet(r["diet_name"]) for r in diets],
            allergens=[r["allergen"] for r in allergens],
        )
