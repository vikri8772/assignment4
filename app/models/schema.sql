-- Running this file deletes all data and creates empty tables.

-- Questions first, because they point to orders and users.
DROP TABLE IF EXISTS question;
-- Then the order tables, because they point to users, event and food_item.
DROP TABLE IF EXISTS guest_group;
DROP TABLE IF EXISTS order_line;
DROP TABLE IF EXISTS orders;
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

-- "order" is an SQL keyword, so the table is called orders.
CREATE TABLE orders (
    id               TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users (id),
    event_name       TEXT NOT NULL REFERENCES event (name),
    event_date       TEXT NOT NULL,  -- ISO date, e.g. '2027-05-15'
    number_of_guests INTEGER NOT NULL,
    delivery_address TEXT NOT NULL,
    created_at       TEXT NOT NULL,  -- ISO date and time, e.g. '2026-10-25T14:30:00'
    order_status     TEXT NOT NULL,  -- an OrderStatus, e.g. 'SUBMITTED'
    payment_status   TEXT NOT NULL   -- a PaymentStatus, e.g. 'NOT_PAID'
);

CREATE TABLE order_line (
    order_id     TEXT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    position     INTEGER NOT NULL,  -- keeps the lines in the order they were added
    -- No ON DELETE CASCADE: a food item that is in an order can't be deleted.
    food_item_id TEXT NOT NULL REFERENCES food_item (id),
    item_name    TEXT NOT NULL,
    quantity     INTEGER NOT NULL,
    unit_price   TEXT NOT NULL,  -- Decimal stored as text
    PRIMARY KEY (order_id, position)
);

-- Allergies and diets are stored per guest group, not per named guest (GDPR).
CREATE TABLE guest_group (
    order_id         TEXT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    position         INTEGER NOT NULL,
    group_name       TEXT NOT NULL,
    number_of_guests INTEGER NOT NULL,
    allergy_notes    TEXT NOT NULL DEFAULT '',
    dietary_notes    TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (order_id, position)
);

-- A question has at most one answer, so the answer is stored in the same row.
-- The three answer columns are NULL while the question is open.
CREATE TABLE question (
    id          TEXT PRIMARY KEY,
    order_id    TEXT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    asked_by    TEXT NOT NULL REFERENCES users (id),
    text        TEXT NOT NULL,
    asked_at    TEXT NOT NULL,  -- ISO date and time
    status      TEXT NOT NULL,  -- a QuestionStatus, 'OPEN' or 'ANSWERED'
    answer_text TEXT,
    answered_by TEXT REFERENCES users (id),
    answered_at TEXT            -- ISO date and time
);
