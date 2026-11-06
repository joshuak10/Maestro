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
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise unauthorized

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized

    return user


def require_role(*roles: Role) -> Callable[..., User]:
    """Dependency factory: Depends(require_role(Role.TEACHER)) -> the User, or 403."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail = "Not allowed",
            )
        
        return user

    return checker
