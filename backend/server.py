import os
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import Client, create_client


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MY_API_KEY = os.getenv("MY_API_KEY")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
TABLE_NAME = "webpage_competition_entries"


if not SUPABASE_URL:
    raise RuntimeError("Missing SUPABASE_URL")

if not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_KEY")

if not MY_API_KEY:
    raise RuntimeError("Missing MY_API_KEY")

if not SUPABASE_URL.startswith("https://") or "supabase.co" not in SUPABASE_URL:
    raise RuntimeError(f"Invalid SUPABASE_URL: {SUPABASE_URL}")


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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
    created_at: str
    updated_at: str


class HealthResponse(BaseModel):
    status: str


app = FastAPI(title="Webpage Competition API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    if x_api_key != MY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def ensure_single(result: Any, not_found_message: str = "Entry not found") -> Dict[str, Any]:
    data = result.data
    if not data:
        raise HTTPException(status_code=404, detail=not_found_message)
    if isinstance(data, list):
        return data[0]
    return data


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/entries", response_model=List[EntryResponse], dependencies=[Depends(verify_api_key)])
def list_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    end = skip + limit - 1
    result = (
        supabase.table(TABLE_NAME)
        .select("*")
        .order("created_at", desc=True)
        .range(skip, end)
        .execute()
    )
    return result.data or []


@app.get("/entries/{entry_id}", response_model=EntryResponse, dependencies=[Depends(verify_api_key)])
def get_entry(entry_id: UUID):
    result = (
        supabase.table(TABLE_NAME)
        .select("*")
        .eq("id", str(entry_id))
        .limit(1)
        .execute()
    )
    return ensure_single(result)


@app.post("/entries", response_model=EntryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
def create_entry(payload: EntryCreate):
    result = supabase.table(TABLE_NAME).insert(payload.model_dump()).execute()
    return ensure_single(result, "Failed to create entry")


@app.patch("/entries/{entry_id}", response_model=EntryResponse, dependencies=[Depends(verify_api_key)])
def patch_entry(entry_id: UUID, payload: EntryUpdate):
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        result = (
            supabase.table(TABLE_NAME)
            .select("*")
            .eq("id", str(entry_id))
            .limit(1)
            .execute()
        )
        return ensure_single(result)

    result = (
        supabase.table(TABLE_NAME)
        .update(update_data)
        .eq("id", str(entry_id))
        .execute()
    )
    return ensure_single(result)


@app.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_api_key)])
def delete_entry(entry_id: UUID):
    result = (
        supabase.table(TABLE_NAME)
        .delete()
        .eq("id", str(entry_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Entry not found")

    return None


# Install:
# pip install fastapi uvicorn supabase
#
# Env:
# export SUPABASE_URL="https://your-project-ref.supabase.co"
#
# Use requests with header:
# headers = {"X-API-Key": os.getenv("MY_API_KEY")}
# requests.get("http://localhost:8000/entries", headers=headers)
