from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Create DB engine
connect_args = {}
if settings.sqlalchemy_database_uri.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
    # Keep a small warm pool of connections alive so requests reuse an already
    # authenticated TCP+SSL session instead of paying the ~3s handshake to the
    # remote pooler on every cold request. Recycle before typical idle timeouts.
    pool_size=5,
    max_overflow=5,
    pool_recycle=1800,
    connect_args=connect_args,
)

# Apply performance-boosting SQLite pragmas on connection
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.sqlalchemy_database_uri.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA cache_size=-64000;")  # 64MB cache size
            cursor.execute("PRAGMA temp_store=MEMORY;")
        except Exception:
            pass
        finally:
            cursor.close()

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base
Base = declarative_base()

# Dependency to get db session in endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
