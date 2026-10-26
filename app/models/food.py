from dataclasses import dataclass, field
from decimal import Decimal
from uuid import uuid4

# Largest quantity a customer can order of one item (C2).
MAX_QUANTITY = 10_000

# The 14 allergens that must be labelled on food in the EU/EEA.
# The admin chooses from this list (A1), so every item uses the same words.
ALLERGENS = [
    "gluten",
    "crustaceans",
    "egg",
    "fish",
    "peanuts",
    "soybeans",
    "milk",
    "nuts",
    "celery",
    "mustard",
    "sesame",
    "sulphites",
    "lupin",
    "molluscs",
]


@dataclass(frozen=True)
class Event:
    name: str


@dataclass(frozen=True)
class Diet:
    name: str


@dataclass
class FoodItem:
    name: str
    desc: str
    price: Decimal
    min_order: int
    events: list[Event] = field(default_factory=list)
    diets: list[Diet] = field(default_factory=list)
    allergens: list[str] = field(default_factory=list)
    picture_path: str | None = None
    published: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)

    def accepts_quantity(self, qty: int) -> bool:
        return self.min_order <= qty <= MAX_QUANTITY

    def add_allergen(self, allergen: str):
        if allergen not in self.allergens:
            self.allergens.append(allergen)

    def remove_allergen(self, allergen: str):
        if allergen in self.allergens:
            self.allergens.remove(allergen)

    def publish(self):
        self.published = True

    def unpublish(self):
        self.published = False
