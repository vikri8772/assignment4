from app.models.user import Role, User
from app.models.user_repository import UserRepository


def make_user(**changes):
    values = dict(name="Kari Nordmann", email="kari@example.test", password_hash="hash")
    values.update(changes)
    return User(**values)


def test_new_user_is_a_customer():
    user = make_user()

    assert user.role == Role.CUSTOMER
    assert not user.is_admin()


def test_admin_is_admin():
    assert make_user(role=Role.ADMIN).is_admin()


def test_added_user_comes_back_the_same(db):
    repo = UserRepository(db)
    user = make_user(role=Role.ADMIN)
    repo.add(user)

    assert repo.get_by_id(user.id) == user
    assert repo.get_by_email("kari@example.test") == user


def test_unknown_user_is_none(db):
    repo = UserRepository(db)

    assert repo.get_by_id("no-such-id") is None
    assert repo.get_by_email("nobody@example.test") is None
