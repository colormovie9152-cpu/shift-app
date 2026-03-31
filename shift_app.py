import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date
import random

st.set_page_config(layout="wide", page_title="プロ版・自動シフト作成くん")

st.title("🗓️ プロ版・自動シフト作成くん")

# --- サイドバー：基本設定 ---
st.sidebar.header("1. スタッフと休み数の設定")
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = ["スタッフA", "スタッフB", "スタッフC", "スタッフD"]

new_staff = st.sidebar.text_input("名前を追加")
if st.sidebar.button("追加"):
    if new_staff and new_staff not in st.session_state.staff_list:
        st.session_state.staff_list.append(new_staff)

selected_staff = st.sidebar.multiselect("今月のメンバー", st.session_state.staff_list, default=st.session_state.staff_list)

# 各自の理想の休み数を設定（出張などを考慮して調整可能にする）
st.sidebar.subheader("月間の希望休み数")
target_off_days = {}
for staff in selected_staff:
    target_off_days[staff] = st.sidebar.number_input(f"{staff}の休み数", min_value=0, max_value=15, value=8)

# --- 月の設定 ---
st.sidebar.header("2. 年月の設定")
year = st.sidebar.number_input("年", value=datetime.now().year)
month = st.sidebar.number_input("月", min_value=1, max_value=12, value=datetime.now().month)

days_in_month = calendar.monthrange(year, month)[1]
days = [f"{i}日" for i in range(1, days_in_month + 1)]

# 祝日や土日の判定
weekend_indices = []
for i in range(1, days_in_month + 1):
    if calendar.weekday(year, month, i) >= 5: # 5=土曜, 6=日曜
        weekend_indices.append(i-1)

# --- イレギュラー設定 ---
st.header("3. 出張・絶対に休みの日の設定")
st.write("※出張や希望休など、シフトに入れない日にチェックを入れてください。")
holiday_df = pd.DataFrame(False, index=selected_staff, columns=days)
edited_holidays = st.data_editor(holiday_df)

# --- シフト作成ロジック ---
if st.button("✨ プロ仕様でシフトを自動作成する"):
    earlies = ["早1(7:30)", "早2(8:30)"]
    lates = ["遅1(11:30)", "遅2(12:30)"]
    
    result_df = pd.DataFrame("休", index=selected_staff, columns=days)
    # 休み実績のカウント用
    current_off_counts = {staff: 0 for staff in selected_staff}
    weekend_off_counts = {staff: 0 for staff in selected_staff}
    
    for d_idx, day in enumerate(days):
        is_weekend = d_idx in weekend_indices
        available_staff = list(selected_staff)
        
        # 1. 強制休みの確定
        off_today = []
        for staff in selected_staff:
            if edited_holidays.at[staff, day]:
                off_today.append(staff)
                current_off_counts[staff] += 1
                if is_weekend: weekend_off_counts[staff] += 1

        # 2. 4連勤防止ルール (3連勤してたら強制休み)
        for staff in selected_staff:
            if staff not in off_today:
                count = 0
                for b in range(1, 4):
                    if d_idx - b >= 0 and result_df.at[staff, days[d_idx-b]] != "休":
                        count += 1
                if count >= 3: # 3連勤済みなら今日は休み
                    if len(selected_staff) - (len(off_today) + 1) >= 2: # 最低2人維持
                        off_today.append(staff)
                        current_off_counts[staff] += 1
                        if is_weekend: weekend_off_counts[staff] += 1

        # 3. 土日祝の公平化 & 休み数の調整
        remaining_staff = [s for s in selected_staff if s not in off_today]
        # 「土日休みが少ない人」「トータルの休みが足りない人」を優先的に休ませる
        random.shuffle(remaining_staff)
        remaining_staff.sort(key=lambda s: (weekend_off_counts[s] if is_weekend else current_off_counts[s]))

        for staff in remaining_staff:
            # 休み数が目標に達していない ＆ 出勤2人を維持できるなら休ませる
            if current_off_counts[staff] < target_off_days[staff]:
                if len(selected_staff) - (len(off_today) + 1) >= 2:
                    off_today.append(staff)
                    current_off_counts[staff] += 1
                    if is_weekend: weekend_off_counts[staff] += 1

        # 4. シフト割り当て
        working_staff = [s for s in selected_staff if s not in off_today]
        random.shuffle(working_staff)
        shift_pool = earlies + lates + earlies + lates
        
        for staff in working_staff:
            prev_shift = result_df.at[staff, days[d_idx-1]] if d_idx > 0 else "休"
            assigned = False
            for s_type in shift_pool:
                if prev_shift in lates and s_type in earlies: continue
                result_df.at[staff, day] = s_type
                shift_pool.remove(s_type)
                assigned = True
                break
            if not assigned:
                result_df.at[staff, day] = "遅番(調整)"

    st.success("プロ仕様のシフトが完成しました！")
    st.dataframe(result_df)
    
    # 公平性の確認用
    st.subheader("📊 今月の休み実績（公平性のチェック用）")
    summary_df = pd.DataFrame({
        "設定した休み数": [target_off_days[s] for s in selected_staff],
        "実際の合計休み数": [current_off_counts[s] for s in selected_staff],
        "うち土日の休み数": [weekend_off_counts[s] for s in selected_staff]
    }, index=selected_staff)
    st.table(summary_df)

    csv = result_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 CSVで保存", csv, "pro_shift.csv", "text/csv")

# --- 削除機能 ---
st.sidebar.markdown("---")
staff_to_delete = st.sidebar.selectbox("スタッフ削除", ["選択"] + st.session_state.staff_list)
if st.sidebar.button("削除実行"):
    if staff_to_delete in st.session_state.staff_list:
        st.session_state.staff_list.remove(staff_to_delete)
        st.rerun()
