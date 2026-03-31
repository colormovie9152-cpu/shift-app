import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="プロ版・自動シフト作成くん")

st.title("🗓️ シフト作成くん（出張＆希望休 完璧版）")

# --- 1. スタッフ設定 ---
st.sidebar.header("1. スタッフ設定")
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = ["スタッフA", "スタッフB", "スタッフC", "スタッフD"]

new_staff = st.sidebar.text_input("名前を追加")
if st.sidebar.button("追加"):
    if new_staff and new_staff not in st.session_state.staff_list:
        st.session_state.staff_list.append(new_staff)

selected_staff = st.sidebar.multiselect("今月のメンバー", st.session_state.staff_list, default=st.session_state.staff_list)

# --- 2. 年月の設定 ---
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

# --- 3. 休み数の設定 ---
st.sidebar.header("3. 公休（追加の休み）設定")
st.sidebar.write("出張や希望休とは「別」に、自動で割り振る休みの日数です。")
extra_off_days = {}
for staff in selected_staff:
    extra_off_days[staff] = st.sidebar.number_input(f"{staff}の追加休み", min_value=0, max_value=15, value=4)

# --- 4. 絶対休みの入力（出張 ＆ 希望休） ---
st.header("📍 絶対に休ませる日の設定（出張・希望休）")

# 記憶の保管庫の準備
if 'holiday_df' not in st.session_state or \
   len(st.session_state.holiday_df) != len(selected_staff) or \
   list(st.session_state.holiday_df.index) != selected_staff:
    st.session_state.holiday_df = pd.DataFrame(False, index=selected_staff, columns=days)

# --- ✨新機能：出張の一括入力 ---
st.subheader("✈️ 出張などの「期間」を一括入力")
st.write("「Aさんは15日〜24日まで出張」などの場合、ここで一気に休みにできます。")
col1, col2, col3, col4 = st.columns(4)
with col1:
    trip_staff = st.selectbox("誰が？", selected_staff)
with col2:
    start_day = st.selectbox("いつから？", days, index=0)
with col3:
    end_day = st.selectbox("いつまで？", days, index=0)
with col4:
    st.write("") # ボタンの位置調整
    if st.button("一括で休みにする"):
        s_idx = days.index(start_day)
        e_idx = days.index(end_day)
        if s_idx <= e_idx:
            for i in range(s_idx, e_idx + 1):
                st.session_state.holiday_df.at[trip_staff, days[i]] = True
            st.rerun() # 画面を更新して表に反映
        else:
            st.error("期間が逆になっています！")

st.markdown("---")

# --- 既存のピンポイント入力 ---
st.subheader("👆 ピンポイントの希望休 ＆ 確認表")
st.write("上の出張入力で反映されたチェックの確認や、「16日だけ休みたい」といった個別のチェックをポチポチ入力できます。")
edited_holidays = st.data_editor(st.session_state.holiday_df, key="holiday_editor")
st.session_state.holiday_df = edited_holidays

# --- 5. シフト作成ロジック ---
if st.button("✨ この設定でシフトを自動作成する", type="primary"):
    earlies = ["早1(7:30)", "早2(8:30)"]
    lates = ["遅1(11:30)", "遅2(12:30)"]
    
    result_df = pd.DataFrame("休", index=selected_staff, columns=days)
    
    current_off_counts = {staff: 0 for staff in selected_staff}
    weekend_off_counts = {staff: 0 for staff in selected_staff}
    total_off_target = {}
    
    for staff in selected_staff:
        # 固定休（チェックされた数）＋ サイドバーの追加休み数
        fixed_count = sum(edited_holidays.loc[staff])
        total_off_target[staff] = fixed_count + extra_off_days[staff]

    for d_idx, day in enumerate(days):
        is_weekend = d_idx in weekend_indices
        available_staff = list(selected_staff)
        
        # A. チェックされた日を確定させる
        off_today = []
        for staff in selected_staff:
            if edited_holidays.at[staff, day]:
                off_today.append(staff)
                current_off_counts[staff] += 1
                if is_weekend: weekend_off_counts[staff] += 1

        # B. 4連勤防止（3連勤後は強制休み）
        for staff in selected_staff:
            if staff not in off_today:
                work_count = 0
                for b in range(1, 4):
                    if d_idx - b >= 0 and result_df.at[staff, days[d_idx-b]] != "休":
                        work_count += 1
                if work_count >= 3:
                    if len(selected_staff) - (len(off_today) + 1) >= 2:
                        off_today.append(staff)
                        current_off_counts[staff] += 1
                        if is_weekend: weekend_off_counts[staff] += 1

        # C. 公休（追加分）をバランスよく配置
        remaining_staff = [s for s in selected_staff if s not in off_today]
        random.shuffle(remaining_staff)
        remaining_staff.sort(key=lambda s: (weekend_off_counts[s] if is_weekend else 0, current_off_counts[s] / total_off_target[s] if total_off_target[s] > 0 else 1))

        for staff in remaining_staff:
            if current_off_counts[staff] < total_off_target[staff]:
                if len(selected_staff) - (len(off_today) + 1) >= 2:
                    off_today.append(staff)
                    current_off_counts[staff] += 1
                    if is_weekend: weekend_off_counts[staff] += 1

        # D. シフト割り当て
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
                result_df.at[staff, day] = "遅(調)"

    st.success("シフトを作成しました！")
    st.dataframe(result_df)
    
    # 統計
    st.subheader("📊 公平性の確認")
    summary_list = []
    for s in selected_staff:
        summary_list.append({
            "スタッフ": s,
            "出張・希望休(チェック数)": sum(edited_holidays.loc[s]),
            "自動で入れた公休": extra_off_days[s],
            "実際の合計休み": current_off_counts[s],
            "土日の休み数": weekend_off_counts[s]
        })
    st.table(pd.DataFrame(summary_list))

    csv = result_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 CSVダウンロード", csv, "shift_final.csv", "text/csv")

# --- 削除機能 ---
st.sidebar.markdown("---")
staff_to_delete = st.sidebar.selectbox("スタッフ削除", ["選択"] + st.session_state.staff_list)
if st.sidebar.button("削除実行"):
    if staff_to_delete in st.session_state.staff_list:
        st.session_state.staff_list.remove(staff_to_delete)
        if 'holiday_df' in st.session_state:
            del st.session_state.holiday_df
        st.rerun()
