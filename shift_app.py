import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="プロ仕様・シフト作成くん")

st.title("🗓️ シフト作成くん（スタッフ別・公休日数指定版）")

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

# 土日祝の判定
weekend_indices = []
for i in range(1, days_in_month + 1):
    if calendar.weekday(year, month, i) >= 5: # 5=土, 6=日
        weekend_indices.append(i-1)

# --- 3. 【重要】スタッフごとの公休日数設定 ---
st.sidebar.header("3. 個別の公休日数（休み）")
st.sidebar.write("出張の日数は含めず、純粋に『休み』とする日数を入力してください。")
target_off_days = {}
for staff in selected_staff:
    # Aさんは3日、Bさんは8日、のようにここで個別に設定
    target_off_days[staff] = st.sidebar.number_input(f"{staff}の今月の休み数", min_value=0, max_value=20, value=8)

# --- 4. 出張と希望休の管理 ---
if 'trip_df' not in st.session_state or list(st.session_state.trip_df.index) != selected_staff:
    st.session_state.trip_df = pd.DataFrame(False, index=selected_staff, columns=days)
if 'fixed_off_df' not in st.session_state or list(st.session_state.fixed_off_df.index) != selected_staff:
    st.session_state.fixed_off_df = pd.DataFrame(False, index=selected_staff, columns=days)

st.header("📍 出張・希望休の設定")
st.info("出張は『仕事だけど不在』、希望休は『絶対に休み』として扱われます。")

tabs = st.tabs(["✈️ 出張のチェック（仕事）", "👆 希望休のチェック（絶対休み）"])

with tabs[0]:
    st.write("出張日をポチポチ選んでください（ドラッグ入力も可能）")
    edited_trip = st.data_editor(st.session_state.trip_df, key="trip_editor")
    st.session_state.trip_df = edited_trip

with tabs[1]:
    st.write("法事などの固定の休みをチェックしてください（これらも休み数にカウントされます）")
    edited_off = st.data_editor(st.session_state.fixed_off_df, key="off_editor")
    st.session_state.fixed_off_df = edited_off

# --- 5. シフト作成ロジック ---
if st.button("✨ この条件でシフトを自動作成する", type="primary"):
    earlies = ["早1", "早2"]
    lates = ["遅1", "遅2"]
    
    res_df = pd.DataFrame("", index=selected_staff, columns=days)
    off_counts = {s: 0 for s in selected_staff}
    weekend_off_counts = {s: 0 for s in selected_staff}
    
    for d_idx, day in enumerate(days):
        is_we = d_idx in weekend_indices
        todays_off = []
        
        # 1. 状態の確定
        for s in selected_staff:
            if edited_trip.at[s, day]:
                res_df.at[s, day] = "出張"
            elif edited_off.at[s, day]:
                res_df.at[s, day] = "休"
                todays_off.append(s)
                off_counts[s] += 1
                if is_we: weekend_off_counts[s] += 1

        # 2. 4連勤防止（出張も連勤に含む）
        for s in selected_staff:
            if s not in todays_off and res_df.at[s, day] != "出張":
                work_streak = 0
                for b in range(1, 4):
                    if d_idx - b >= 0 and res_df.at[s, days[d_idx-b]] != "休":
                        work_streak += 1
                if work_streak >= 3:
                    if len(selected_staff) - (len(todays_off) + 1 + sum(edited_trip.loc[:, day])) >= 2:
                        res_df.at[s, day] = "休"
                        todays_off.append(s)
                        off_counts[s] += 1
                        if is_we: weekend_off_counts[s] += 1

        # 3. 追加の休みを割り振る
        rem_s = [s for s in selected_staff if s not in todays_off and res_df.at[s, day] != "出張"]
        random.shuffle(rem_s)
        # 土日休みの公平性と、目標達成率でソート
        rem_s.sort(key=lambda s: (weekend_off_counts[s] if is_we else 0, off_counts[s] / target_off_days[s] if target_off_days[s]>0 else 1))
        
        for s in rem_s:
            if off_counts[s] < target_off_days[s]:
                if len(selected_staff) - (len(todays_off) + 1 + sum(edited_trip.loc[:, day])) >= 2:
                    res_df.at[s, day] = "休"
                    todays_off.append(s)
                    off_counts[s] += 1
                    if is_we: weekend_off_counts[s] += 1

        # 4. シフト割り当て
        working = [s for s in selected_staff if s not in todays_off and res_df.at[s, day] != "出張"]
        random.shuffle(working)
        pool = earlies + lates + earlies + lates
        
        for s in working:
            prev = res_df.at[s, days[d_idx-1]] if d_idx > 0 else "休"
            assigned = False
            for p in pool:
                if prev in lates and p in earlies: continue 
                res_df.at[s, day] = p
                pool.remove(p)
                assigned = True
                break
            if not assigned: res_df.at[s, day] = "調整"

    st.success("シフトが完成しました！")
    
    # 色付け表示
    st.dataframe(res_df.style.applymap(lambda x: 'background-color: #ffcccc' if x=='休' else ('background-color: #ccffcc' if x=='出張' else '')))
    
    # 統計表
    st.subheader("📊 最終集計（不在日の合計確認）")
    stats = []
    for s in selected_staff:
        trip_days = sum(edited_trip.loc[s])
        stats.append({
            "スタッフ": s,
            "出張（仕事）": f"{trip_days}日間",
            "公休（休み）": f"{off_counts[s]}日間 / 目標{target_off_days[s]}日",
            "不在の合計": f"{trip_days + off_counts[s]}日間",
            "土日祝の休み": f"{weekend_off_counts[s]}日間"
        })
    st.table(pd.DataFrame(stats))

    csv = res_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 CSV保存", csv, "shift_custom.csv", "text/csv")
