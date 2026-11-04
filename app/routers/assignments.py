from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload
from app.db import get_db
from app.deps import require_role
from app.models import Assignment, Role, Scale, User
from app.schemas import AssignmentCreate, AssignmentOut, StudentAssignmentOut

router = APIRouter(prefix="/assignments", tags=["assignments"])

UNIQUE_ASSIGNMENT = "uq_assignments_teacher_id_student_id_scale_id"


@router.post("", response_model=list[AssignmentOut], status_code=status.HTTP_201_CREATED)
def create_assignments(
    body: AssignmentCreate,
    teacher: User = Depends(require_role(Role.TEACHER)),
    db: Session = Depends(get_db),
) -> list[Assignment]:
    """Assign scales to one student. Idempotent: already-assigned scales are skipped.

    1. student = user with body.student_username AND role student, else
       400 "No student with that username" (same message if it's a teacher).
    2. dedupe body.scale_ids keeping order (dict.fromkeys); any id not in scales
       -> 400 f"Unknown scale ids: {missing}".
    3. insert(Assignment).values(rows)
         .on_conflict_do_nothing(constraint=UNIQUE_ASSIGNMENT)
         .returning(Assignment)
       -> db.scalars(stmt).all(); commit ONCE; return those rows (may be []).
    """
    student = db.scalar(select(User).where(User.username == body.student_username).where(User.role == Role.STUDENT))
    if not student:
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail="No student with that username"
        )

    ids = list(dict.fromkeys(body.scale_ids))
    
    existing = set(db.scalars(select(Scale.id).where(Scale.id.in_(ids))))
    missing = [scale_id for scale_id in ids if scale_id not in existing]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scale ids: {missing}",
        )

    rows = [
        {"teacher_id": teacher.id, "student_id": student.id, "scale_id": scale_id}
        for scale_id in ids
    ]
    stmt = (
        insert(Assignment)
        .values(rows)
        .on_conflict_do_nothing(constraint=UNIQUE_ASSIGNMENT)
        .returning(Assignment)
    )
    created = db.scalars(stmt).all()
    db.commit()
    return created


#keep /me above any future /{assignment_id} route, or "me" would be parsed as an id
@router.get("/me", response_model=list[StudentAssignmentOut])
def my_assignments(
    student: User = Depends(require_role(Role.STUDENT)),
    db: Session = Depends(get_db),
) -> list[Assignment]:
    """This student's assignments, newest first (created_at desc, id desc).

    selectinload(Assignment.scale) and selectinload(Assignment.teacher) -> no N+1.
    """
    raise NotImplementedError("Step 12: GET /assignments/me")
