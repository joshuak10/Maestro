from pathlib import Path
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

#repo root, so .env is found no matter which directory a command runs from
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

DB_DRIVER = "postgresql+psycopg"
MIN_SECRET_LEN = 32


class Settings(BaseSettings):
    #real env vars (CI, Render) take priority over .env
    database_url: str
    jwt_secret: SecretStr

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        try:
            url = make_url(v)
        except ArgumentError:
            raise ValueError("DATABASE_URL is not a valid database URL")

        #Render/Heroku hand out postgres:// or postgresql:// -> force the psycopg 3 driver
        if url.drivername in ("postgres", "postgresql"):
            url = url.set(drivername=DB_DRIVER)
        if url.drivername != DB_DRIVER:
            raise ValueError(f"DATABASE_URL must use {DB_DRIVER}, got {url.drivername}")

        #str(url) would mask the password as ***
        return url.render_as_string(hide_password=False)

    @field_validator("jwt_secret")
    @classmethod
    def check_secret_len(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < MIN_SECRET_LEN:
            raise ValueError(f"JWT_SECRET must be at least {MIN_SECRET_LEN} characters")
        return v


#created at import so missing/invalid config fails fast at startup (no DB connection is made)
settings = Settings()
