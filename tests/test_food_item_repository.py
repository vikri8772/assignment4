import sqlite3
from decimal import Decimal

import pytest

from app.models.food import Diet, Event, FoodItem
from app.models.food_item_repository import FoodItemRepository

WEDDING = Event("Bryllup")
CONFIRMATION = Event("Konfirmasjon")
VEGETARIAN = Diet("Vegetar")


@pytest.fixture
def repo(db):
    repo = FoodItemRepository(db)
    repo.add_event(WEDDING)
    repo.add_event(CONFIRMATION)
    repo.add_diet(VEGETARIAN)
    return repo


def make_item(**changes):
    values = dict(
        name="Fiskesuppe",
        desc="Bergensk fiskesuppe",
        price=Decimal("129.00"),
        min_order=10,
        events=[WEDDING],
        allergens=["fisk", "melk"],
    )
    values.update(changes)
    return FoodItem(**values)


def test_added_item_comes_back_the_same(repo):
    item = make_item(events=[WEDDING, CONFIRMATION], diets=[VEGETARIAN])
    repo.add(item)

    assert repo.get_by_id(item.id) == item


def test_get_by_id_returns_none_for_unknown_id(repo):
    assert repo.get_by_id("no-such-id") is None


def test_get_all_returns_every_item(repo):
    repo.add(make_item(name="Fiskesuppe"))
    repo.add(make_item(name="Bløtkake"))

    assert [item.name for item in repo.get_all()] == ["Bløtkake", "Fiskesuppe"]


def test_get_published_items_only_returns_published_items_for_the_event(repo):
    published_wedding = make_item(name="Fiskesuppe", published=True)
    unpublished_wedding = make_item(name="Bløtkake")
    published_confirmation = make_item(name="Rekesmørbrød", events=[CONFIRMATION], published=True)
    for item in (published_wedding, unpublished_wedding, published_confirmation):
        repo.add(item)

    assert repo.get_published_items(WEDDING) == [published_wedding]


def test_update_saves_new_values_and_lists(repo):
    item = make_item()
    repo.add(item)

    item.name = "Fiskesuppe med reker"
    item.price = Decimal("149.50")
    item.events = [CONFIRMATION]
    item.remove_allergen("melk")
    item.publish()
    repo.update(item)

    assert repo.get_by_id(item.id) == item


def test_delete_removes_item_and_its_links(repo, db):
    item = make_item()
    repo.add(item)

    repo.delete(item.id)

    assert repo.get_by_id(item.id) is None
    assert db.execute("SELECT * FROM food_item_event").fetchall() == []


def test_item_with_unknown_event_is_not_saved_at_all(repo):
    item = make_item(events=[Event("No such event")])

    with pytest.raises(sqlite3.IntegrityError):
        repo.add(item)

    assert repo.get_all() == []


def test_events_and_diets(repo):
    assert repo.get_events() == [WEDDING, CONFIRMATION]
    assert repo.get_diets() == [VEGETARIAN]
