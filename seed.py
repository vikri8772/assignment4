"""Fill the database with synthetic sample data.

Run with:  python seed.py
WARNING: this deletes everything in the database first.

All people, e-mails and passwords here are made up for testing.
"""

from datetime import date, datetime
from decimal import Decimal

from werkzeug.security import generate_password_hash

from app import create_app
from app.models.db import get_db, init_db
from app.models.food import Diet, Event, FoodItem
from app.models.food_item_repository import FoodItemRepository
from app.models.order import GuestGroup, Order, OrderLine, OrderStatus, PaymentStatus
from app.models.order_repository import OrderRepository
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


FISH_SOUP, PRAWN_SANDWICH, PINNEKJOTT, RIBBE, CAKE, LASAGNE, WRAP = FOOD_ITEMS[:7]


def line(item, quantity):
    # An order line keeps the item's name and price from when the order was made.
    return OrderLine(food_item_id=item.id, item_name=item.name, quantity=quantity, unit_price=item.price)


# Synthetic orders, so A3 and C4 have something to show before C3 is built.
# They cover every order status except Rejected, and every payment status.
# Each order is (customer e-mail, Order without user_id).
ORDERS = [
    (
        "kari@example.test",
        Order(
            user_id="",
            event=WEDDING,
            event_date=date(2027, 5, 22),
            number_of_guests=80,
            delivery_address="Solstrand Hotel, Os",
            lines=[line(FISH_SOUP, 80), line(CAKE, 7)],
            guest_groups=[
                GuestGroup("Adults", 70, allergy_notes="3 nut allergies, 1 shellfish", dietary_notes="5 vegetarian"),
                GuestGroup("Children", 10, allergy_notes="1 milk allergy"),
            ],
            created_at=datetime(2026, 10, 20, 9, 15),
        ),
    ),
    (
        "kari@example.test",
        Order(
            user_id="",
            event=JULEBORD,
            event_date=date(2026, 12, 11),
            number_of_guests=35,
            delivery_address="Strandkaien 2, 5013 Bergen",
            lines=[line(PINNEKJOTT, 20), line(RIBBE, 15)],
            guest_groups=[GuestGroup("Staff", 35, allergy_notes="2 gluten intolerant")],
            order_status=OrderStatus.APPROVED,
            payment_status=PaymentStatus.DEPOSIT_PAID,
            created_at=datetime(2026, 10, 2, 14, 30),
        ),
    ),
    (
        "kari@example.test",
        Order(
            user_id="",
            event=CONFIRMATION,
            event_date=date(2026, 10, 3),
            number_of_guests=25,
            delivery_address="Fjellveien 12, 5019 Bergen",
            lines=[line(PRAWN_SANDWICH, 25), line(CAKE, 3)],
            guest_groups=[GuestGroup("Family", 25)],
            order_status=OrderStatus.CANCELLED,
            created_at=datetime(2026, 8, 15, 11, 0),
        ),
    ),
    (
        "ola@example.test",
        Order(
            user_id="",
            event=CONFERENCE,
            event_date=date(2026, 11, 4),
            number_of_guests=25,
            delivery_address="Marineholmen, Thormøhlens gate 55, 5006 Bergen",
            lines=[line(PRAWN_SANDWICH, 25), line(WRAP, 20)],
            guest_groups=[
                GuestGroup("Participants", 22, dietary_notes="4 vegan"),
                GuestGroup("Speakers", 3, allergy_notes="1 sesame allergy"),
            ],
            order_status=OrderStatus.IN_PREPARATION,
            payment_status=PaymentStatus.INVOICED,
            created_at=datetime(2026, 10, 10, 8, 45),
        ),
    ),
    (
        "ola@example.test",
        Order(
            user_id="",
            event=BIRTHDAY,
            event_date=date(2026, 9, 19),
            number_of_guests=15,
            delivery_address="Nordnesgaten 8, 5005 Bergen",
            lines=[line(LASAGNE, 15), line(CAKE, 2)],
            guest_groups=[GuestGroup("Guests", 15, dietary_notes="2 vegetarian")],
            order_status=OrderStatus.DELIVERED,
            payment_status=PaymentStatus.PAID,
            created_at=datetime(2026, 9, 1, 19, 20),
        ),
    ),
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

    orders = OrderRepository(db)
    for email, order in ORDERS:
        order.user_id = users.get_by_email(email).id
        orders.add(order)

    print(
        f"Seeded {len(EVENTS)} events, {len(DIETS)} diets, {len(FOOD_ITEMS)} food items, "
        f"{len(USERS)} users and {len(ORDERS)} orders."
    )


if __name__ == "__main__":
    with create_app().app_context():
        seed()
