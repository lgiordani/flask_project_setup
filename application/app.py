from flask import Flask
from application.models import User


def create_app(config_name):

    app = Flask(__name__)

    config_module = f"application.config.{config_name.capitalize()}Config"

    app.config.from_object(config_module)

    from application.models import db, migrate

    db.init_app(app)
    migrate.init_app(app, db)

    @app.route("/")
    def hello_world():
        return "Hello, World!"

    @app.route("/users")
    def users():
        num_users = User.query.count()
        return f"Number of users: {num_users}"

    return app
