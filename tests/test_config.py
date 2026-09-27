import pytest
from pydantic import ValidationError
from app.config import Settings

SECRET = "x" * 32


def make(**overrides):
    #kwargs take priority over env vars and .env, so these tests ignore local config
    values = {"database_url": "postgresql+psycopg://u:p@h:5432/d", "jwt_secret": SECRET}
    return Settings(**(values | overrides))


@pytest.mark.parametrize("url", [
    "postgres://u:p@h:5432/d",
    "postgresql://u:p@h:5432/d",
    "postgresql+psycopg://u:p@h:5432/d",
])
def test_db_url_is_normalized_to_psycopg(url):
    assert make(database_url=url).database_url == "postgresql+psycopg://u:p@h:5432/d"


def test_db_url_keeps_special_char_password():
    #@ and / in the password must survive the parse/render round trip
    url = "postgres://u:p%40ss%2Fword@h:5432/d"
    assert make(database_url=url).database_url == "postgresql+psycopg://u:p%40ss%2Fword@h:5432/d"


@pytest.mark.parametrize("url", ["not a url", "postgresql+psycopg2://u:p@h/d", "sqlite:///x.db"])
def test_bad_db_url_is_rejected(url):
    with pytest.raises(ValidationError, match="database_url"):
        make(database_url=url)


def test_short_secret_is_rejected():
    with pytest.raises(ValidationError, match="jwt_secret"):
        make(jwt_secret="change_me")


def test_secret_is_masked():
    s = make()
    assert SECRET not in repr(s)
    assert s.jwt_secret.get_secret_value() == SECRET


def test_missing_config_fails(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError) as e:
        Settings(_env_file=None)
    assert {err["loc"][0] for err in e.value.errors()} == {"database_url", "jwt_secret"}
