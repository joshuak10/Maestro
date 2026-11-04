import os
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]

#app.config and app.db read DATABASE_URL when imported, so point it at the test
#database BEFORE anything imports app. Otherwise the tests would wipe the dev database.
test_url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(ROOT / ".env").get("TEST_DATABASE_URL")
if not test_url:
    pytest.exit("TEST_DATABASE_URL is not set")
test_db_name = make_url(test_url).database
if not test_db_name or not test_db_name.endswith("_test"):
    pytest.exit(f"refusing to run tests against database {test_db_name!r}: name must end in _test")
os.environ["DATABASE_URL"] = test_url

SR = 16000


def tone(freq, seconds=0.5, amp=0.5):
    t = np.arange(int(SR * seconds), dtype=np.float32) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


@pytest.fixture
def a4():
    return tone(440.0)


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def migrated_db():
    from alembic import command
    from alembic.config import Config
    from app.db import SessionLocal
    from app.seed import seed_scales

    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    with SessionLocal() as db:
        seed_scales(db)


@pytest.fixture
def api(migrated_db, client):
    from sqlalchemy import text
    from app.db import engine

    yield client
    #endpoints really commit, so clean up with TRUNCATE. scales isn't listed, so the seed survives.
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, assignments RESTART IDENTITY CASCADE"))


def signup(api, role, username=None, password="password123", name="Test"):
    username = username or f"u{uuid4().hex[:8]}"
    r = api.post(
        "/auth/signup",
        json={"name": name, "username": username, "password": password, "role": role},
    )
    assert r.status_code == 201, r.text
    return r.json()


def auth_headers(api, username, password="password123"):
    r = api.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def scale_ids(api, headers):
    """{scale name: id}, so tests don't hard-code ids."""
    return {s["name"]: s["id"] for s in api.get("/scales", headers=headers).json()}
