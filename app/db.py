from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.config import settings

#create_engine does not connect; the pool opens a connection on the first query
#pre_ping checks a pooled connection before reuse (managed DBs drop idle ones)
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    #every model subclasses this; Base.metadata is what alembic diffs against
    pass


#FastAPI dependency: one session per request, closed even if the endpoint raises
def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
