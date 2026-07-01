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
    load_leaves,
    load_schedule,
    save_leaves,
    save_schedule,
    schedule_to_display,
)


st.set_page_config(page_title="科室自动排班工具", layout="wide")


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

    display_df = schedule_to_display(st.session_state.schedule_df, year, month)
    date_columns = [column for column in display_df.columns if column not in ["序号", "姓名"]]
    edited_df = st.data_editor(
        display_df,
        hide_index=True,
        use_container_width=True,
        disabled=["序号", "姓名"],
        column_config={
            column: st.column_config.SelectboxColumn(column, options=SHIFT_OPTIONS, required=True)
            for column in date_columns
        },
    )

    if st.button("保存手动修改", type="primary"):
        schedule_df = display_to_schedule(edited_df, year, month)
        st.session_state.schedule_df = schedule_df
        save_schedule(year, month, schedule_df)
        st.success("修改已保存，下次打开仍会保留。")


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

    tabs = st.tabs(["请假设置", "生成排班", "手动编辑", "统计", "Excel 导出"])
    with tabs[0]:
        render_leave_section(year, month)
    with tabs[1]:
        render_generate_section(year, month)
        if st.session_state.schedule_df is not None:
            st.dataframe(schedule_to_display(st.session_state.schedule_df, year, month), hide_index=True, use_container_width=True)
    with tabs[2]:
        render_editor_section(year, month)
    with tabs[3]:
        render_stats_section(year, month)
    with tabs[4]:
        render_export_section(year, month)


if __name__ == "__main__":
    main()
