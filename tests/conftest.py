import pytest
from neo4j.exceptions import AuthError, ServiceUnavailable

from app import create_app
from app.models.db import check_connection, get_db, init_db


def make_app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "SECRET_KEY": "test",
        }
    )


@pytest.fixture(scope="session", autouse=True)
def neo4j_is_running(tmp_path_factory):
    # Stop at once with a clear message, instead of 200 failing tests, when Neo4j isn't reachable.
    app = make_app(tmp_path_factory.mktemp("check"))
    with app.app_context():
        try:
            check_connection()
        except ServiceUnavailable:
            pytest.exit("Neo4j is not running. Start it with: neo4j start", returncode=1)
        except AuthError:
            pytest.exit("Neo4j refused the login. Check NEO4J_USER and NEO4J_PASSWORD in .env", returncode=1)


@pytest.fixture
def app(tmp_path):
    # Each test starts with an empty Neo4j database and its own upload folder.
    # NOTE: this empties the local database. Run "python seed.py" after pytest to get the sample data back.
    app = make_app(tmp_path)
    with app.app_context():
        init_db()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    with app.app_context():
        yield get_db()
