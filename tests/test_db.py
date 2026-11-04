import pytest

from app.models.db import CONSTRAINTS, IntegrityError


def test_constraints_are_created(db):
    rows = db.query("SHOW CONSTRAINTS YIELD labelsOrTypes, properties")
    created = {(row["labelsOrTypes"][0], row["properties"][0]) for row in rows}

    assert set(CONSTRAINTS) <= created


def test_duplicate_unique_value_is_refused(db):
    db.query("CREATE (:Event {name: 'Wedding'})")

    with pytest.raises(IntegrityError):
        db.query("CREATE (:Event {name: 'Wedding'})")


def test_init_db_deletes_everything(app, db):
    db.query("CREATE (:Event {name: 'Wedding'})")

    with app.app_context():
        from app.models.db import init_db

        init_db()

    assert db.query("MATCH (n) RETURN n") == []


def test_init_db_command(app):
    result = app.test_cli_runner().invoke(args=["init-db"])

    assert "Created an empty database." in result.output
