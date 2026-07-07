from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Define the connection string (matches docker-compose.yml)
# Format: postgresql://<user>:<password>@<host>:<port>/<db_name>
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/guardian_pricing"

# Create the SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for our models to inherit from
Base = declarative_base()

# Dependency to get the DB session for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
