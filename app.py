from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from excel_exporter import export_schedule_excel
from scheduler import (
    PEOPLE,
    SHIFT_OPTIONS,
    calculate_stats,
    display_to_schedule,
    generate_schedule,
    get_month_days,
    list_saved_month_keys,
    load_leaves,
    load_schedule,
    save_leaves,
    save_schedule,
    schedule_to_display,
)


st.set_page_config(page_title="科室自动排班工具", layout="wide")

BLOCK_DAYS = 14


def init_state() -> None:
    today = date.today()
    st.session_state.setdefault("year", today.year)
    st.session_state.setdefault("month", today.month)
    st.session_state.setdefault("schedule_df", None)
    st.session_state.setdefault("loaded_key", None)


def current_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def load_current_schedule(year: int, month: int) -> None:
    key = current_key(year, month)
    if st.session_state.loaded_key == key:
        return
    st.session_state.schedule_df = load_schedule(year, month)
    st.session_state.loaded_key = key


def split_date_columns(display_df: pd.DataFrame) -> list[list[str]]:
    date_columns = [column for column in display_df.columns if column not in ["序号", "姓名"]]
    return [
        date_columns[index:index + BLOCK_DAYS]
        for index in range(0, len(date_columns), BLOCK_DAYS)
    ]


def render_schedule_blocks(schedule_df: pd.DataFrame, year: int, month: int) -> None:
    display_df = schedule_to_display(schedule_df, year, month)
    for block_index, columns in enumerate(split_date_columns(display_df), start=1):
        first_day = (block_index - 1) * BLOCK_DAYS + 1
        last_day = min(first_day + BLOCK_DAYS - 1, len(get_month_days(year, month)))
        st.caption(f"{month}月 {first_day}日 - {last_day}日")
        st.dataframe(
            display_df[["序号", "姓名"] + columns],
            hide_index=True,
            use_container_width=True,
        )


