import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="決定版・自動シフト作成くん")

st.title("🗓️ シフト作成くん（出張・公休 完全分離版）")

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

# --- 3. 休み日数の設定 ---
st.sidebar.header("3. 公休（純粋な休み）の日数")
st.sidebar.write("出張の日数とは『別』に、何日休ませるか設定します。")
target_off_days = {}
for staff in selected_staff:
    target_off_days[staff] = st.sidebar.number_input(f"{staff}の休み希望数", min_value=0, max_value=20, value=8)

# --- 4. 出張と希望休の管理 ---
if 'trip_df' not in st.session_state or len(st.session_state.trip_df) != len(selected_staff):
    st.session_state.trip_df = pd.DataFrame(False, index=selected_staff, columns=days)
if 'fixed_off_df' not in st.session_state or len(st.session_state.fixed_off_df) != len(selected_staff):
    st.session_state.fixed_off_df = pd.DataFrame(False, index=selected_staff, columns=days)

st.header("📍 ステータス設定")

tabs = st.tabs(["✈️ 出張の設定", "👆 希望休（絶対休み）の設定"])

with tabs[0]:
    st.subheader("出張（仕事だけど不在）の期間入力")
    c1, c2, c3, c4 = st.columns(4)
    with c1: t_staff = st.selectbox("誰が？", selected_staff, key="t_s")
    with c2: s_day = st.selectbox("いつから？", days, key="s_d")
    with c3: e_day = st.selectbox("いつまで？", days, key="e_d")
    with c4:
        st.write("")
        if st.button("出張として登録"):
            si, ei = days.index(s_day), days.index(e_day)
            for i in range(si, ei + 1):
                st.session_state.trip_df.at[t_staff, days[i]] = True
                st.session_state.fixed_off_df.at[t_staff, days[i]] = False # 休みと重複させない
            st.rerun()
    st.write("【現在の出張状況】（チェックが入っている日は出張）")
    edited_trip = st.data_editor(st.session_state.trip_df, key="trip_editor")
    st.session_state.trip_df = edited_trip

with tabs[1]:
    st.subheader("希望休（絶対休み）の個別チェック")
    st.write("「この日は法事」など、出張以外の純粋な休みはここでチェックしてください。")
    edited_off = st.data_editor(st.session_state.fixed_off_df, key="off_editor")
    st.session_state.fixed_off_df = edited_off

# --- 5. シフト作成ロジック ---
if st.button("✨ シフトを自動作成する", type="primary"):
    earlies = ["早1", "早2"]
    lates = ["遅1", "遅2"]
    
    # 結果用データフレーム
    res_df = pd.DataFrame("", index=selected_staff, columns=days)
    
    # 統計用
    off_counts = {s: 0 for s in selected_staff}
    weekend_off_counts = {s: 0 for s in selected_staff}
    
    for d_idx, day in enumerate(days):
        is_we = d_idx in weekend_indices
        
        # 1. 状態の確定（出張か、固定休みか）
        todays_off = []
        for s in selected_staff:
            if edited_trip.at[s, day]:
                res_df.at[s, day] = "出張"
            elif edited_off.at[s, day]:
                res_df.at[s, day] = "休"
                todays_off.append(s)
                off_counts[s] += 1
                if is_we: weekend_off_counts[s] += 1

        # 2. 4連勤防止ルール（出張も仕事としてカウント）
        for s in selected_staff:
            if s not in todays_off and res_df.at[s, day] != "出張":
                work_streak = 0
                for b in range(1, 4):
                    if d_idx - b >= 0 and res_df.at[s, days[d_idx-b]] != "休":
                        work_streak += 1
                if work_streak >= 3:
                    # 他に2人以上出勤できるなら休ませる
                    if len(selected_staff) - (len(todays_off) + 1 + sum(edited_trip.loc[:, day])) >= 2:
                        res_df.at[s, day] = "休"
                        todays_off.append(s)
                        off_counts[s] += 1
                        if is_we: weekend_off_counts[s] += 1

        # 3. 追加の休み（月8日に足りない分）を土日バランス良く割り振る
        rem_s = [s for s in selected_staff if s not in todays_off and res_df.at[s, day] != "出張"]
        random.shuffle(rem_s)
        # 土日休みの公平性と、目標達成率でソート
        rem_s.sort(key=lambda s: (weekend_off_counts[s] if is_we else 0, off_counts[s] / target_off_days[s] if target_off_days[s]>0 else 1))
        
        for s in rem_s:
            if off_counts[s] < target_off_days[s]:
                # 最低2人出勤を維持
                if len(selected_staff) - (len(todays_off) + 1 + sum(edited_trip.loc[:, day])) >= 2:
                    res_df.at[s, day] = "休"
                    todays_off.append(s)
                    off_counts[s] += 1
                    if is_we: weekend_off_counts[s] += 1

        # 4. 早番・遅番の割り当て
        working = [s for s in selected_staff if s not in todays_off and res_df.at[s, day] != "出張"]
        random.shuffle(working)
        pool = earlies + lates + earlies + lates
        
        for s in working:
            prev = res_df.at[s, days[d_idx-1]] if d_idx > 0 else "休"
            assigned = False
            for p in pool:
                if prev in lates and p in earlies: continue # 遅番→早番禁止
                res_df.at[s, day] = p
                pool.remove(p)
                assigned = True
                break
            if not assigned:
                res_df.at[s, day] = "調整"

    st.success("シフトが完成しました！")
    st.dataframe(res_df.style.applymap(lambda x: 'background-color: #ffcccc' if x=='休' else ('background-color: #ccffcc' if x=='出張' else '')))
    
    # 統計
    st.subheader("📊 休みと出張の集計（公平性の確認）")
    stats = []
    for s in selected_staff:
        stats.append({
            "スタッフ": s,
            "出張日数": sum(edited_trip.loc[s]),
            "設定した公休日数": target_off_days[s],
            "実際の公休日数": off_counts[s],
            "うち土日祝の休み": weekend_off_counts[s]
        })
    st.table(pd.DataFrame(stats))

    csv = res_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 CSVダウンロード", csv, "shift_perfect.csv", "text/csv")
