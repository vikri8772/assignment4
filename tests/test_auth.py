import pytest
from werkzeug.security import generate_password_hash

from app.models.user import Role, User
from app.models.user_repository import UserRepository

PASSWORD = "testpassord"


@pytest.fixture
def users(db):
    repo = UserRepository(db)
    repo.add(User(name="Kunde", email="kunde@example.test", password_hash=generate_password_hash(PASSWORD)))
    repo.add(
        User(
            name="Admin",
            email="admin@example.test",
            password_hash=generate_password_hash(PASSWORD),
            role=Role.ADMIN,
        )
    )
    return repo


def log_in(client, email, password=PASSWORD, next=None):
    url = "/account/login" + (f"?next={next}" if next else "")
    return client.post(url, data={"email": email, "password": password})


def test_register_creates_customer_and_logs_in(client, db):
    response = client.post(
        "/account/register",
        data={"name": "Ola", "email": "Ola@Example.test", "password": "langtpassord"},
    )

    assert response.status_code == 302
    user = UserRepository(db).get_by_email("ola@example.test")  # stored in lower case
    assert user is not None and not user.is_admin()
    assert "Logged in as Ola" in client.get("/").get_data(as_text=True)


def test_register_rejects_used_email_and_short_password(client, users):
    response = client.post(
        "/account/register",
        data={"name": "Kunde 2", "email": "kunde@example.test", "password": "kort"},
    )
    page = response.get_data(as_text=True)

    assert response.status_code == 400
    assert "already exists" in page
    assert "at least 8 characters" in page


def test_login_and_logout(client, users):
    response = log_in(client, "kunde@example.test")
    assert response.status_code == 302
    assert "Logged in as Kunde" in client.get("/").get_data(as_text=True)

    client.post("/account/logout")
    assert "Log in" in client.get("/").get_data(as_text=True)


def test_wrong_password_is_rejected(client, users):
    response = log_in(client, "kunde@example.test", password="feil")

    assert response.status_code == 400
    assert "Wrong e-mail or password." in response.get_data(as_text=True)


def test_login_keeps_the_rest_of_the_session(client, users):
    # The cart lives in the session and must survive logging in (C3).
    with client.session_transaction() as session:
        session["cart"] = {"some-item": 10}

    log_in(client, "kunde@example.test")

    with client.session_transaction() as session:
        assert session["cart"] == {"some-item": 10}


def test_login_goes_back_to_next_page_but_never_to_other_sites(client, users):
    assert log_in(client, "kunde@example.test", next="/admin/").headers["Location"] == "/admin/"
    client.post("/account/logout")
    assert log_in(client, "kunde@example.test", next="//evil.example").headers["Location"] == "/"


def test_admin_page_needs_login(client):
    response = client.get("/admin/")

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/account/login")


def test_customer_cannot_open_admin_page(client, users):
    log_in(client, "kunde@example.test")

    assert client.get("/admin/").status_code == 403


def test_admin_can_open_admin_page(client, users):
    log_in(client, "admin@example.test")

    assert client.get("/admin/").status_code == 200
