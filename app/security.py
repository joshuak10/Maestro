import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings

ALGORITHM = "HS256"
TOKEN_MINUTES = 60


def hash_password(password: str) -> str:
    """bcrypt hash as a 60-char str (salt + cost are stored inside it).

    bcrypt works on bytes: .encode() going in, .decode() the result to store it.
    """
    password_bytes = password.encode('utf-8')
    seed = bcrypt.gensalt(rounds = 12)
    hashed_pword = bcrypt.hashpw(password_bytes, seed)
    return hashed_pword.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """True if `password` matches the stored bcrypt hash."""
    password_bytes = password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    """Signed JWT with sub=str(user_id) and exp = now(UTC) + TOKEN_MINUTES.

    Secret: settings.jwt_secret.get_secret_value()
    """
    token = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    }

    #jwt.encode(package, encrypter, algorithm)
    return jwt.encode(token, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """The user id from a valid token, or None if invalid/expired.

    Pin algorithms=[ALGORITHM]; every failure is a jwt.InvalidTokenError subclass.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms = [ALGORITHM])
        return int(payload["sub"])
    except jwt.InvalidTokenError:
        return None

    raise NotImplementedError("Step 7: decode_access_token")
