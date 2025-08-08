
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

# Configure connection pool to prevent exhaustion
engine = create_engine(
    settings.DATABASE_URL,
    # Connection pool settings to prevent the issue we just fixed
    pool_size=10,           # Base connection pool size
    max_overflow=20,        # Additional connections beyond pool_size
    pool_timeout=30,        # Timeout when getting connection from pool
    pool_recycle=3600,      # Recycle connections every hour
    pool_pre_ping=True,     # Validate connections before use
    echo=False              # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger.info(f"Database engine configured with pool_size=10, max_overflow=20, pool_timeout=30s")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
