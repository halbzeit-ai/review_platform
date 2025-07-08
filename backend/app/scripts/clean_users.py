
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Get the database URL from environment or use default SQLite
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./backend/sql_app.db')
engine = create_engine(DATABASE_URL)

from backend.app.db.models import Base, User

def clean_users():
    # Drop all users
    User.__table__.drop(engine)
    # Recreate the users table
    Base.metadata.create_all(engine)
    print("Users table has been cleaned.")

if __name__ == "__main__":
    clean_users()
