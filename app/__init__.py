from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    # Temporary route to check that the app runs.
    # It moves into the shop blueprint in step 2.
    @app.route("/")
    def home():
        return render_template("base.html", company="Ekte Mat")

    return app
