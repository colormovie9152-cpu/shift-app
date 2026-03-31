import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="サクサク・シフト作成くん")

st.title("🗓️ シフト作成くん（休み日数・厳守版）")

# --- 1. スタッフ設定 ---
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = ["スタッフA", "スタッフB", "スタッフC", "スタッフD"]

with st.sidebar:
    st.header("1. スタッフ管理")
    new_staff = st.text_input("名前を追加")
    if st.button("追加"):
        if new_staff and new_staff not in st.session_state.staff_list:
            st.session_state.staff_list.append(new_staff)
            st.rerun()
    
    selected_staff = st.multiselect("今月のメンバー", st.session_state.staff_list, default=st.session_state.staff_list)

    # --- 2. 年月の設定 ---
    st.header("2. 年月の設定")
    year = st.number_input("年", value=datetime.now().year)
    month = st.number_input("月", min_value=1, max_value=12, value=datetime.now().month)

    # --- 3. 休み日数の設定 ---
    st.header("3. 今月の休み数")
    st.write("出張日数は含めず、純粋な『休み』の合計数を入力。")
    target_off_days = {}
    for staff in selected_staff:
        target_off_days[staff] = st.number_input(f"{staff}の休み数", min_value=0, max_value=20, value=8)

days_in_month = calendar.monthrange(year, month)[1]
days = [f"{i}日" for i in range(1, days_in_month + 1)]
weekend_indices = [i-1 for i in range(1, days_in_month + 1) if calendar.weekday(year, month, i) >= 5]

# --- 4. 出張と希望休の設定 ---
st.header("📍 出張・希望休の設定")
st.markdown("""
<style>
    div[data-testid="stDataEditor"] div { cursor: pointer !important; }
</style>
""", unsafe_allow_html=True)

# データの保持（リロード対策）
if 'trip_df' not in st.session_state:
    st.session_state.trip_df = pd.DataFrame(False, index=selected_staff, columns=days)
if 'fixed_off_df' not in st.session_state:
    st.session_state.fixed_off_df = pd.DataFrame(False, index=selected_staff, columns=days)

# メンバーが変更された場合のみ再構築
if not st.session_state.trip_df.index.equals(pd.Index(selected_staff)):
    st.session_state.trip_df = pd.DataFrame(False, index=selected_staff, columns=days)
    st.session_state.fixed_off_df = pd.DataFrame(False, index=selected_staff, columns=days)

col_trip, col_off = st.columns(2)

with col_trip:
    st.subheader("✈️ 出張（仕事だけど不在）")
    edited_trip = st.data_editor(st.session_state.trip_df, key="trip_editor_key")

with col_off:
    st.subheader("👆 希望休（絶対休み）")
    edited_off = st.data_editor(st.session_state.fixed_off_df, key="off_editor_key")

# --- 5. シフト作成ロジック ---
if st.button("🚀 シフトを自動作成する", type="primary"):
    # 状態を保存
    st.session_state.trip_df = edited_trip
    st.session_state.fixed_off_df = edited_off

    earlies = ["早1", "早2"]
    lates = ["遅1", "遅2"]
    
    res_df = pd.DataFrame("", index=selected_staff, columns=days)
    off_counts = {s: 0 for s in selected_staff}
    we_off_counts = {s: 0 for s in selected_staff}

    for d_idx, day in enumerate(days):
        is_we = d_idx in weekend_indices
        todays_off = []
        
        # A. 確定事項の反映
        for s in selected_staff:
            if edited_trip.at[s, day]:
                res_df.at[s, day] = "出張"
            elif edited_off.at[s, day]:
                res_df.at[s, day] = "休"
                todays_off.append(s)
                off_counts[s] += 1
                if is_we: we_off_counts[s] += 1

        # B. 休み日数の割り振り
        rem_s = [s for s in selected_staff if s not in todays_off and res_df.at[s, day] != "出張"]
        random.shuffle(rem_s)
        # 土日休みの公平性と、目標達成率でソート
        rem_s.sort(key=lambda s: (we_off_counts[s] if is_we else 0, off_counts[s] / target_off_days[s] if target_off_days[s]>0 else 1))
        
        for s in rem_s:
            # 指定された休み数（target_off_days）を超えないように厳格にチェック
            if off_counts[s] < target_off_days[s]:
                # 最低2人出勤を維持できる場合のみ休ませる
                total_away = len(todays_off) + 1 + sum(edited_trip.iloc[:, d_idx])
                if len(selected_staff) - total_away >= 2:
                    res_df.at[s, day] = "休"
                    todays_off.append(s)
                    off_counts[s] += 1
                    if is_we: we_off_counts[s] += 1

        # C. シフト割り当て
        working = [s for s in selected_staff if s not in todays_off and res_df.at[s, day] != "出張"]
        random.shuffle(working)
        pool = (earlies + lates) * 2 # 余裕を持ってプール
        
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
    st.dataframe(res_df.style.applymap(lambda x: 'background-color: #ffcccc' if x=='休' else ('background-color: #ccffcc' if x=='出張' else '')))
    
    # 統計
    st.subheader("📊 集計確認")
    stats = [{"スタッフ": s, "出張": f"{sum(edited_trip.loc[s])}日", "実際の休み": f"{off_counts[s]}日（目標:{target_off_days[s]}日）", "土日祝休み": f"{we_off_counts[s]}日"} for s in selected_staff]
    st.table(pd.DataFrame(stats))
