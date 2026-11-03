from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Role, User
from app.security import decode_access_token

#auto_error=False -> a missing header gives None, so WE choose the response (401)
#also adds the Authorize button to /docs
bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """Who is calling? Missing header, bad/expired token, or deleted user -> 401.

    Load the user from the DB every time (db.get(User, user_id)), so a deleted
    user's token stops working immediately.
    """
    raise NotImplementedError("Step 9: get_current_user")


def require_role(*roles: Role) -> Callable[..., User]:
    """Dependency factory: Depends(require_role(Role.TEACHER)) -> the User, or 403."""

    def checker(user: User = Depends(get_current_user)) -> User:
        raise NotImplementedError("Step 10: require_role")

    return checker
