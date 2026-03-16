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
st.caption("Manage competition entries from your FastAPI backend")


def api_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}{path}"


def get_headers() -> Dict[str, str]:
    return {"X-API-Key": MY_API_KEY}


def get_entries() -> List[Dict[str, Any]]:
    response = requests.get(api_url("/entries"), headers=get_headers(), timeout=15)
    response.raise_for_status()
    return response.json()


def create_entry(payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(api_url("/entries"), json=payload, headers=get_headers(), timeout=15)
    response.raise_for_status()
    return response.json()


def update_entry(entry_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.patch(api_url(f"/entries/{entry_id}"), json=payload, headers=get_headers(), timeout=15)
    response.raise_for_status()
    return response.json()


def delete_entry(entry_id: str) -> None:
    response = requests.delete(api_url(f"/entries/{entry_id}"), headers=get_headers(), timeout=15)
    response.raise_for_status()


with st.sidebar:
    st.header("Settings")
    st.write(f"API Base URL: `{API_BASE_URL}`")
    st.write("API key auth: enabled")
    if st.button("Refresh entries"):
        st.rerun()


left_col, right_col = st.columns([1.05, 1.45])

with left_col:
    st.subheader("Create entry")
    with st.form("create_entry_form", clear_on_submit=True):
        title = st.text_input("Title")
        description = st.text_area("Description")
        spa_file_path = st.text_input("SPA file path")
        avatar_file_path = st.text_input("Avatar file path")
        author_first_name = st.text_input("Author first name")
        author_last_name = st.text_input("Author last name")
        submitted = st.form_submit_button("Create")

        if submitted:
            if not title.strip() or not spa_file_path.strip() or not author_first_name.strip() or not author_last_name.strip():
                st.error("Title, SPA file path, author first name, and author last name are required.")
            else:
                payload = {
                    "title": title.strip(),
                    "description": description.strip() or None,
                    "spa_file_path": spa_file_path.strip(),
                    "avatar_file_path": avatar_file_path.strip() or None,
                    "author_first_name": author_first_name.strip(),
                    "author_last_name": author_last_name.strip(),
                }
                try:
                    created = create_entry(payload)
                    st.success(f"Created entry: {created['title']}")
                    st.rerun()
                except requests.RequestException as e:
                    st.error(f"Failed to create entry: {e}")

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
            with st.expander(f"{entry['title']} — {full_name}", expanded=False):
                st.write(f"**ID:** `{entry['id']}`")
                st.write(f"**Description:** {entry.get('description') or '-'}")
                st.write(f"**SPA file:** `{entry['spa_file_path']}`")
                st.write(f"**Avatar:** `{entry.get('avatar_file_path') or '-'}"
                )
                st.write(f"**Created:** {entry['created_at']}")
                st.write(f"**Updated:** {entry['updated_at']}")

                st.markdown("### Edit entry")
                with st.form(f"edit_form_{entry['id']}"):
                    edit_title = st.text_input("Title", value=entry["title"], key=f"title_{entry['id']}")
                    edit_description = st.text_area(
                        "Description",
                        value=entry.get("description") or "",
                        key=f"description_{entry['id']}",
                    )
                    edit_spa = st.text_input(
                        "SPA file path",
                        value=entry["spa_file_path"],
                        key=f"spa_{entry['id']}",
                    )
                    edit_avatar = st.text_input(
                        "Avatar file path",
                        value=entry.get("avatar_file_path") or "",
                        key=f"avatar_{entry['id']}",
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

                    save = st.form_submit_button("Save changes")
                    if save:
                        payload = {
                            "title": edit_title.strip(),
                            "description": edit_description.strip() or None,
                            "spa_file_path": edit_spa.strip(),
                            "avatar_file_path": edit_avatar.strip() or None,
                            "author_first_name": edit_first.strip(),
                            "author_last_name": edit_last.strip(),
                        }
                        try:
                            update_entry(entry["id"], payload)
                            st.success("Entry updated.")
                            st.rerun()
                        except requests.RequestException as e:
                            st.error(f"Failed to update entry: {e}")

                if st.button("Delete entry", key=f"delete_{entry['id']}"):
                    try:
                        delete_entry(entry["id"])
                        st.success("Entry deleted.")
                        st.rerun()
                    except requests.RequestException as e:
                        st.error(f"Failed to delete entry: {e}")


st.markdown("---")
st.markdown("### Run locally")
st.code(
    """pip install streamlit requests
export API_BASE_URL=http://localhost:8000
export MY_API_KEY=your-private-api-key
streamlit run webpage_competition_streamlit.py""",
    language="bash",
)
