import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    # One connection per request, kept on flask.g and reused within that request.
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row  # rows can be read by column name: row["name"]
        g.db.execute("PRAGMA foreign_keys = ON")  # SQLite skips REFERENCES checks without this
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("models/schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Delete all data and create empty tables."""
    init_db()
    click.echo("Created an empty database.")


def init_app(app):
    app.teardown_appcontext(close_db)  # close the connection when the request ends
    app.cli.add_command(init_db_command)
