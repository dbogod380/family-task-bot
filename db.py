import os
from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Date, text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///family_tasks.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False, default="User")
    timezone = Column(String, nullable=False, default="UTC")
    language = Column(String, nullable=False, default="en")
    streak = Column(Integer, nullable=False, default=0)
    last_completed = Column(Date, nullable=True)
    digest_sent_date = Column(String, nullable=True)  # "YYYY-MM-DD" in user's local tz


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=True)
    chat_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=True)       # UTC naive
    is_done = Column(Boolean, nullable=False, default=False)
    is_recurring = Column(Boolean, nullable=False, default=False)
    recur_interval = Column(String, nullable=True)   # "daily" | "weekly" | "monthly"
    reminder_sent = Column(Boolean, nullable=False, default=False)
    pending_review = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("chat_id", "user_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    role = Column(String, nullable=False, default="member")  # admin | member | kid


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    added_by = Column(Integer, ForeignKey("users.telegram_id"), nullable=False)
    is_checked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def migrate_db():
    """Add new columns to existing tables without losing data."""
    with engine.connect() as conn:
        for sql in [
            "ALTER TABLE users ADD COLUMN language VARCHAR DEFAULT 'en'",
            "ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_completed DATE",
            "ALTER TABLE users ADD COLUMN digest_sent_date VARCHAR",
            "ALTER TABLE tasks ADD COLUMN pending_review INTEGER DEFAULT 0",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # Column already exists


def init_db():
    Base.metadata.create_all(engine)
    migrate_db()


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
