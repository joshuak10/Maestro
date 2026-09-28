from enum import StrEnum
from app.db import Base
from sqlalchemy import Integer, String, DateTime, CheckConstraint, UniqueConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, UTC

class Role(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key = True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), unique = True)
    password_hash: Mapped[str] = mapped_column(String(255),)
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            f"role IN ({', '.join(f'{r.value!r}' for r in Role)})",
            name = "role"
            ,),
    )

class Scale(Base):
    __tablename__ = "scales"

    id: Mapped[int] = mapped_column(Integer,primary_key= True)
    name: Mapped[str] = mapped_column(String(100), unique = True)

class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer,primary_key= True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id",ondelete="CASCADE"), index = True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id",ondelete="CASCADE"))
    scale_id: Mapped[int] = mapped_column(ForeignKey("scales.id",ondelete="RESTRICT"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("teacher_id", "student_id", "scale_id"),
    )
    teacher: Mapped[User] = relationship(foreign_keys=[teacher_id])
    student: Mapped[User] = relationship(foreign_keys=[student_id])
    scale: Mapped[Scale] = relationship(foreign_keys=[scale_id])

"""
users                         assignments                        scales
┌────┬───────┬─────────┐      ┌────┬────────────┬────────────┬──────────┐      ┌────┬─────────┐
│ id │ name  │ role    │      │ id │ teacher_id │ student_id │ scale_id │      │ id │ name    │
├────┼───────┼─────────┤      ├────┼────────────┼────────────┼──────────┤      ├────┼─────────┤
│ 1  │ Kim   │ teacher │◄─────│ 10 │     1      │     2      │    1     │─────►│ 1  │ G Major │
│ 2  │ Alex  │ student │◄─────│ 11 │     1      │     2      │    2     │─────►│ 2  │ D Major │
│ 3  │ Sam   │ student │      │ 12 │     1      │     3      │    1     │      │ 3  │ A Major │
└────┴───────┴─────────┘      └────┴────────────┴────────────┴──────────┘      └────┴─────────┘
"""
