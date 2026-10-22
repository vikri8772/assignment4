from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.controllers import account, admin, shop

    app.register_blueprint(shop.bp)
    app.register_blueprint(account.bp)
    app.register_blueprint(admin.bp)

    return app
