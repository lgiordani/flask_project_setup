from application.models import User


def test__create_user(database):
    email = "some.email@server.com"
    user = User(email=email)
    database.session.add(user)
    database.session.commit()

    user = User.query.first()

    assert user.email == email
