from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"
LEAVES_PATH = DATA_DIR / "leaves.json"
SCHEDULES_PATH = DATA_DIR / "schedules.json"


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LEAVES_PATH.exists():
        LEAVES_PATH.write_text("[]", encoding="utf-8")
    if not SCHEDULES_PATH.exists():
        SCHEDULES_PATH.write_text("{}", encoding="utf-8")


def read_local_json(path: Path, fallback):
    ensure_data_files()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return fallback


def write_local_json(path: Path, data) -> None:
    ensure_data_files()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_secret(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        supabase_config = st.secrets.get("supabase", {})
        return supabase_config.get(name.lower().replace("supabase_", ""))
    except Exception:
        return None


def get_supabase_client():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_KEY")
    if not url or not key:
        return None

    try:
        from supabase import create_client
    except ImportError:
        return None

    return create_client(url, key)


def using_cloud_database() -> bool:
    return get_supabase_client() is not None


def load_leaves_data() -> list[dict[str, str]]:
    client = get_supabase_client()
    if client:
        response = client.table("leaves").select("person,date").order("date").execute()
        return response.data or []
    return read_local_json(LEAVES_PATH, [])


def save_leaves_data(leaves: list[dict[str, str]]) -> None:
    client = get_supabase_client()
    if client:
        client.table("leaves").delete().neq("person", "__never_delete_marker__").execute()
        if leaves:
            client.table("leaves").insert(leaves).execute()
        return
    write_local_json(LEAVES_PATH, leaves)


def load_schedules_data() -> dict[str, Any]:
    client = get_supabase_client()
    if client:
        response = client.table("schedules").select("month_key,records").execute()
        return {
            item["month_key"]: item.get("records", [])
            for item in response.data or []
            if item.get("month_key")
        }
    return read_local_json(SCHEDULES_PATH, {})


def save_schedules_data(schedules: dict[str, Any]) -> None:
    client = get_supabase_client()
    if client:
        rows = [
            {"month_key": key, "records": records}
            for key, records in schedules.items()
        ]
        if rows:
            client.table("schedules").upsert(rows, on_conflict="month_key").execute()
        return
    write_local_json(SCHEDULES_PATH, schedules)
