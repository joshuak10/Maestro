from datetime import datetime
from typing import Annotated
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints
from app.models import Role

MAX_PASSWORD_BYTES = 72  #bcrypt 5 raises on longer input -> must be a 422, not a 500
 

def _normalize_username(v: object) -> object:
    """Runs BEFORE the length/pattern checks: strip + lowercase so `Alex ` == `alex`.

    Return non-str values unchanged and let pydantic reject them.
    """
    if isinstance(v, str):
        v = v.strip().lower()    
    return v


def _password_fits_bcrypt(v: str) -> str:
    """Raise ValueError if the UTF-8 encoding is longer than MAX_PASSWORD_BYTES ("é" is 2 bytes)."""
    v_encode = v.encode('utf-8')
    if len(v_encode) > MAX_PASSWORD_BYTES:
        raise ValueError('Password too long')
    return v


def _no_nul(v: str) -> str:
    """Postgres text can't store a NUL byte; reject it here (422) so the insert can't fail (500)."""
    if "\x00" in v:
        raise ValueError("Must not contain NUL characters")
    return v


#defined once; signup, login and assignments all reuse it so they normalize the same way
Username = Annotated[
    str,
    BeforeValidator(_normalize_username),
    Field(min_length=3, max_length=30, pattern=r"^[a-z0-9_]+$"),
]
Password = Annotated[str, Field(min_length=8), AfterValidator(_password_fits_bcrypt)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100), AfterValidator(_no_nul)]


# --- auth ---

class SignupIn(BaseModel):
    name: Name
    username: Username
    password: Password
    role: Role


class LoginIn(BaseModel):
    username: Username
    password: Annotated[str, AfterValidator(_password_fits_bcrypt)]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    #response_model=UserOut drops every other attribute, so password_hash can't leak
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str
    role: Role
    created_at: datetime


# --- scales / assignments ---

class ScaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class AssignmentCreate(BaseModel):
    #teacher_id comes from the token; sending it (or anything else extra) is a 422
    model_config = ConfigDict(extra="forbid")

    student_username: Username
    scale_ids: list[int] = Field(min_length=1)


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    scale_id: int
    created_at: datetime


class StudentAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scale: ScaleOut
    teacher: TeacherOut
    created_at: datetime
