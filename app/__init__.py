import os

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "ektemat.db"),
    )
    if test_config is not None:
        app.config.update(test_config)

    # The instance/ folder holds the database file. It is in .gitignore.
    os.makedirs(app.instance_path, exist_ok=True)

    from app.models import db

    db.init_app(app)

    from app.controllers import account, admin, shop

    app.register_blueprint(shop.bp)
    app.register_blueprint(account.bp)
    app.register_blueprint(admin.bp)

    return app
