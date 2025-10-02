from app.models import db
from app.models.user import Role


def register_user(client, email="student@example.com", password="pass12345", first="Stu", last="Dent", role="Student"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first,
            "last_name": last,
            "role": role,
        },
    )


def login_user(client, email="student@example.com", password="pass12345"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_register_and_login_and_me(client):
    # register
    r = register_user(client)
    assert r.status_code == 201

    # login
    r = login_user(client)
    assert r.status_code == 200
    tokens = r.get_json()
    access = tokens.get("access_token")
    assert access

    # me
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["user"]["email"] == "student@example.com"
