import pymysql
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import DATABASE_URL


if DATABASE_URL:
    url = DATABASE_URL 
else:
    raise Exception("DATABASE_URL is not set in the environment variables.")

engine = create_engine(
    url,
    pool_pre_ping=True, pool_recycle=3600
)
local_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
base = declarative_base()
