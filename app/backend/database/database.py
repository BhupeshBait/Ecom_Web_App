from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import pymysql

url= "sqlite:///./Ecom.db"

engine=create_engine(url,connect_args={"check_same_thread":False},pool_pre_ping=True)
local_session=sessionmaker(autocommit=False,autoflush=False,bind=engine)
base=declarative_base()