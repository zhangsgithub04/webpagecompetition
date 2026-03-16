import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import Client, create_client


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MY_API_KEY = os.getenv("MY_API_KEY")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

TABLE_NAME = "webpage_competition_entries"
SPA_BUCKET = "competition-spa"
AVATAR_BUCKET = "competition-avatars"

if not SUPABASE_URL:
    raise RuntimeError("Missing SUPABASE_URL")

if not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_KEY")

if not MY_API_KEY:
    raise RuntimeError("Missing MY_API_KEY")

if not SUPABASE_URL.startswith("https://") or "supabase.co" not in SUPABASE_URL:
    raise RuntimeError(f"Invalid SUPABASE_URL: {SUPABASE_URL}")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Webpage Competition API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EntryResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    spa_file_path: str
    avatar_file_path: Optional[str] = None
    author_first_name: str
    author_last_name: str
    created_at: str
    updated_at: str


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    if x_api_key != MY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def ensure_single(result: Any, message: str = "Entry not found") -> Dict[str, Any]:
    data = result.data
    if not data:
        raise HTTPException(status_code=404, detail=message)
    if isinstance(data, list):
        return data[0]
    return data


def upload_to_bucket(bucket_name: str, uploaded_file: UploadFile, folder: str) -> str:
    try:
        ext = ""
        if uploaded_file.filename and "." in uploaded_file.filename:
            ext = "." + uploaded_file.filename.split(".")[-1].lower()

        file_path = f"{folder}/{uuid.uuid4()}{ext}"
        file_bytes = uploaded_file.file.read()

        supabase.storage.from_(bucket_name).upload(
            path=file_path,
            file=file_bytes,
            file_options={
                "content-type": uploaded_file.content_type or "application/octet-stream"
            },
        )
        return file_path
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload to bucket '{bucket_name}' failed: {str(e)}",
        )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/files/avatar-url", dependencies=[Depends(verify_api_key)])
def get_avatar_url(path: str = Query(...)) -> Dict[str, str]:
    try:
        result = supabase.storage.from_(AVATAR_BUCKET).create_signed_url(path, 3600)
        signed_url = result.get("signedURL") or result.get("signed_url")
        if not signed_url:
            raise HTTPException(status_code=400, detail="Could not create avatar URL")
        return {"url": signed_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Avatar URL failed: {str(e)}")


@app.get("/files/spa-url", dependencies=[Depends(verify_api_key)])
def get_spa_url(path: str = Query(...)) -> Dict[str, str]:
    try:
        result = supabase.storage.from_(SPA_BUCKET).create_signed_url(path, 3600)
        signed_url = result.get("signedURL") or result.get("signed_url")
        if not signed_url:
            raise HTTPException(status_code=400, detail="Could not create SPA URL")
        return {"url": signed_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SPA URL failed: {str(e)}")

@app.get("/entries", response_model=List[EntryResponse], dependencies=[Depends(verify_api_key)])
def list_entries() -> List[Dict[str, Any]]:
    try:
        result = (
            supabase.table(TABLE_NAME)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List entries failed: {str(e)}")


@app.get("/entries/{entry_id}", response_model=EntryResponse, dependencies=[Depends(verify_api_key)])
def get_entry(entry_id: str) -> Dict[str, Any]:
    try:
        result = (
            supabase.table(TABLE_NAME)
            .select("*")
            .eq("id", entry_id)
            .limit(1)
            .execute()
        )
        return ensure_single(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get entry failed: {str(e)}")


@app.post(
    "/entries/upload",
    response_model=EntryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_api_key)],
)
def create_entry_upload(
    title: str = Form(...),
    description: str = Form(""),
    author_first_name: str = Form(...),
    author_last_name: str = Form(...),
    avatar: UploadFile = File(...),
    webpage: UploadFile = File(...),
) -> Dict[str, Any]:
    try:
        avatar_path = upload_to_bucket(AVATAR_BUCKET, avatar, "avatars")
        webpage_path = upload_to_bucket(SPA_BUCKET, webpage, "webpages")

        payload = {
            "title": title.strip(),
            "description": description.strip() or None,
            "spa_file_path": webpage_path,
            "avatar_file_path": avatar_path,
            "author_first_name": author_first_name.strip(),
            "author_last_name": author_last_name.strip(),
        }

        result = supabase.table(TABLE_NAME).insert(payload).execute()
        return ensure_single(result, "Failed to create entry")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create entry failed: {str(e)}")


@app.patch(
    "/entries/{entry_id}/upload",
    response_model=EntryResponse,
    dependencies=[Depends(verify_api_key)],
)
def update_entry_upload(
    entry_id: str,
    title: str = Form(...),
    description: str = Form(""),
    author_first_name: str = Form(...),
    author_last_name: str = Form(...),
    avatar: UploadFile | None = File(None),
    webpage: UploadFile | None = File(None),
) -> Dict[str, Any]:
    try:
        existing = (
            supabase.table(TABLE_NAME)
            .select("*")
            .eq("id", entry_id)
            .limit(1)
            .execute()
        )
        _ = ensure_single(existing)

        update_data = {
            "title": title.strip(),
            "description": description.strip() or None,
            "author_first_name": author_first_name.strip(),
            "author_last_name": author_last_name.strip(),
        }

        if avatar is not None:
            update_data["avatar_file_path"] = upload_to_bucket(AVATAR_BUCKET, avatar, "avatars")

        if webpage is not None:
            update_data["spa_file_path"] = upload_to_bucket(SPA_BUCKET, webpage, "webpages")

        result = (
            supabase.table(TABLE_NAME)
            .update(update_data)
            .eq("id", entry_id)
            .execute()
        )
        return ensure_single(result, "Failed to update entry")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update entry failed: {str(e)}")


@app.delete(
    "/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_api_key)],
)
def delete_entry(entry_id: str):
    try:
        result = (
            supabase.table(TABLE_NAME)
            .delete()
            .eq("id", entry_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Entry not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete entry failed: {str(e)}")
