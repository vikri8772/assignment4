import os
import secrets

from dotenv import load_dotenv
from flask import Flask

# Reads .env (not committed) into the environment. See .env.example.
load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # The Neo4j server. The defaults match a local Neo4j, see README.md.
        NEO4J_URI=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        NEO4J_USER=os.environ.get("NEO4J_USER", "neo4j"),
        NEO4J_PASSWORD=os.environ.get("NEO4J_PASSWORD", ""),
        # Signs the login cookie. Set SECRET_KEY in .env; without it, a random
        # key is made at startup and everyone is logged out on every restart.
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        # Food item pictures (A2). Tests use a temporary folder instead.
        UPLOAD_FOLDER=os.path.join(app.static_folder, "uploads"),
        # Largest request Flask accepts: a 5 MB picture plus the other form fields.
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
    )
    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from app.models import db

    db.init_app(app)

    from app.controllers import account, admin, auth, shop

    app.before_request(auth.load_logged_in_user)
    app.register_blueprint(shop.bp)
    app.register_blueprint(account.bp)
    app.register_blueprint(admin.bp)

    return app
