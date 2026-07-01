from __future__ import annotations

import calendar
from collections import Counter
from datetime import date

import pandas as pd

from storage import load_leaves_data, load_schedules_data, save_leaves_data, save_schedules_data


PEOPLE = ["吕佳意", "何青青", "陈明萍", "黄凌", "叶锦圣"]
NAME_ALIASES = {"何倩青": "何青青"}
SHIFT_OPTIONS = ["空白", "中班", "晚班", "休息", "班/休"]
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

FIXED_TEMPLATE = {
    0: {"何青青": "中班", "黄凌": "晚班"},
    1: {"陈明萍": "中班", "吕佳意": "晚班"},
    2: {"黄凌": "中班", "何青青": "晚班"},
    3: {"叶锦圣": "中班", "陈明萍": "晚班"},
}


def normalize_person_name(person: str) -> str:
    return NAME_ALIASES.get(person, person)


def load_leaves() -> list[dict[str, str]]:
    leaves = load_leaves_data()
    return [
        {"person": normalize_person_name(item["person"]), "date": item["date"]}
        for item in leaves
        if normalize_person_name(item.get("person", "")) in PEOPLE and item.get("date")
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
    save_leaves_data([{"person": person, "date": day} for person, day in cleaned])


def month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def load_schedule(year: int, month: int) -> pd.DataFrame | None:
    schedules = load_schedules_data()
    records = schedules.get(month_key(year, month))
    if not records:
        return None
    return ensure_weekend_coverage(normalize_schedule_names(pd.DataFrame(records)), year, month)


def list_saved_month_keys() -> list[str]:
    schedules = load_schedules_data()
    valid_keys = [
        key
        for key, records in schedules.items()
        if parse_month_key(key) and isinstance(records, list) and records
    ]
    return sorted(valid_keys, reverse=True)


def save_schedule(year: int, month: int, schedule_df: pd.DataFrame) -> None:
    schedules = load_schedules_data()
    schedule_df = normalize_schedule_names(schedule_df)
    schedule_df = ensure_weekend_coverage(schedule_df, year, month)
    schedules[month_key(year, month)] = schedule_df.fillna("").to_dict("records")
    save_schedules_data(schedules)


def parse_month_key(key: str) -> tuple[int, int] | None:
    try:
        year_text, month_text = key.split("-", 1)
        year = int(year_text)
        month = int(month_text)
    except ValueError:
        return None
    if 1 <= month <= 12:
        return year, month
    return None


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


def build_history_counts(year: int, month: int) -> tuple[dict[str, Counter], dict[str, Counter], int]:
    schedules = load_schedules_data()
    shift_counts = {
        "中班": Counter(),
        "晚班": Counter(),
        "班/休": Counter(),
    }
    friday_shift_counts = {
        "中班": Counter(),
        "晚班": Counter(),
    }
    friday_count = 0

    for key, records in schedules.items():
        parsed = parse_month_key(key)
        if not parsed or parsed >= (year, month) or not isinstance(records, list):
            continue

        history_year, history_month = parsed
        history_days = get_month_days(history_year, history_month)
        date_columns = {item["date"]: item for item in history_days}

        for record in records:
            person = normalize_person_name(record.get("姓名", ""))
            if person not in PEOPLE:
                continue
            for day, item in date_columns.items():
                shift = record.get(day, "")
                if shift in shift_counts:
                    shift_counts[shift][person] += 1
                if item["weekday"] == "周五" and shift in friday_shift_counts:
                    friday_shift_counts[shift][person] += 1

        friday_count += sum(1 for item in history_days if item["weekday"] == "周五")

    return shift_counts, friday_shift_counts, friday_count


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


def choose_rotating_person(
    people_order: list[str],
    day: str,
    leave_set: set[tuple[str, str]],
    counter: Counter,
    assigned_people: set[str],
) -> str | None:
    candidates = [
        person
        for person in people_order
        if person not in assigned_people and not is_on_leave(person, day, leave_set)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda person: (counter[person], people_order.index(person)))


def generate_schedule(year: int, month: int) -> pd.DataFrame:
    days = get_month_days(year, month)
    leave_set = leaves_for_month(year, month)
    shift_counts, friday_shift_counts, friday_index = build_history_counts(year, month)
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
            middle_order = PEOPLE[friday_index % len(PEOPLE):] + PEOPLE[:friday_index % len(PEOPLE)]
            night_order = PEOPLE[(friday_index + 1) % len(PEOPLE):] + PEOPLE[:(friday_index + 1) % len(PEOPLE)]

            middle = choose_rotating_person(
                middle_order,
                day,
                leave_set,
                friday_shift_counts["中班"],
                assigned_people,
            )
            if middle:
                by_person[middle][day] = "中班"
                assigned_people.add(middle)
                shift_counts["中班"][middle] += 1
                friday_shift_counts["中班"][middle] += 1

            night = choose_rotating_person(
                night_order,
                day,
                leave_set,
                friday_shift_counts["晚班"],
                assigned_people,
            )
            if night:
                by_person[night][day] = "晚班"
                assigned_people.add(night)
                shift_counts["晚班"][night] += 1
                friday_shift_counts["晚班"][night] += 1
            friday_index += 1

        else:
            selected = choose_substitute("班/休", day, leave_set, shift_counts, set())
            if selected:
                by_person[selected][day] = "班/休"
                shift_counts["班/休"][selected] += 1

    return ensure_weekend_coverage(pd.DataFrame(rows), year, month)


def ensure_weekend_coverage(schedule_df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    normalized = normalize_schedule_df(schedule_df, year, month)
    leave_set = leaves_for_month(year, month)
    weekend_counts = Counter()
    days = get_month_days(year, month)

    for _, row in normalized.iterrows():
        person = row["姓名"]
        for item in days:
            if item["weekday"] in ["周六", "周日"] and row[item["date"]] == "班/休":
                weekend_counts[person] += 1

    for item in days:
        if item["weekday"] not in ["周六", "周日"]:
            continue

        day = item["date"]
        has_weekend_shift = (normalized[day] == "班/休").any()
        if has_weekend_shift:
            continue

        candidates = [
            person
            for person in PEOPLE
            if not is_on_leave(person, day, leave_set)
        ]
        if not candidates:
            continue

        selected = min(candidates, key=lambda person: (weekend_counts[person], PEOPLE.index(person)))
        normalized.loc[normalized["姓名"] == selected, day] = "班/休"
        weekend_counts[selected] += 1

    return normalized


def normalize_schedule_df(schedule_df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    days = get_month_days(year, month)
    expected_columns = ["序号", "姓名"] + [item["date"] for item in days]
    normalized = normalize_schedule_names(schedule_df)
    for column in expected_columns:
        if column not in normalized.columns:
            normalized[column] = ""
    normalized = normalized[expected_columns].fillna("")
    return normalized


def normalize_schedule_names(schedule_df: pd.DataFrame) -> pd.DataFrame:
    normalized = schedule_df.copy()
    if "姓名" in normalized.columns:
        normalized["姓名"] = normalized["姓名"].map(
            lambda person: normalize_person_name(str(person))
        )
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
