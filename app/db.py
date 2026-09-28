from collections.abc import Iterator
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.config import settings

#predictable constraint names (e.g. uq_users_email) so alembic and error handling can refer to them
#check constraints must be given a name= for the "ck" pattern to work
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

#create_engine does not connect; the pool opens a connection on the first query
#pre_ping checks a pooled connection before reuse (managed DBs drop idle ones)
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    #every model subclasses this; Base.metadata is what alembic diffs against
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


#FastAPI dependency: one session per request, closed even if the endpoint raises
def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
