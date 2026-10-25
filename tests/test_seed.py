from seed import FOOD_ITEMS, ORDERS, USERS, seed

from app.models.food_item_repository import FoodItemRepository
from app.models.order_repository import OrderRepository
from app.models.user_repository import UserRepository


def test_seed_creates_items_events_and_users(app, db):
    with app.app_context():
        seed()

    food = FoodItemRepository(db)
    assert len(food.get_all()) == len(FOOD_ITEMS)
    assert len(food.get_events()) == 5

    admin_email = USERS[0][1]
    assert UserRepository(db).get_by_email(admin_email).is_admin()


def test_seed_creates_orders_for_the_customers(app, db):
    with app.app_context():
        seed()

    users = UserRepository(db)
    orders = OrderRepository(db)
    assert len(orders.find()) == len(ORDERS)
    kari = users.get_by_email("kari@example.test")
    assert len(orders.get_by_user(kari.id)) == 3
