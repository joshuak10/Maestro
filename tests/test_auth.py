from conftest import auth_headers, signup


def test_signup_returns_user_without_password(api):
    r = api.post(
        "/auth/signup",
        json={"name": "Alex", "username": "alex", "password": "password123", "role": "student"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "alex"
    assert body["role"] == "student"
    assert "password" not in body
    assert "password_hash" not in body


def test_signup_stores_a_bcrypt_hash(api):
    from sqlalchemy import select
    from app.db import SessionLocal
    from app.models import User

    user = signup(api, "student", password="password123")
    with SessionLocal() as db:
        stored = db.scalar(select(User.password_hash).where(User.id == user["id"]))
    assert stored.startswith("$2b$")
    assert "password123" not in stored


def test_duplicate_username_ignores_case(api):
    signup(api, "student", username="Alex")
    r = api.post(
        "/auth/signup",
        json={"name": "Other", "username": "alex", "password": "password123", "role": "student"},
    )
    assert r.status_code == 409


def test_signup_rejects_unknown_role(api):
    r = api.post(
        "/auth/signup",
        json={"name": "Alex", "username": "alex", "password": "password123", "role": "admin"},
    )
    assert r.status_code == 422


def test_login_token_works_on_me(api):
    user = signup(api, "teacher")
    r = api.get("/auth/me", headers=auth_headers(api, user["username"]))
    assert r.status_code == 200
    assert r.json()["id"] == user["id"]
    assert "password_hash" not in r.json()


def test_wrong_password_and_unknown_user_look_the_same(api):
    user = signup(api, "student")
    wrong_password = api.post("/auth/login", json={"username": user["username"], "password": "wrong-password"})
    unknown_user = api.post("/auth/login", json={"username": "nobody_here", "password": "password123"})
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json()["detail"] == unknown_user.json()["detail"]


def test_me_requires_a_valid_token(api):
    missing = api.get("/auth/me")
    garbage = api.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert missing.status_code == 401
    assert garbage.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
