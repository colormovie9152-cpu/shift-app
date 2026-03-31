import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="プロ仕様・シフト作成くん")

st.title("🗓️ シフト作成くん（完全バランス分散版）")

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
        target_off_days[staff] = st.number_input(f"{staff}の休み数", min_value=0, max_value=20, value=8)

# --- カレンダー計算 ---
days_in_month = calendar.monthrange(year, month)[1]
days = [f"{i}日" for i in range(1, days_in_month + 1)]
weekend_indices = [i-1 for i in range(1, days_in_month + 1) if calendar.weekday(year, month, i) >= 5]

# --- 4. 出張と希望休の設定 ---
st.header("📍 出張・希望休の設定")

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
    st.session_state.trip_df = edited_trip
    st.session_state.fixed_off_df = edited_off

    earlies = ["早1", "早2"]
    lates = ["遅1", "遅2"]
    
    res_df = pd.DataFrame("", index=selected_staff, columns=days)
    off_counts = {s: 0 for s in selected_staff}
    we_off_counts = {s: 0 for s in selected_staff}

    def get_streak(staff, current_d_idx):
        streak = 0
        for b in range(1, current_d_idx + 1):
            if res_df.at[staff, days[current_d_idx-b]] != "休":
                streak += 1
            else:
                break
        return streak

    for d_idx, day in enumerate(days):
        is_we = d_idx in weekend_indices
        todays_away = []
        
        # A. 手動設定（出張・希望休）の反映
        for s in selected_staff:
            if edited_trip.at[s, day]:
                res_df.at[s, day] = "出張"
                todays_away.append(s)
            elif edited_off.at[s, day]:
                res_df.at[s, day] = "休"
                todays_away.append(s)
                off_counts[s] += 1
                if is_we: we_off_counts[s] += 1

        # B. 【超重要】ペースメーカーによる休み分散ロジック
        candidates = []
        for s in selected_staff:
            if res_df.at[s, day] != "": continue # すでに予定がある人はスキップ
            if off_counts[s] >= target_off_days[s]: continue # 休み数に達した人もスキップ

            streak = get_streak(s, d_idx)
            offs_left = target_off_days[s] - off_counts[s]
            days_left = days_in_month - d_idx
            
            # 今日までに「本来何日休んでいるべきか」の理想ペースを計算
            expected_offs = ((d_idx + 1) / days_in_month) * target_off_days[s]

            score = 0
            
            # 1. 絶対に休ませる条件（残りの日数が全部休みじゃないと間に合わない時）
            if offs_left >= days_left:
                score += 10000
                
            # 2. 4連勤以上は強制休み（これ以上は疲労が溜まる）
            if streak >= 4:
                score += 5000
                
            # 3. ペース配分（ここが前半への偏りを防ぐ最強の盾！）
            if off_counts[s] < expected_offs:
                score += 1000 # ペースが遅れているから休んでヨシ
            else:
                score -= 1000 # ペースが早いから今は休んじゃダメ！（後半に残す）
                
            # 4. 週末の平等性（土日に休めていない人を優先）
            if is_we:
                we_diff = max(we_off_counts.values()) - we_off_counts[s]
                score += we_diff * 100
                
            # 5. 連勤の疲労度（働いている日数が長いほど休ませたくなる）
            if streak >= 2:
                score += streak * 10
                
            candidates.append((score + random.random(), s))

        # スコアが高い順（休ませるべき順）に並び替え
        candidates.sort(reverse=True)
        
        for score, s in candidates:
            # スコアがマイナス（＝ペースが早すぎる）場合は、強制条件がない限り休ませない
            if score < 0: continue 
            
            # 常に2人以上の出勤を死守する
            if len(selected_staff) - len(todays_away) <= 2: break 
            
            res_df.at[s, day] = "休"
            todays_away.append(s)
            off_counts[s] += 1
            if is_we: we_off_counts[s] += 1

        # C. 早番・遅番の割り当て
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
    st.success("間隔がバッチリ調整されたシフトが完成しました！")
    
    def style_shift(val):
        if val == '休': return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
        if val == '出張': return 'background-color: #e6fffa; color: #006666;'
        return ''
    
    st.dataframe(res_df.style.applymap(style_shift), height=400)
    
    st.subheader("📊 今月の集計（ペースと公平性の確認）")
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
    st.download_button("📥 CSVダウンロード", csv, "perfect_paced_shift.csv", "text/csv")
