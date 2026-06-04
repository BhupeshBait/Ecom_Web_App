import pymysql
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

url = "mysql+pymysql://root:@localhost:3306/ecomdb"

engine = create_engine(
    url,
    pool_pre_ping=True,pool_recycle=3600)
local_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
base = declarative_base()
