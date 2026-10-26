from seed import DIETS, FOOD_ITEMS, USERS, seed

from app.models.food_item_repository import FoodItemRepository
from app.models.user_repository import UserRepository


def test_seed_creates_items_events_and_users(app, db):
    with app.app_context():
        seed()

    food = FoodItemRepository(db)
    assert len(food.get_all()) == len(FOOD_ITEMS)
    assert len(food.get_events()) == 5
    assert len(food.get_diets()) == len(DIETS)

    admin_email = USERS[0][1]
    assert UserRepository(db).get_by_email(admin_email).is_admin()
