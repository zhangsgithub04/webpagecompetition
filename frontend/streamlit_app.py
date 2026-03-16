import os
from typing import Any, Dict, List

import requests
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
MY_API_KEY = os.getenv("MY_API_KEY")

if not MY_API_KEY:
    raise RuntimeError("Missing MY_API_KEY")


st.set_page_config(page_title="Webpage Competition", layout="wide")
st.title("Webpage Competition Dashboard")
st.caption("Manage competition entries and upload avatar/webpage files")


def api_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}{path}"


def get_headers() -> Dict[str, str]:
    return {"X-API-Key": MY_API_KEY}


def get_entries() -> List[Dict[str, Any]]:
    response = requests.get(api_url("/entries"), headers=get_headers(), timeout=30)
    response.raise_for_status()
    return response.json()


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
        headers=get_headers(),
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
        headers=get_headers(),
        data=data,
        files=files if files else None,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def delete_entry(entry_id: str) -> None:
    response = requests.delete(api_url(f"/entries/{entry_id}"), headers=get_headers(), timeout=30)
    response.raise_for_status()


with st.sidebar:
    st.header("Settings")
    st.write(f"API Base URL: `{API_BASE_URL}`")
    st.write("API key auth: enabled")
    st.markdown(
        "**Expected backend endpoints**\n"
        "- `POST /entries/upload`\n"
        "- `PATCH /entries/{entry_id}/upload`\n"
        "- `GET /entries`\n"
        "- `DELETE /entries/{entry_id}`"
    )
    if st.button("Refresh entries"):
        st.rerun()


left_col, right_col = st.columns([1.05, 1.45])

with left_col:
    st.subheader("Create entry")
    with st.form("create_entry_form", clear_on_submit=True):
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
            "Upload webpage",
            type=["zip", "html"],
            accept_multiple_files=False,
            help="Upload a ZIP of the webpage or a single HTML file.",
        )
        submitted = st.form_submit_button("Create")

        if submitted:
            missing_fields = [
                not title.strip(),
                not author_first_name.strip(),
                not author_last_name.strip(),
                avatar_file is None,
                webpage_file is None,
            ]
            if any(missing_fields):
                st.error("Title, author names, avatar upload, and webpage upload are required.")
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
                    st.success(f"Created entry: {created['title']}")
                    st.rerun()
                except requests.RequestException as e:
                    detail = getattr(e.response, "text", str(e)) if hasattr(e, "response") else str(e)
                    st.error(f"Failed to create entry: {detail}")

with right_col:
    st.subheader("Entries")
    try:
        entries = get_entries()
    except requests.RequestException as e:
        st.error(f"Could not connect to API: {e}")
        entries = []

    if not entries:
        st.info("No entries found.")
    else:
        for entry in entries:
            full_name = f"{entry['author_first_name']} {entry['author_last_name']}"
            with st.expander(f"{entry['title']} — {full_name}"):
                st.write(f"**ID:** `{entry['id']}`")
                st.write(f"**Description:** {entry.get('description') or '-'}")
                st.write(f"**SPA file path:** `{entry.get('spa_file_path') or '-'}`")
                st.write(f"**Avatar file path:** `{entry.get('avatar_file_path') or '-'}`")
                st.write(f"**Created:** {entry['created_at']}")
                st.write(f"**Updated:** {entry['updated_at']}")

                st.markdown("### Replace details or files")
                with st.form(f"edit_form_{entry['id']}"):
                    edit_title = st.text_input("Title", value=entry["title"], key=f"title_{entry['id']}")
                    edit_description = st.text_area(
                        "Description",
                        value=entry.get("description") or "",
                        key=f"description_{entry['id']}",
                    )
                    edit_first = st.text_input(
                        "Author first name",
                        value=entry["author_first_name"],
                        key=f"first_{entry['id']}",
                    )
                    edit_last = st.text_input(
                        "Author last name",
                        value=entry["author_last_name"],
                        key=f"last_{entry['id']}",
                    )
                    edit_avatar = st.file_uploader(
                        "Replace avatar (optional)",
                        type=["png", "jpg", "jpeg", "webp"],
                        accept_multiple_files=False,
                        key=f"avatar_{entry['id']}",
                    )
                    edit_webpage = st.file_uploader(
                        "Replace webpage (optional)",
                        type=["zip", "html"],
                        accept_multiple_files=False,
                        key=f"webpage_{entry['id']}",
                    )

                    save = st.form_submit_button("Save changes")
                    if save:
                        try:
                            update_entry_with_optional_files(
                                entry_id=entry["id"],
                                title=edit_title.strip(),
                                description=edit_description.strip(),
                                author_first_name=edit_first.strip(),
                                author_last_name=edit_last.strip(),
                                avatar_file=edit_avatar,
                                webpage_file=edit_webpage,
                            )
                            st.success("Entry updated.")
                            st.rerun()
                        except requests.RequestException as e:
                            detail = getattr(e.response, "text", str(e)) if hasattr(e, "response") else str(e)
                            st.error(f"Failed to update entry: {detail}")

                if st.button("Delete entry", key=f"delete_{entry['id']}"):
                    try:
                        delete_entry(entry["id"])
                        st.success("Entry deleted.")
                        st.rerun()
                    except requests.RequestException as e:
                        detail = getattr(e.response, "text", str(e)) if hasattr(e, "response") else str(e)
                        st.error(f"Failed to delete entry: {detail}")


st.markdown("---")
st.markdown("### requirements.txt")
st.code("streamlit\nrequests", language="text")

st.markdown("### Run locally")
st.code(
    """export API_BASE_URL=http://localhost:8000
export MY_API_KEY=your-private-api-key
streamlit run webpage_competition_streamlit_upload.py""",
    language="bash",
)
