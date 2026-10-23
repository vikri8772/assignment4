from functools import wraps

from flask import abort, g, redirect, request, session, url_for

from app.models.db import get_db
from app.models.user_repository import UserRepository


def load_logged_in_user():
    # Runs before every request: g.user is the logged-in User, or None.
    user_id = session.get("user_id")
    g.user = UserRepository(get_db()).get_by_id(user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("account.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("account.login", next=request.path))
        if not g.user.is_admin():
            abort(403)
        return view(*args, **kwargs)

    return wrapped