def edit_schedule_in_blocks(schedule_df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    display_df = schedule_to_display(schedule_df, year, month)
    merged_df = display_df.copy()

    for block_index, columns in enumerate(split_date_columns(display_df), start=1):
        first_day = (block_index - 1) * BLOCK_DAYS + 1
        last_day = min(first_day + BLOCK_DAYS - 1, len(get_month_days(year, month)))
        st.caption(f"{month}月 {first_day}日 - {last_day}日")
        edited_block = st.data_editor(
            display_df[["序号", "姓名"] + columns],
            hide_index=True,
            use_container_width=True,
            disabled=["序号", "姓名"],
            column_config={
                column: st.column_config.SelectboxColumn(column, options=SHIFT_OPTIONS, required=True)
                for column in columns
            },
            key=f"schedule_editor_{year}_{month}_{block_index}",
        )
        for column in columns:
            merged_df[column] = edited_block[column]

    return display_to_schedule(merged_df, year, month)


def render_month_selector() -> tuple[int, int]:
    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("选择年份", min_value=2020, max_value=2100, value=st.session_state.year, step=1)
    with col2:
        month = st.selectbox("选择月份", list(range(1, 13)), index=st.session_state.month - 1)

    st.session_state.year = int(year)
    st.session_state.month = int(month)
    load_current_schedule(int(year), int(month))
    return int(year), int(month)


def render_leave_section(year: int, month: int) -> None:
    st.subheader("请假设置")
    leaves = load_leaves()
    month_days = get_month_days(year, month)
    month_date_options = [item["date"] for item in month_days]

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        person = st.selectbox("选择人员", PEOPLE)
    with col2:
        leave_day = st.selectbox(
            "选择日期",
            month_date_options,
            format_func=lambda value: f"{int(value[5:7])}/{int(value[8:10])}",
        )
    with col3:
        st.write("")
        st.write("")
        if st.button("添加请假", type="primary"):
            leaves.append({"person": person, "date": leave_day})
            save_leaves(leaves)
            st.success("请假已添加")
            st.rerun()

    month_leaves = [item for item in leaves if item["date"].startswith(current_key(year, month))]
    if month_leaves:
        leave_df = pd.DataFrame(month_leaves)
        leave_df["日期"] = leave_df["date"]
        leave_df["姓名"] = leave_df["person"]
        leave_df = leave_df[["姓名", "日期"]]
        st.dataframe(leave_df, hide_index=True, use_container_width=True)

        delete_options = [
            f"{item['date']} - {item['person']}"
            for item in month_leaves
        ]
        selected_delete = st.multiselect("选择要删除的请假记录", delete_options)
        if st.button("删除选中的请假记录"):
            delete_set = set(selected_delete)
            kept = [
                item
                for item in leaves
                if f"{item['date']} - {item['person']}" not in delete_set
            ]
            save_leaves(kept)
            st.success("已删除")
            st.rerun()
    else:
        st.info("当前月份还没有请假记录。")


def render_generate_section(year: int, month: int) -> None:
    st.subheader("自动生成排班")
    if st.button("生成当月排班", type="primary"):
        schedule_df = generate_schedule(year, month)
        st.session_state.schedule_df = schedule_df
        save_schedule(year, month, schedule_df)
        st.success("排班已生成并保存。")


def render_editor_section(year: int, month: int) -> None:
    st.subheader("手动编辑排班")
    if st.session_state.schedule_df is None:
        st.info("还没有当前月份排班，请先点击“生成当月排班”。")
        return

    schedule_df = edit_schedule_in_blocks(st.session_state.schedule_df, year, month)

    if st.button("保存手动修改", type="primary"):
        st.session_state.schedule_df = schedule_df
        save_schedule(year, month, schedule_df)
        st.success("修改已保存，下次打开仍会保留。")


def render_history_section() -> None:
    st.subheader("历史排班")
    saved_months = list_saved_month_keys()
    if not saved_months:
        st.info("还没有保存过的排班。生成并保存后，这里会显示历史月份。")
        return

    selected_key = st.selectbox("选择要查看的月份", saved_months)
    year_text, month_text = selected_key.split("-", 1)
    history_year = int(year_text)
    history_month = int(month_text)
    schedule_df = load_schedule(history_year, history_month)

    if schedule_df is None:
        st.info("这个月份暂时没有可显示的排班。")
        return

    render_schedule_blocks(schedule_df, history_year, history_month)


def render_stats_section(year: int, month: int) -> None:
    st.subheader("统计")
    if st.session_state.schedule_df is None:
        st.info("生成排班后会显示统计。")
        return
    st.dataframe(calculate_stats(st.session_state.schedule_df, year, month), hide_index=True, use_container_width=True)


def render_export_section(year: int, month: int) -> None:
    st.subheader("Excel 导出")
    if st.session_state.schedule_df is None:
        st.info("生成排班后可以导出 Excel。")
        return
    excel_bytes = export_schedule_excel(st.session_state.schedule_df, year, month)
    st.download_button(
        "导出当前排班表 .xlsx",
        data=excel_bytes,
        file_name=f"{year}-{month:02d}-科室排班表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


def main() -> None:
    init_state()
    st.title("科室自动排班工具")
    year, month = render_month_selector()

    tabs = st.tabs(["生成排班", "请假设置", "手动编辑", "历史排班", "统计", "Excel 导出"])
    with tabs[0]:
        render_generate_section(year, month)
        if st.session_state.schedule_df is not None:
            render_schedule_blocks(st.session_state.schedule_df, year, month)
    with tabs[1]:
        render_leave_section(year, month)
    with tabs[2]:
        render_editor_section(year, month)
    with tabs[3]:
        render_history_section()
    with tabs[4]:
        render_stats_section(year, month)
    with tabs[5]:
        render_export_section(year, month)


if __name__ == "__main__":
    main()
