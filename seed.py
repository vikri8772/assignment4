"""Fill the database with synthetic sample data.

Run with:  python seed.py
WARNING: this deletes everything in the database first.

All people, e-mails and passwords here are made up for testing.
"""

from decimal import Decimal

from werkzeug.security import generate_password_hash

from app import create_app
from app.models.db import get_db, init_db
from app.models.food import Diet, Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.user import Role, User
from app.models.user_repository import UserRepository

BIRTHDAY = Event("Birthday")
CONFIRMATION = Event("Confirmation")
WEDDING = Event("Wedding")
CONFERENCE = Event("Conference")
JULEBORD = Event("Julebord")
EVENTS = [BIRTHDAY, CONFIRMATION, WEDDING, CONFERENCE, JULEBORD]

VEGETARIAN = Diet("Vegetarian")
VEGAN = Diet("Vegan")
GLUTEN_FREE = Diet("Gluten-free")
LACTOSE_FREE = Diet("Lactose-free")
HALAL = Diet("Halal")  # often asked for in the order export (data pack)
DIETS = [VEGETARIAN, VEGAN, GLUTEN_FREE, LACTOSE_FREE, HALAL]

FOOD_ITEMS = [
    FoodItem(
        name="Bergensk fiskesuppe",
        desc="Creamy fish soup with salmon, cod and root vegetables.",
        price=Decimal("129.00"),
        min_order=10,
        events=[CONFIRMATION, WEDDING, CONFERENCE],
        diets=[GLUTEN_FREE],
        allergens=["fish", "milk", "celery"],
        published=True,
    ),
    FoodItem(
        name="Rekesmørbrød",
        desc="Open sandwich with hand-peeled prawns, egg and mayonnaise.",
        price=Decimal("89.00"),
        min_order=20,
        events=[CONFIRMATION, CONFERENCE],
        allergens=["crustaceans", "egg", "gluten"],
        published=True,
    ),
    FoodItem(
        name="Pinnekjøtt",
        desc="Salted and dried lamb ribs with mashed swede and potatoes.",
        price=Decimal("349.00"),
        min_order=15,
        events=[JULEBORD],
        diets=[GLUTEN_FREE, LACTOSE_FREE],
        allergens=["celery"],
        published=True,
    ),
    FoodItem(
        name="Ribbe",
        desc="Crispy pork belly with sauerkraut, sausages and gravy.",
        price=Decimal("329.00"),
        min_order=15,
        events=[JULEBORD],
        allergens=["gluten", "milk"],
        published=True,
    ),
    FoodItem(
        name="Bløtkake",
        desc="Layered sponge cake with cream and fresh strawberries. Serves 12.",
        price=Decimal("590.00"),
        min_order=1,
        events=[BIRTHDAY, CONFIRMATION, WEDDING],
        diets=[VEGETARIAN],
        allergens=["gluten", "milk", "egg"],
        published=True,
    ),
    FoodItem(
        name="Vegetarlasagne",
        desc="Lasagne with roasted vegetables, lentils and tomato sauce.",
        price=Decimal("159.00"),
        min_order=10,
        events=[BIRTHDAY, CONFERENCE],
        diets=[VEGETARIAN],
        allergens=["gluten", "milk"],
        published=True,
    ),
    FoodItem(
        name="Grønnsakswrap",
        desc="Wrap with hummus, falafel and crunchy vegetables.",
        price=Decimal("79.00"),
        min_order=20,
        events=[CONFERENCE, BIRTHDAY],
        diets=[VEGETARIAN, VEGAN, LACTOSE_FREE],
        allergens=["gluten", "sesame"],
        published=True,
    ),
    FoodItem(
        name="Hjortegryte",
        desc="Venison stew with mushrooms and lingonberries. Not on the menu yet.",
        price=Decimal("289.00"),
        min_order=10,
        events=[WEDDING, JULEBORD],
        diets=[GLUTEN_FREE],
        allergens=["milk"],
        published=False,  # shows that unpublished items are hidden from customers
    ),
]

# Synthetic test logins. Also listed in README.md.
USERS = [
    ("Ekte Mat Admin", "admin@ektemat.test", "admin1234", Role.ADMIN),
    ("Kari Nordmann", "kari@example.test", "kunde1234", Role.CUSTOMER),
    ("Ola Nordmann", "ola@example.test", "kunde1234", Role.CUSTOMER),
]


def seed():
    init_db()
    db = get_db()

    food = FoodItemRepository(db)
    for event in EVENTS:
        food.add_event(event)
    for diet in DIETS:
        food.add_diet(diet)
    for item in FOOD_ITEMS:
        food.add(item)

    users = UserRepository(db)
    for name, email, password, role in USERS:
        users.add(User(name=name, email=email, password_hash=generate_password_hash(password), role=role))

    print(f"Seeded {len(EVENTS)} events, {len(DIETS)} diets, {len(FOOD_ITEMS)} food items and {len(USERS)} users.")


if __name__ == "__main__":
    with create_app().app_context():
        seed()
