from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.db import SessionLocal
from app.models import Scale

#the one place scales are defined; the seed only adds, it never deletes
SCALES = ("G Major", "D Major", "A Major", "E Major")


def seed_scales(db: Session) -> int:
    rows = [{"name": scale} for scale in SCALES]
    stmt = (
        insert(Scale)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["name"])
        .returning(Scale.id)
    )
    inserted = len(db.execute(stmt).all())  #ORM inserts report rowcount as -1, so count RETURNING rows
    db.commit()
    return inserted


#runs only via `python -m app.seed`, not when imported (e.g. by tests)
if __name__ == "__main__":
    with SessionLocal() as db:
        inserted = seed_scales(db)
    print(f"seeded {inserted} new scale(s)")
