from __future__ import annotations

import calendar
import json
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd


PEOPLE = ["吕佳意", "何倩青", "陈明萍", "黄凌", "叶锦圣"]
SHIFT_OPTIONS = ["空白", "中班", "晚班", "休息", "班/休"]
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

DATA_DIR = Path(__file__).resolve().parent / "data"
LEAVES_PATH = DATA_DIR / "leaves.json"
SCHEDULES_PATH = DATA_DIR / "schedules.json"

FIXED_TEMPLATE = {
    0: {"何倩青": "中班", "黄凌": "晚班"},
    1: {"陈明萍": "中班", "吕佳意": "晚班"},
    2: {"黄凌": "中班", "何倩青": "晚班"},
    3: {"叶锦圣": "中班", "陈明萍": "晚班"},
}


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LEAVES_PATH.exists():
        LEAVES_PATH.write_text("[]", encoding="utf-8")
    if not SCHEDULES_PATH.exists():
        SCHEDULES_PATH.write_text("{}", encoding="utf-8")


def read_json(path: Path, fallback):
    ensure_data_files()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return fallback


def write_json(path: Path, data) -> None:
    ensure_data_files()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_leaves() -> list[dict[str, str]]:
    leaves = read_json(LEAVES_PATH, [])
    return [
        {"person": item["person"], "date": item["date"]}
        for item in leaves
        if item.get("person") in PEOPLE and item.get("date")
    ]


def save_leaves(leaves: list[dict[str, str]]) -> None:
    cleaned = sorted(
        {
            (item["person"], item["date"])
            for item in leaves
            if item.get("person") in PEOPLE and item.get("date")
        },
        key=lambda item: (item[1], PEOPLE.index(item[0])),
    )
    write_json(LEAVES_PATH, [{"person": person, "date": day} for person, day in cleaned])


def month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def load_schedule(year: int, month: int) -> pd.DataFrame | None:
    schedules = read_json(SCHEDULES_PATH, {})
    records = schedules.get(month_key(year, month))
    if not records:
        return None
    return pd.DataFrame(records)


def save_schedule(year: int, month: int, schedule_df: pd.DataFrame) -> None:
    schedules = read_json(SCHEDULES_PATH, {})
    schedules[month_key(year, month)] = schedule_df.fillna("").to_dict("records")
    write_json(SCHEDULES_PATH, schedules)


def get_month_days(year: int, month: int) -> list[dict[str, str | int]]:
    _, last_day = calendar.monthrange(year, month)
    days = []
    for day in range(1, last_day + 1):
        current = date(year, month, day)
        days.append(
            {
                "date": current.isoformat(),
                "day": day,
                "weekday_index": current.weekday(),
                "weekday": WEEKDAY_NAMES[current.weekday()],
                "label": f"{month}/{day}",
            }
        )
    return days


def leaves_for_month(year: int, month: int) -> set[tuple[str, str]]:
    prefix = month_key(year, month)
    return {
        (item["person"], item["date"])
        for item in load_leaves()
        if item["date"].startswith(prefix)
    }


def is_on_leave(person: str, day: str, leave_set: set[tuple[str, str]]) -> bool:
    return (person, day) in leave_set


def choose_substitute(
    shift_name: str,
    day: str,
    leave_set: set[tuple[str, str]],
    shift_counts: dict[str, Counter],
    assigned_people: set[str],
) -> str | None:
    candidates = [
        person
        for person in PEOPLE
        if person not in assigned_people and not is_on_leave(person, day, leave_set)
    ]
    if not candidates:
        return None
    counter = shift_counts[shift_name]
    return min(candidates, key=lambda person: (counter[person], PEOPLE.index(person)))


def generate_schedule(year: int, month: int) -> pd.DataFrame:
    days = get_month_days(year, month)
    leave_set = leaves_for_month(year, month)
    shift_counts = {
        "中班": Counter(),
        "晚班": Counter(),
        "班/休": Counter(),
    }
    rows = []

    for index, person in enumerate(PEOPLE, start=1):
        row = {"序号": index, "姓名": person}
        for item in days:
            row[item["date"]] = ""
        rows.append(row)

    by_person = {row["姓名"]: row for row in rows}

    for item in days:
        day = item["date"]
        weekday_index = int(item["weekday_index"])

        for person in PEOPLE:
            if is_on_leave(person, day, leave_set):
                by_person[person][day] = "休息"

        if weekday_index <= 3:
            assigned_people: set[str] = set()
            template = FIXED_TEMPLATE[weekday_index]
            for fixed_person, shift_name in template.items():
                if not is_on_leave(fixed_person, day, leave_set):
                    selected = fixed_person
                else:
                    selected = choose_substitute(
                        shift_name,
                        day,
                        leave_set,
                        shift_counts,
                        assigned_people,
                    )
                if selected:
                    by_person[selected][day] = shift_name
                    assigned_people.add(selected)
                    shift_counts[shift_name][selected] += 1

        elif weekday_index == 4:
            assigned_people = set()
            middle = choose_substitute("中班", day, leave_set, shift_counts, assigned_people)
            if middle:
                by_person[middle][day] = "中班"
                assigned_people.add(middle)
                shift_counts["中班"][middle] += 1

            night = choose_substitute("晚班", day, leave_set, shift_counts, assigned_people)
            if night:
                by_person[night][day] = "晚班"
                assigned_people.add(night)
                shift_counts["晚班"][night] += 1

        else:
            selected = choose_substitute("班/休", day, leave_set, shift_counts, set())
            for person in PEOPLE:
                if not is_on_leave(person, day, leave_set):
                    by_person[person][day] = "休息"
            if selected:
                by_person[selected][day] = "班/休"
                shift_counts["班/休"][selected] += 1

    return pd.DataFrame(rows)


def normalize_schedule_df(schedule_df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    days = get_month_days(year, month)
    expected_columns = ["序号", "姓名"] + [item["date"] for item in days]
    normalized = schedule_df.copy()
    for column in expected_columns:
        if column not in normalized.columns:
            normalized[column] = ""
    normalized = normalized[expected_columns].fillna("")
    return normalized


def schedule_to_display(schedule_df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    days = get_month_days(year, month)
    display = normalize_schedule_df(schedule_df, year, month)
    rename_map = {
        item["date"]: f"{item['label']}\n{item['weekday']}"
        for item in days
    }
    display = display.rename(columns=rename_map)
    for column in display.columns:
        if column not in ["序号", "姓名"]:
            display[column] = display[column].replace({"": "空白"})
    return display


def display_to_schedule(display_df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    days = get_month_days(year, month)
    rename_map = {
        f"{item['label']}\n{item['weekday']}": item["date"]
        for item in days
    }
    schedule = display_df.rename(columns=rename_map)
    for item in days:
        schedule[item["date"]] = schedule[item["date"]].replace({"空白": ""}).fillna("")
    return normalize_schedule_df(schedule, year, month)


def calculate_stats(schedule_df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    days = get_month_days(year, month)
    date_columns = [item["date"] for item in days]
    weekend_columns = [
        item["date"]
        for item in days
        if int(item["weekday_index"]) >= 5
    ]
    records = []

    for _, row in normalize_schedule_df(schedule_df, year, month).iterrows():
        records.append(
            {
                "姓名": row["姓名"],
                "中班次数": sum(row[column] == "中班" for column in date_columns),
                "晚班次数": sum(row[column] == "晚班" for column in date_columns),
                "周末班次数": sum(row[column] == "班/休" for column in weekend_columns),
                "休息次数": sum(row[column] == "休息" for column in date_columns),
            }
        )
    return pd.DataFrame(records)
