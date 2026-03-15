from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres",
)


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class WebpageCompetitionEntry(Base):
    __tablename__ = "webpage_competition_entries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    spa_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_first_name: Mapped[str] = mapped_column(String, nullable=False)
    author_last_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class EntryBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    spa_file_path: str = Field(..., min_length=1)
    avatar_file_path: Optional[str] = None
    author_first_name: str = Field(..., min_length=1, max_length=100)
    author_last_name: str = Field(..., min_length=1, max_length=100)


class EntryCreate(EntryBase):
    pass


class EntryUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    spa_file_path: Optional[str] = Field(None, min_length=1)
    avatar_file_path: Optional[str] = None
    author_first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    author_last_name: Optional[str] = Field(None, min_length=1, max_length=100)


class EntryResponse(EntryBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


app = FastAPI(title="Webpage Competition API")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Webpage Competition API is running"}


@app.get("/entries", response_model=List[EntryResponse])
def list_entries(db: Session = Depends(get_db)):
    return db.query(WebpageCompetitionEntry).order_by(WebpageCompetitionEntry.created_at.desc()).all()


@app.get("/entries/{entry_id}", response_model=EntryResponse)
def get_entry(entry_id: UUID, db: Session = Depends(get_db)):
    entry = db.get(WebpageCompetitionEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return entry


@app.post("/entries", response_model=EntryResponse, status_code=status.HTTP_201_CREATED)
def create_entry(payload: EntryCreate, db: Session = Depends(get_db)):
    entry = WebpageCompetitionEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.put("/entries/{entry_id}", response_model=EntryResponse)
def update_entry(entry_id: UUID, payload: EntryUpdate, db: Session = Depends(get_db)):
    entry = db.get(WebpageCompetitionEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    db.commit()
    db.refresh(entry)
    return entry


@app.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: UUID, db: Session = Depends(get_db)):
    entry = db.get(WebpageCompetitionEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    db.delete(entry)
    db.commit()
    return None


# Optional: only use this if you want SQLAlchemy to create the table.
# If you already created the table in Supabase SQL, you can leave this disabled.
# Base.metadata.create_all(bind=engine)


# Run locally with:
# uvicorn webpage_competition_fastapi:app --reload
#
# Recommended dependencies:
# pip install fastapi uvicorn sqlalchemy psycopg2-binary
#
# Example .env / environment variable:
# DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/postgres
