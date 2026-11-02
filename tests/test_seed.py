import os

from seed import DIETS, FOOD_ITEMS, ORDERS, QUESTIONS, USERS, seed

from app.models.food import ALLERGENS
from app.models.food_item_repository import FoodItemRepository
from app.models.order_repository import OrderRepository
from app.models.question_repository import QuestionRepository
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


def test_seed_creates_orders_for_the_customers(app, db):
    with app.app_context():
        seed()

    users = UserRepository(db)
    orders = OrderRepository(db)
    assert len(orders.find()) == len(ORDERS)
    kari = users.get_by_email("kari@example.test")
    assert len(orders.get_by_user(kari.id)) == 3


def test_seed_creates_questions_on_the_customers_orders(app, db):
    with app.app_context():
        seed()

    questions = QuestionRepository(db).get_all()
    assert len(questions) == len(QUESTIONS)
    assert len([q for q in questions if q.is_answered()]) == 1

    # Every question is on an order that belongs to the customer who asked it.
    orders = OrderRepository(db)
    for question in questions:
        assert orders.get_by_id(question.order_id).belongs_to(question.asked_by)


def test_seed_allergens_are_on_the_allergen_list():
    for item in FOOD_ITEMS:
        assert set(item.allergens) <= set(ALLERGENS), item.name


def test_seed_pictures_exist(app):
    # The seed pictures are committed, so the menu has photos right after "python seed.py".
    for item in FOOD_ITEMS:
        assert item.picture_path, item.name
        assert os.path.isfile(os.path.join(app.static_folder, item.picture_path)), item.picture_path
