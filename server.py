import json
import os
import uuid
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP
import mcp.types as types


DATA_FILE = "notes.json"
ALL_NOTES_RESOURCE_URI = "notes://all"
TAGS_RESOURCE_URI = "notes://tags"


def data_path() -> str:
    return os.path.join(os.path.dirname(__file__), DATA_FILE)


def load_notes() -> list[dict]:
    path = data_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_notes(notes: list[dict]) -> None:
    path = data_path()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(notes, fh, ensure_ascii=False, indent=2)


def build_note(title: str, content: str, tags: list[str] | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": content,
        "tags": tags or [],
        "completed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def find_note(notes: list[dict], note_id: str) -> dict | None:
    return next((n for n in notes if n.get("id") == note_id), None)


def _wrap_result(result: object) -> list[types.TextContent]:
    return [
        types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2),
        )
    ]


mcp = FastMCP("notes")


@mcp.tool()
def create_note(title: str, content: str, tags: list[str] | None = None) -> list[types.TextContent]:
    if not title or not content:
        raise ValueError("title and content are required")
    note = build_note(title, content, tags)
    notes = load_notes()
    notes.append(note)
    save_notes(notes)
    return _wrap_result(note)


@mcp.tool()
def list_notes(completed: bool | None = None) -> list[types.TextContent]:
    notes = load_notes()
    if completed is None:
        result = notes
    else:
        result = [n for n in notes if bool(n.get("completed", False)) is completed]
    return _wrap_result(result)


@mcp.tool()
def search_notes(query: str) -> list[types.TextContent]:
    q = (query or "").lower()
    if not q:
        return _wrap_result([])
    notes = load_notes()
    matched = [n for n in notes if q in (n.get("title", "") + " " + n.get("content", "") + " " + " ".join(n.get("tags", []))).lower()]
    return _wrap_result(matched)


@mcp.tool(name="get_notes_by_tag")
def get_notes_by_tag(tag: str) -> list[types.TextContent]:
    if not tag:
        return _wrap_result([])
    notes = load_notes()
    matched = [n for n in notes if tag in n.get("tags", [])]
    return _wrap_result(matched)


@mcp.tool()
def complete_note(note_id: str) -> list[types.TextContent]:
    if not note_id:
        raise ValueError("note_id is required")
    notes = load_notes()
    note = find_note(notes, note_id)
    if note is None:
        raise ValueError(f"Note not found: {note_id}")
    note["completed"] = True
    save_notes(notes)
    return _wrap_result({"success": True, "note": note})


@mcp.tool()
def delete_note(note_id: str) -> list[types.TextContent]:
    if not note_id:
        raise ValueError("note_id is required")
    notes = load_notes()
    note = find_note(notes, note_id)
    if note is None:
        raise ValueError(f"Note not found: {note_id}")
    notes = [n for n in notes if n.get("id") != note_id]
    save_notes(notes)
    return _wrap_result({"success": True, "deleted_id": note_id})


@mcp.resource(ALL_NOTES_RESOURCE_URI, title="All Notes", description="All notes stored in notes.json", mime_type="application/json")
def all_notes_resource() -> str:
    return json.dumps(load_notes(), ensure_ascii=False, indent=2)


@mcp.resource(TAGS_RESOURCE_URI, title="Note Tags", description="All unique tags from saved notes", mime_type="application/json")
def tags_resource() -> str:
    tags: list[str] = []
    for n in load_notes():
        for t in n.get("tags", []) or []:
            tt = str(t).strip()
            if tt and tt not in tags:
                tags.append(tt)
    return json.dumps(tags, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
