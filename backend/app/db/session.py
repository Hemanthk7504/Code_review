"""Database engine, connection pooling, and session management for SQLite."""
import logging
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..models import AuditLogModel, Base, ReviewRecordModel, UserModel

log = logging.getLogger(__name__)

# Locate database file in project root
DB_PATH = Path(__file__).resolve().parents[3] / "codesentinel.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a managed database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database schema and seed default enterprise accounts if empty."""
    from ..core.auth import hash_password, USERS_DB, UserInDB, UserRole


    # Create tables
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        admin = db.query(UserModel).filter_by(username="admin").first()
        if not admin:
            log.info("Seeding default accounts into SQLite database: %s", DB_PATH)
            seeds = [
                UserModel(
                    id="usr-admin001",
                    username="admin",
                    email="admin@codesentinel.internal",
                    full_name="Enterprise Administrator",
                    role="admin",
                    disabled=False,
                    hashed_password=hash_password("Admin@123"),
                ),
                UserModel(
                    id="usr-reviewer002",
                    username="reviewer",
                    email="reviewer@codesentinel.internal",
                    full_name="Staff Security Engineer",
                    role="reviewer",
                    disabled=False,
                    hashed_password=hash_password("Reviewer@123"),
                ),
                UserModel(
                    id="usr-viewer003",
                    username="viewer",
                    email="viewer@codesentinel.internal",
                    full_name="Compliance Auditor",
                    role="viewer",
                    disabled=False,
                    hashed_password=hash_password("Viewer@123"),
                ),
            ]
            db.add_all(seeds)
            db.commit()
            log.info("Database initialized successfully with default credentials.")

        # Hydrate in-memory USERS_DB from SQLite persistent storage
        all_users = db.query(UserModel).all()
        for u in all_users:
            USERS_DB[u.username] = UserInDB(
                id=u.id,
                username=u.username,
                email=u.email,
                full_name=u.full_name or "",
                role=UserRole(u.role),
                disabled=u.disabled,
                hashed_password=u.hashed_password,
                created_at=u.created_at or "",
            )


