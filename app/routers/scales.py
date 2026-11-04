from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_user
from app.models import Scale, User
from app.schemas import ScaleOut

router = APIRouter(prefix="/scales", tags=["scales"])


@router.get("", response_model=list[ScaleOut])
def list_scales(
    _user: User = Depends(get_current_user),  #any logged-in role
    db: Session = Depends(get_db),
) -> list[Scale]:
    """Every scale, ordered by id."""
    return db.scalars(select(Scale).order_by(Scale.id)).all()

