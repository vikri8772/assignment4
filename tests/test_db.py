import sqlite3

import pytest


def test_tables_are_created(db):
    rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    tables = {row["name"] for row in rows}

    assert {"event", "diet", "food_item", "food_item_event"} <= tables


def test_foreign_keys_are_checked(db):
    # Linking a food item to an event that does not exist must fail.
    db.execute(
        "INSERT INTO food_item (id, name, description, price, min_order) VALUES ('1', 'Suppe', '', '100.00', 10)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO food_item_event (food_item_id, event_name) VALUES ('1', 'No such event')")


def test_init_db_command(app):
    result = app.test_cli_runner().invoke(args=["init-db"])

    assert "Created an empty database." in result.output
