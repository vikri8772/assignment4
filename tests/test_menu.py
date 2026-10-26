import re
from decimal import Decimal

import pytest

from app.models.food import Diet, Event, FoodItem
from app.models.food_item_repository import FoodItemRepository

WEDDING = Event("Wedding")
JULEBORD = Event("Julebord")
BIRTHDAY = Event("Birthday")
VEGAN = Diet("Vegan")


@pytest.fixture
def food(db):
    repo = FoodItemRepository(db)
    for event in [WEDDING, JULEBORD, BIRTHDAY]:
        repo.add_event(event)
    repo.add_diet(VEGAN)
    repo.add(
        FoodItem(
            name="Fiskesuppe",
            desc="Fish soup.",
            price=Decimal("129.00"),
            min_order=10,
            events=[WEDDING],
            allergens=["fish", "milk"],
            published=True,
        )
    )
    repo.add(
        FoodItem(
            name="Ribbe",
            desc="Pork belly.",
            price=Decimal("329.00"),
            min_order=15,
            events=[JULEBORD],
            diets=[VEGAN],
            published=True,
        )
    )
    repo.add(
        FoodItem(
            name="Hjortegryte",
            desc="Not on the menu yet.",
            price=Decimal("289.00"),
            min_order=10,
            events=[WEDDING],
            published=False,
        )
    )
    return repo


def section(page, event_name):
    # The HTML of one event's section on the menu page, or None if it isn't there.
    match = re.search(rf'<section id="event-{event_name.lower()}".*?</section>', page, re.S)
    return match.group(0) if match else None


def test_menu_shows_published_items_under_their_events(client, food):
    page = client.get("/").get_data(as_text=True)

    assert "Fiskesuppe" in section(page, "Wedding")
    assert "Ribbe" in section(page, "Julebord")
    assert "Ribbe" not in section(page, "Wedding")


def test_menu_hides_unpublished_items(client, food):
    page = client.get("/").get_data(as_text=True)

    assert "Hjortegryte" not in page


def test_menu_skips_events_without_items(client, food):
    page = client.get("/").get_data(as_text=True)

    assert section(page, "Birthday") is None


def test_card_shows_price_min_order_allergens_and_diets(client, food):
    page = client.get("/").get_data(as_text=True)
    wedding = section(page, "Wedding")
    julebord = section(page, "Julebord")

    assert "129.00 NOK" in wedding
    assert "Minimum order: 10" in wedding
    assert "Allergens: fish, milk" in wedding
    assert "Allergens: none" in julebord
    assert "Vegan" in julebord


def test_card_without_picture_shows_placeholder(client, food):
    page = client.get("/").get_data(as_text=True)

    assert "No picture yet" in page


def test_empty_menu_shows_message(client, db):
    page = client.get("/").get_data(as_text=True)

    assert "The menu is empty" in page
