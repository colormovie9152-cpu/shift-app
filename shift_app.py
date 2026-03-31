import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="プロ版・自動シフト作成くん")

st.title("🗓️ シフト作成くん（出張・公休調整版）")

# --- サイドバー：基本設定 ---
st.sidebar.header("1. スタッフと「追加の休み」設定")
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = ["スタッフA", "スタッフB", "スタッフC", "スタッフD"]

new_staff = st.sidebar.text_input("名前を追加")
if st.sidebar.button("追加"):
    if new_staff and new_staff not in st.session_state.staff_list:
        st.session_state.staff_list.append(new_staff)

selected_staff = st.sidebar.multiselect("今月のメンバー", st.session_state.staff_list, default=st.session_state.staff_list)

# 各スタッフの「追加でほしい休み」を設定
st.sidebar.subheader("出張/希望休「以外」の休み数")
extra_off_days = {}
for staff in selected_staff:
    extra_off_days[staff] = st.sidebar.number_input(f"{staff}の追加休み", min_value=0, max_value=15, value=8, help="チェックを入れた日以外に、何日休ませるかを設定します。")

# --- 月の設定 ---
st.sidebar.header("2. 年月の設定")
year = st.sidebar.number_input("年", value=datetime.now().year)
month = st.sidebar.number_input("月", min_value=1, max_value=12, value=datetime.now().month)

days_in_month = calendar.monthrange(year, month)[1]
days = [f"{i}日" for i in range(1, days_in_month + 1)]

# 土日の判定
weekend_indices = []
for i in range(1, days_in_month + 1):
    if calendar.weekday(year, month, i) >= 5: # 5=土, 6=日
        weekend_indices.append(i-1)

# --- イレギュラー設定 ---
st.header("3. 出張・希望休の設定（チェックした日は出勤しません）")
st.info("Aさんの出張（15日〜24日）などは、ここでチェックを入れてください。")
if 'holiday_data' not in st.session_state:
    st.session_state.holiday_data = pd.DataFrame(False, index=selected_staff, columns=days)

# メンバーが変更された時にデータフレームを更新
edited_holidays = st.data_editor(pd.DataFrame(False, index=selected_staff, columns=days))

# --- シフト作成ロジック ---
if st.button("✨ シフトを自動作成する"):
    earlies = ["早1(7:30)", "早2(8:30)"]
    lates = ["遅1(11:30)", "遅2(12:30)"]
    
    result_df = pd.DataFrame("休", index=selected_staff, columns=days)
    
    # 休み実績のカウント用
    total_off_target = {}
    current_off_counts = {staff: 0 for staff in selected_staff}
    weekend_off_counts = {staff: 0 for staff in selected_staff}
    
    # 各スタッフの「目標合計休み数」を計算（チェックした数 + 追加の休み）
    for staff in selected_staff:
        fixed_off_count = sum(edited_holidays.loc[staff])
        total_off_target[staff] = fixed_off_count + extra_off_days[staff]

    for d_idx, day in enumerate(days):
        is_weekend = d_idx in weekend_indices
        available_staff = list(selected_staff)
        
        # 1. チェックされた日（出張など）を強制休みに
        off_today = []
        for staff in selected_staff:
            if edited_holidays.at[staff, day]:
                off_today.append(staff)
                current_off_counts[staff] += 1
                if is_weekend: weekend_off_counts[staff] += 1

        # 2. 4連勤防止（3連勤後は休み）
        for staff in selected_staff:
            if staff not in off_today:
                work_count = 0
                for b in range(1, 4):
                    if d_idx - b >= 0 and result_df.at[staff, days[d_idx-b]] != "休":
                        work_count += 1
                if work_count >= 3:
                    if len(
