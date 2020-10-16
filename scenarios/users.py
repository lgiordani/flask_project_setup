from application.app import create_app
from application.models import db, User


app = create_app("development")


def run():
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Administrator
        admin = User(email="admin@server.com")
        db.session.add(admin)

        # First user
        user1 = User(email="user1@server.com")
        db.session.add(user1)

        # Second user
        user2 = User(email="user2@server.com")
        db.session.add(user2)

        db.session.commit()
