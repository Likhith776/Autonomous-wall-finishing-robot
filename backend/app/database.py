from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os

# SQLite database configuration with optimizations
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wall_robot.db")

# Engine configuration with performance optimizations
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # For SQLite
    echo=False  # Set to True for SQL query debugging
)


# Enable SQLite optimizations
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable SQLite performance optimizations"""
    cursor = dbapi_conn.cursor()
    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    # Increase cache size to 64MB
    cursor.execute("PRAGMA cache_size=-64000")
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    # Set synchronous to NORMAL for better performance
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Set temp_store to MEMORY
    cursor.execute("PRAGMA temp_store=MEMORY")
    # Set mmap_size for memory-mapped I/O
    cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
    cursor.close()


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from app.models import Base
    Base.metadata.create_all(bind=engine)
