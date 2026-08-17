from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./devsnapshot.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    github_username = Column(String, unique=True, index=True)
    access_token = Column(String)
    last_synced = Column(DateTime, nullable=True)
    theme = Column(String, default="minimal")


class Repo(Base):
    __tablename__ = "repos"
    id = Column(Integer, primary_key=True, index=True)
    owner_username = Column(String, index=True)
    name = Column(String)
    description = Column(String, nullable=True)
    language = Column(String, nullable=True)
    stars = Column(Integer, default=0)
    included = Column(Boolean, default=True)


Base.metadata.create_all(bind=engine)