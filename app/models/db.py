import click
from flask import current_app, g
from flask.cli import with_appcontext
from neo4j import GraphDatabase
from neo4j.exceptions import ConstraintError

# Unique properties, see docs/plans/neo4j-graph-model.md.
# Neo4j has no foreign keys: the repositories check references themselves.
CONSTRAINTS = [
    ("User", "id"),
    ("User", "email"),  # two users can't share an e-mail address
    ("FoodItem", "id"),
    ("Order", "id"),
    ("Question", "id"),
    ("Event", "name"),
    ("Diet", "name"),
]


class IntegrityError(Exception):
    """A save that would break the data: a missing referenced node or a duplicate unique value."""


class Database:
    """A Neo4j session for one request. The repositories call these methods, so they never import neo4j."""

    def __init__(self, session):
        self.session = session

    def query(self, cypher, **params):
        # All result rows, as dicts: a node becomes a dict of its properties.
        try:
            return [record.data() for record in self.session.run(cypher, params)]
        except ConstraintError as error:
            raise IntegrityError(error.message) from error

    def query_one(self, cypher, **params):
        rows = self.query(cypher, **params)
        return rows[0] if rows else None

    def close(self):
        self.session.close()


# One driver per server and login, shared by all requests (and all tests). It keeps the connections open.
_drivers = {}


def _driver():
    config = current_app.config
    key = (config["NEO4J_URI"], config["NEO4J_USER"], config["NEO4J_PASSWORD"])
    if key not in _drivers:
        _drivers[key] = GraphDatabase.driver(key[0], auth=(key[1], key[2]))
    return _drivers[key]


def get_db():
    # One session per request, kept on flask.g and reused within that request.
    if "db" not in g:
        g.db = Database(_driver().session())
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Delete all nodes and relationships, and create the constraints."""
    db = get_db()
    db.query("MATCH (n) DETACH DELETE n")
    for label, prop in CONSTRAINTS:
        db.query(
            f"CREATE CONSTRAINT {label.lower()}_{prop} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
        )


def check_connection():
    # Raises neo4j.exceptions.ServiceUnavailable or AuthError if Neo4j can't be reached.
    _driver().verify_connectivity()


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Delete all data and create the constraints."""
    init_db()
    click.echo("Created an empty database.")


def init_app(app):
    app.teardown_appcontext(close_db)  # close the session when the request ends
    app.cli.add_command(init_db_command)
