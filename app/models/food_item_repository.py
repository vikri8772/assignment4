from decimal import Decimal

from app.models.db import IntegrityError
from app.models.food import Diet, Event, FoodItem

# Returns a food item with the names of its events and diets, sorted.
# Used at the end of every query that loads food items.
_RETURN_ITEM = """
    RETURN f,
           COLLECT { MATCH (f)-[:SERVED_AT]->(e:Event) RETURN e.name ORDER BY e.name } AS events,
           COLLECT { MATCH (f)-[:SUITS]->(d:Diet) RETURN d.name ORDER BY d.name } AS diets
"""

# Finds the events and diets an item should link to. If one of them doesn't exist,
# no row is left after the WHERE, so nothing is saved (like a foreign key in SQLite).
_MATCH_EVENTS_AND_DIETS = """
    OPTIONAL MATCH (e:Event) WHERE e.name IN $events
    WITH f, collect(e) AS events
    OPTIONAL MATCH (d:Diet) WHERE d.name IN $diets
    WITH f, events, collect(d) AS diets
    WHERE size(events) = size($events) AND size(diets) = size($diets)
"""


class FoodItemRepository:
    """Saves and loads FoodItems as (:FoodItem) nodes linked to (:Event) and (:Diet) nodes.
    The rest of the app never sees Neo4j. See docs/plans/neo4j-graph-model.md."""

    def __init__(self, db):
        self.db = db

    def get_all(self):
        rows = self.db.query("MATCH (f:FoodItem)" + _RETURN_ITEM + "ORDER BY f.name")
        return [self._to_food_item(row) for row in rows]

    def get_by_id(self, id):
        row = self.db.query_one("MATCH (f:FoodItem {id: $id})" + _RETURN_ITEM, id=id)
        if row is None:
            return None
        return self._to_food_item(row)

    def get_published_items(self, event):
        rows = self.db.query(
            "MATCH (f:FoodItem {published: true})-[:SERVED_AT]->(:Event {name: $event})"
            + _RETURN_ITEM
            + "ORDER BY f.name",
            event=event.name,
        )
        return [self._to_food_item(row) for row in rows]

    def add(self, item):
        # One statement: the item and its links are saved together, or not at all.
        row = self.db.query_one(
            "WITH null AS f"
            + _MATCH_EVENTS_AND_DIETS
            + """
            CREATE (f2:FoodItem)
            SET f2 = $props
            FOREACH (e IN events | CREATE (f2)-[:SERVED_AT]->(e))
            FOREACH (d IN diets | CREATE (f2)-[:SUITS]->(d))
            RETURN f2.id AS id
            """,
            props=self._properties(item),
            **self._link_names(item),
        )
        if row is None:
            raise IntegrityError(f"{item.name} was not saved: an event or diet doesn't exist.")

    def update(self, item):
        # Simplest way to update the lists: remove the old links and make the new ones.
        row = self.db.query_one(
            "MATCH (f:FoodItem {id: $id})"
            + _MATCH_EVENTS_AND_DIETS
            + """
            SET f = $props
            WITH f, events, diets
            CALL (f) { MATCH (f)-[r:SERVED_AT|SUITS]->() DELETE r }
            FOREACH (e IN events | CREATE (f)-[:SERVED_AT]->(e))
            FOREACH (d IN diets | CREATE (f)-[:SUITS]->(d))
            RETURN f.id AS id
            """,
            id=item.id,
            props=self._properties(item),
            **self._link_names(item),
        )
        if row is None:
            raise IntegrityError(f"{item.name} was not saved: it, or one of its events or diets, doesn't exist.")

    def delete(self, id):
        # An item that is in an order can't be deleted (A1), so the order keeps pointing to it.
        row = self.db.query_one(
            """
            MATCH (f:FoodItem {id: $id})
            WITH f, EXISTS { (:Order)-[:CONTAINS]->(f) } AS used
            FOREACH (_ IN CASE WHEN used THEN [] ELSE [1] END | DETACH DELETE f)
            RETURN used
            """,
            id=id,
        )
        if row is not None and row["used"]:
            raise IntegrityError("The food item is used in orders, so it can't be deleted.")

    def is_used_in_orders(self, id):
        # True if any order CONTAINS this item. Such items can't be deleted (A1).
        row = self.db.query_one(
            "MATCH (f:FoodItem {id: $id}) RETURN EXISTS { (:Order)-[:CONTAINS]->(f) } AS used", id=id
        )
        return row is not None and row["used"]

    # Events and diets are fixed lists, created by seed.py.

    def get_events(self):
        rows = self.db.query("MATCH (e:Event) RETURN e.name AS name ORDER BY name")
        return [Event(row["name"]) for row in rows]

    def add_event(self, event):
        self.db.query("CREATE (:Event {name: $name})", name=event.name)

    def get_diets(self):
        rows = self.db.query("MATCH (d:Diet) RETURN d.name AS name ORDER BY name")
        return [Diet(row["name"]) for row in rows]

    def add_diet(self, diet):
        self.db.query("CREATE (:Diet {name: $name})", name=diet.name)

    def _properties(self, item):
        # The node's properties. A None picture path is left out, because Neo4j doesn't store nulls.
        props = {
            "id": item.id,
            "name": item.name,
            "desc": item.desc,
            "price": str(item.price),  # Decimal as text, e.g. "129.00"
            "minOrder": item.min_order,
            "published": item.published,
            "allergens": list(item.allergens),
        }
        if item.picture_path is not None:
            props["picturePath"] = item.picture_path
        return props

    def _link_names(self, item):
        # The names without duplicates, so the size check in _MATCH_EVENTS_AND_DIETS works.
        return {
            "events": list(dict.fromkeys(e.name for e in item.events)),
            "diets": list(dict.fromkeys(d.name for d in item.diets)),
        }

    def _to_food_item(self, row):
        f = row["f"]
        return FoodItem(
            id=f["id"],
            name=f["name"],
            desc=f["desc"],
            price=Decimal(f["price"]),
            min_order=f["minOrder"],
            picture_path=f.get("picturePath"),
            published=f["published"],
            events=[Event(name) for name in row["events"]],
            diets=[Diet(name) for name in row["diets"]],
            allergens=sorted(f.get("allergens", [])),  # sorted, as they were in SQLite
        )
