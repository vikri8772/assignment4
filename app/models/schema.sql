-- Running this file deletes all data and creates empty tables.
-- Orders and questions get their tables when those features are built.

DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS food_item_allergen;
DROP TABLE IF EXISTS food_item_diet;
DROP TABLE IF EXISTS food_item_event;
DROP TABLE IF EXISTS food_item;
DROP TABLE IF EXISTS diet;
DROP TABLE IF EXISTS event;

CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,  -- two users can't share an e-mail address
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL  -- 'CUSTOMER' or 'ADMIN'
);

CREATE TABLE event (
    name TEXT PRIMARY KEY
);

CREATE TABLE diet (
    name TEXT PRIMARY KEY
);

CREATE TABLE food_item (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT NOT NULL,  -- FoodItem.desc ("desc" is an SQL keyword)
    price        TEXT NOT NULL,  -- Decimal stored as text, e.g. '129.00'
    min_order    INTEGER NOT NULL,
    picture_path TEXT,
    published    INTEGER NOT NULL DEFAULT 0  -- 0 = false, 1 = true
);

-- A food item can belong to many events, and an event has many food items.
CREATE TABLE food_item_event (
    food_item_id TEXT NOT NULL REFERENCES food_item (id) ON DELETE CASCADE,
    event_name   TEXT NOT NULL REFERENCES event (name),
    PRIMARY KEY (food_item_id, event_name)
);

CREATE TABLE food_item_diet (
    food_item_id TEXT NOT NULL REFERENCES food_item (id) ON DELETE CASCADE,
    diet_name    TEXT NOT NULL REFERENCES diet (name),
    PRIMARY KEY (food_item_id, diet_name)
);

CREATE TABLE food_item_allergen (
    food_item_id TEXT NOT NULL REFERENCES food_item (id) ON DELETE CASCADE,
    allergen     TEXT NOT NULL,
    PRIMARY KEY (food_item_id, allergen)
);
