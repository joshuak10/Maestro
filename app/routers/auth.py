from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginIn, SignupIn, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

#same message for unknown username and wrong password -> doesn't reveal which usernames exist
INVALID_LOGIN = "Invalid username or password"


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn, db: Session = Depends(get_db)) -> User:
    """Insert + commit; let uq_users_username decide duplicates.

    IntegrityError -> db.rollback() -> 409 (check e.orig.diag.constraint_name).
    Doesn't log the user in; the frontend calls /auth/login next.
    """
    user = User(
        name=body.name,
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    try:
        db.add(user)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        if e.orig.diag.constraint_name == "uq_users_username":
            raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken") from e
        raise  #anything else is a real bug -> 500

    db.refresh(user)  #loads the server-set id and created_at
    return user

@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    """Look up by username, verify_password, return a token. Any failure -> 401 INVALID_LOGIN."""
    try:
        user = db.scalar(select(User).where(User.username == body.username))
        if not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = INVALID_LOGIN,
                headers={"WWW-Authenticate": "Bearer"}
            )
    except AttributeError:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = INVALID_LOGIN,
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    return TokenOut(access_token = create_access_token(user.id))

#class LoginIn(BaseModel):
    username: Username
    password: str
#class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
