import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="プロ仕様・シフト作成くん")

st.title("🗓️ シフト作成くん（3勤1休＆2人出勤死守版）")

# --- 1. スタッフ・設定管理 ---
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = ["スタッフA", "スタッフB", "スタッフC", "スタッフD"]

with st.sidebar:
    st.header("1. スタッフ管理")
    new_staff = st.text_input("名前を追加")
    if st.button("追加"):
        if new_staff and new_staff not in st.session_state.staff_list:
            st.session_state.staff_list.append(new_staff)
            st.rerun()
    
    selected_staff = st.multiselect("メンバー選択", st.session_state.staff_list, default=st.session_state.staff_list)

    st.header("2. 年月の設定")
    year = st.number_input("年", value=datetime.now().year)
    month = st.number_input("月", min_value=1, max_value=12, value=datetime.now().month)

    st.header("3. 今月の公休（休み）数")
    target_off_days = {}
    for staff in selected_staff:
        # 出張を除いた純粋な休みの日数
        target_off_days[staff] = st.number_input(f"{staff}の休み数", min_value=0, max_value=20, value=8)

# --- カレンダー計算 ---
days_in_month = calendar.monthrange(year, month)[1]
days = [f"{i}日" for i in range(1, days_in_month + 1)]
# 土日祝の判定
weekend_indices = [i-1 for i in range(1, days_in_month + 1) if calendar.weekday(year, month, i) >= 5]

# --- 4. 出張と希望休の設定 ---
st.header("📍 出張・希望休の設定")
st.info("💡 左側に『出張（仕事）』、右側に『絶対に休み（希望休）』をチェック。設定後、下のボタンを押してください。")

if 'trip_df' not in st.session_state or not st.session_state.trip_df.index.equals(pd.Index(selected_staff)):
    st.session_state.trip_df = pd.DataFrame(False, index=selected_staff, columns=days)
if 'fixed_off_df' not in st.session_state or not st.session_state.fixed_off_df.index.equals(pd.Index(selected_staff)):
    st.session_state.fixed_off_df = pd.DataFrame(False, index=selected_staff, columns=days)

col_trip, col_off = st.columns(2)
with col_trip:
    st.subheader("✈️ 出張（仕事だけど不在）")
    edited_trip = st.data_editor(st.session_state.trip_df, key="trip_editor")
with col_off:
    st.subheader("👆 希望休（絶対休み）")
    edited_off = st.data_editor(st.session_state.fixed_off_df, key="off_editor")

# --- 5. シフト作成ロジック ---
if st.button("🚀 この条件でシフトを作成する", type="primary"):
    # 状態保存
    st.session_state.trip_df = edited_trip
    st.session_state.fixed_off_df = edited_off

    earlies = ["早1", "早2"]
    lates = ["遅1", "遅2"]
    
    res_df = pd.DataFrame("", index=selected_staff, columns=days)
    off_counts = {s: 0 for s in selected_staff}
    we_off_counts = {s: 0 for s in selected_staff}

    for d_idx, day in enumerate(days):
        is_we = d_idx in weekend_indices
        todays_fixed_off = []
        todays_trip = []
        
        # A. 手動設定の反映
        for s in selected_staff:
            if edited_trip.at[s, day]:
                res_df.at[s, day] = "出張"
                todays_trip.append(s)
            elif edited_off.at[s, day]:
                res_df.at[s, day] = "休"
                todays_fixed_off.append(s)
                off_counts[s] += 1
                if is_we: we_off_counts[s] += 1

        # B. 自動休みの割り当て（バランス調整）
        # まだ休みが決まっていない人を対象に
        rem_s = [s for s in selected_staff if res_df.at[s, day] == ""]
        random.shuffle(rem_s)
        
        # スコアリング（点数が高い人を優先的に「休み」にする）
        def get_off_priority(s):
            score = 0
            # 1. 土日祝の平等性（これまで土日に休めていない人を優先）
            if is_we:
                score += (max(we_off_counts.values()) - we_off_counts[s]) * 100
            
            # 2. 3勤1休のリズム（直近3日働いていたら休み優先度アップ）
            streak = 0
            for b in range(1, 4):
                if d_idx - b >= 0 and res_df.at[s, days[d_idx-b]] != "休":
                    streak += 1
            if streak >= 3:
                score += 50
            
            # 3. 休み数が足りない人を優先
            progress = off_counts[s] / target_off_days[s] if target_off_days[s] > 0 else 1.0
            score += (1.0 - progress) * 200
            return score

        rem_s.sort(key=get_off_priority, reverse=True)
        
        for s in rem_s:
            # 目標の休み数に達していなければ休ませる
            if off_counts[s] < target_off_days[s]:
                # 「最低2人出勤」を死守するチェック
                # 全員 - (現在の休み確定 + 今回追加する休み + 今日の出張者) >= 2
                current_away_total = len(todays_fixed_off) + 1 + len(todays_trip)
                if len(selected_staff) - current_away_total >= 2:
                    res_df.at[s, day] = "休"
                    todays_fixed_off.append(s)
                    off_counts[s] += 1
                    if is_we: we_off_counts[s] += 1

        # C. シフト割り当て（早番・遅番）
        working = [s for s in selected_staff if res_df.at[s, day] == ""]
        random.shuffle(working)
        shift_pool = (earlies + lates) * 2
        
        for s in working:
            prev = res_df.at[s, days[d_idx-1]] if d_idx > 0 else "休"
            assigned = False
            for p in shift_pool:
                if prev in lates and p in earlies: continue # 遅番→早番は禁止
                res_df.at[s, day] = p
                shift_pool.remove(p)
                assigned = True
                break
            if not assigned: res_df.at[s, day] = "遅(調)"

    # --- 結果表示 ---
    st.success("バランスの取れたシフトが完成しました！")
    
    # 見やすい色分け
    def style_shift(val):
        if val == '休': return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
        if val == '出張': return 'background-color: #e6fffa; color: #006666;'
        return ''
    
    st.dataframe(res_df.style.applymap(style_shift), height=400)
    
    # 統計
    st.subheader("📊 今月の集計（公平性の確認）")
    stats = []
    for s in selected_staff:
        stats.append({
            "スタッフ": s,
            "出張日数": f"{sum(edited_trip.loc[s])}日",
            "目標休み": f"{target_off_days[s]}日",
            "実際の休み": f"{off_counts[s]}日",
            "土日祝の休み": f"{we_off_counts[s]}回"
        })
    st.table(pd.DataFrame(stats))

    csv = res_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 CSVダウンロード", csv, "balanced_shift.csv", "text/csv")
