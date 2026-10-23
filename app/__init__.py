import os
import secrets

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "ektemat.db"),
        # Signs the login cookie. Set SECRET_KEY in .env; without it, a random
        # key is made at startup and everyone is logged out on every restart.
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    )
    if test_config is not None:
        app.config.update(test_config)

    # The instance/ folder holds the database file. It is in .gitignore.
    os.makedirs(app.instance_path, exist_ok=True)

    from app.models import db

    db.init_app(app)

    from app.controllers import account, admin, auth, shop

    app.before_request(auth.load_logged_in_user)
    app.register_blueprint(shop.bp)
    app.register_blueprint(account.bp)
    app.register_blueprint(admin.bp)

    return app
