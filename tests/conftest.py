import pytest

from app import create_app
from app.models.db import get_db, init_db


@pytest.fixture
def app(tmp_path):
    # Each test gets its own empty database and upload folder in a temporary folder.
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.db"),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "SECRET_KEY": "test",
        }
    )
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
