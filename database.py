from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "postgresql://localhost/local_api_db"  # update if needed

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,            # default is 5
    max_overflow=50,         # default is 10
    pool_timeout=60,         # increase timeout in seconds
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
