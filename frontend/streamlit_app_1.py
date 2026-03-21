import os
from typing import Any, Dict, List

import requests
import streamlit as st
import streamlit.components.v1 as components


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
MY_API_KEY = os.getenv("MY_API_KEY")

if not MY_API_KEY:
    raise RuntimeError("Missing MY_API_KEY")


st.set_page_config(page_title="Webpage Competition", layout="wide")
st.title("Webpage Competition Dashboard")
st.caption("Create, edit, and preview entries with avatar and HTML page")


def api_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}{path}"


def headers() -> Dict[str, str]:
    return {"X-API-Key": MY_API_KEY}


def get_entries() -> List[Dict[str, Any]]:
    response = requests.get(api_url("/entries"), headers=headers(), timeout=30)
    response.raise_for_status()
    return response.json()


def get_avatar_image_url(path: str) -> str:
    return f"{api_url('/files/avatar-image')}?path={path}"


def get_spa_html(path: str) -> str:
    response = requests.get(
        api_url("/files/spa-html"),
        headers=headers(),
        params={"path": path},
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def create_entry_with_files(
    title: str,
    description: str,
    author_first_name: str,
    author_last_name: str,
    avatar_file,
    webpage_file,
) -> Dict[str, Any]:
    data = {
        "title": title,
        "description": description,
        "author_first_name": author_first_name,
        "author_last_name": author_last_name,
    }
    files = {
        "avatar": (
            avatar_file.name,
            avatar_file.getvalue(),
            avatar_file.type or "application/octet-stream",
        ),
        "webpage": (
            webpage_file.name,
            webpage_file.getvalue(),
            webpage_file.type or "application/octet-stream",
        ),
    }

    response = requests.post(
        api_url("/entries/upload"),
        headers=headers(),
        data=data,
        files=files,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def update_entry_with_optional_files(
    entry_id: str,
    title: str,
    description: str,
    author_first_name: str,
    author_last_name: str,
    avatar_file,
    webpage_file,
) -> Dict[str, Any]:
    data = {
        "title": title,
        "description": description,
        "author_first_name": author_first_name,
        "author_last_name": author_last_name,
    }

    files = {}
    if avatar_file is not None:
        files["avatar"] = (
            avatar_file.name,
            avatar_file.getvalue(),
            avatar_file.type or "application/octet-stream",
        )
    if webpage_file is not None:
        files["webpage"] = (
            webpage_file.name,
            webpage_file.getvalue(),
            webpage_file.type or "application/octet-stream",
        )

    response = requests.patch(
        api_url(f"/entries/{entry_id}/upload"),
        headers=headers(),
        data=data,
        files=files if files else None,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def delete_entry(entry_id: str) -> None:
    response = requests.delete(
        api_url(f"/entries/{entry_id}"),
        headers=headers(),
        timeout=30,
    )
    response.raise_for_status()


with st.sidebar:
    st.header("Settings")
    st.write(f"API Base URL: `{API_BASE_URL}`")
    st.write("API key auth: enabled")
    if st.button("Refresh"):
        st.rerun()


left_col, right_col = st.columns([1.0, 1.5])

with left_col:
    st.subheader("Create entry")
    with st.form("create_form", clear_on_submit=True):
        title = st.text_input("Title")
        description = st.text_area("Description")
        author_first_name = st.text_input("Author first name")
        author_last_name = st.text_input("Author last name")
        avatar_file = st.file_uploader(
            "Upload avatar",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=False,
        )
        webpage_file = st.file_uploader(
            "Upload HTML page",
            type=["html"],
            accept_multiple_files=False,
        )
        submitted = st.form_submit_button("Create entry")

        if submitted:
            if (
                not title.strip()
                or not author_first_name.strip()
                or not author_last_name.strip()
                or avatar_file is None
                or webpage_file is None
            ):
                st.error("Title, author names, avatar, and HTML page are required.")
            else:
                try:
                    created = create_entry_with_files(
                        title=title.strip(),
                        description=description.strip(),
                        author_first_name=author_first_name.strip(),
                        author_last_name=author_last_name.strip(),
                        avatar_file=avatar_file,
                        webpage_file=webpage_file,
                    )
                    st.success(f"Created: {created['title']}")
                    st.rerun()
                except requests.RequestException as e:
                    detail = e.response.text if getattr(e, "response", None) is not None else str(e)
                    st.error(f"Failed to create entry: {detail}")


with right_col:
    st.subheader("Entries")

    try:
        entries = get_entries()
    except requests.RequestException as e:
        detail = e.response.text if getattr(e, "response", None) is not None else str(e)
        st.error(f"Could not connect to API: {detail}")
        entries = []

    if not entries:
        st.info("No entries found.")
    else:
        for entry in entries:
            full_name = f"{entry['author_first_name']} {entry['author_last_name']}"

            with st.expander(f"{entry['title']} — {full_name}", expanded=False):
                st.write(f"**ID:** `{entry['id']}`")
                st.write(f"**Description:** {entry.get('description') or '-'}")
                st.write(f"**Created:** {entry['created_at']}")
                st.write(f"**Updated:** {entry['updated_at']}")

                avatar_url = None
                spa_html = None

                try:
                    if entry.get("avatar_file_path"):
                        avatar_url = get_avatar_image_url(entry["avatar_file_path"])
                    if entry.get("spa_file_path"):
                        spa_html = get_spa_html(entry["spa_file_path"])
                except requests.RequestException as e:
                    detail = e.response.text if getattr(e, "response", None) is not None else str(e)
                    st.warning(f"Could not load file preview: {detail}")

                preview_col, meta_col = st.columns([1, 2])

                with preview_col:
                    if avatar_url:
                        st.image(avatar_url, width=160, caption="Avatar")
                    else:
                        st.write("No avatar preview available.")

                with meta_col:
                    st.write(f"**SPA path:** `{entry.get('spa_file_path') or '-'}`")
                    st.write(f"**Avatar path:** `{entry.get('avatar_file_path') or '-'}`")

                if spa_html:
                    st.markdown("### HTML Preview")
                    components.html(spa_html, height=700, scrolling=True)
                else:
                    st.info("No webpage preview available.")
