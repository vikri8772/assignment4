from decimal import Decimal

from app.models.food import MAX_QUANTITY, Event, FoodItem


def make_item(**changes):
    values = dict(name="Fiskesuppe", desc="Bergensk fiskesuppe", price=Decimal("129.00"), min_order=10)
    values.update(changes)
    return FoodItem(**values)


def test_new_item_is_unpublished_and_has_an_id():
    item = make_item()

    assert item.published is False
    assert item.id


def test_two_items_get_different_ids():
    assert make_item().id != make_item().id


def test_accepts_quantity_between_min_order_and_max():
    item = make_item(min_order=10)

    assert item.accepts_quantity(10)
    assert item.accepts_quantity(MAX_QUANTITY)


def test_rejects_quantity_below_min_order_or_above_max():
    item = make_item(min_order=10)

    assert not item.accepts_quantity(9)
    assert not item.accepts_quantity(MAX_QUANTITY + 1)


def test_publish_and_unpublish():
    item = make_item()

    item.publish()
    assert item.published is True

    item.unpublish()
    assert item.published is False


def test_allergen_is_only_added_once_and_can_be_removed():
    item = make_item()

    item.add_allergen("fisk")
    item.add_allergen("fisk")
    assert item.allergens == ["fisk"]

    item.remove_allergen("fisk")
    assert item.allergens == []


def test_events_with_the_same_name_are_equal():
    assert Event("Bryllup") == Event("Bryllup")
