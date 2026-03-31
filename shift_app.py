import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date
import random
import math
import jpholiday

st.set_page_config(layout="wide", page_title="究極・シフト作成くん")

st.title("🗓️ 究極・シフト作成くん（3人出勤バランス対応版）")

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

    st.header("3. 今月の休み数設定")
    target_off_days = {}
    for staff in selected_staff:
        target_off_days[staff] = st.number_input(f"{staff}の休み数", min_value=0, max_value=20, value=8)

# --- カレンダー計算（曜日・祝日対応） ---
days_in_month = calendar.monthrange(year, month)[1]
weekday_ja = ["月", "火", "水", "木", "金", "土", "日"]
days_labels = [] 
is_holiday_list = [] 

for i in range(1, days_in_month + 1):
    curr_date = date(year, month, i)
    wd = weekday_ja[curr_date.weekday()]
    holiday_name = jpholiday.is_holiday_name(curr_date)
    
    label = f"{i}日({wd})"
    if holiday_name:
        label += f" ※{holiday_name}"
        is_holiday_list.append(True)
    elif curr_date.weekday() >= 5: 
        is_holiday_list.append(True)
    else:
        is_holiday_list.append(False)
    
    days_labels.append(label)

# --- 4. 出張と希望休の設定 ---
st.header("📍 出張・希望休の設定")

if 'trip_df' not in st.session_state or \
   not st.session_state.trip_df.index.equals(pd.Index(selected_staff)) or \
   list(st.session_state.trip_df.columns) != days_labels:
    st.session_state.trip_df = pd.DataFrame(False, index=selected_staff, columns=days_labels)

if 'fixed_off_df' not in st.session_state or \
   not st.session_state.fixed_off_df.index.equals(pd.Index(selected_staff)) or \
   list(st.session_state.fixed_off_df.columns) != days_labels:
    st.session_state.fixed_off_df = pd.DataFrame(False, index=selected_staff, columns=days_labels)

col_trip, col_off = st.columns(2)
with col_trip:
    st.subheader("✈️ 出張（仕事）")
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
    
    res_df = pd.DataFrame("", index=selected_staff, columns=days_labels)
    off_counts = {s: 0 for s in selected_staff}
    holiday_off_counts = {s: 0 for s in selected_staff} 

    def get_streak(staff, current_idx):
        streak = 0
        for b in range(1, current_idx + 1):
            if res_df.at[staff, days_labels[current_idx-b]] != "休":
                streak += 1
            else:
                break
        return streak

    for d_idx, day_label in enumerate(days_labels):
        is_sp_day = is_holiday_list[d_idx] 
        todays_away = []
        
        # A. 手動設定の反映
        for s in selected_staff:
            if edited_trip.at[s, day_label]:
                res_df.at[s, day_label] = "出張"
                todays_away.append(s)
            elif edited_off.at[s, day_label]:
                res_df.at[s, day_label] = "休"
                todays_away.append(s)
                off_counts[s] += 1
                if is_sp_day: holiday_off_counts[s] += 1

        # B. 【改善】1日あたりの「理想の休み人数」を計算し、3人出勤をキープする
        rem_s = [s for s in selected_staff if res_df.at[s, day_label] == ""]
        
        # 全員の残り休み日数を合計して、残りの日数で割る（今日は何人休ませるべきか）
        total_rem_offs = sum([max(0, target_off_days[s] - off_counts[s]) for s in selected_staff])
        rem_days_total = len(days_labels) - d_idx
        ideal_offs_today_float = total_rem_offs / rem_days_total if rem_days_total > 0 else 0
        
        ideal_offs_today = math.floor(ideal_offs_today_float)
        if random.random() < (ideal_offs_today_float - ideal_offs_today):
            ideal_offs_today += 1
            
        current_offs_today = sum([1 for s in todays_away if res_df.at[s, day_label] == "休"])
        
        candidates = []
        for s in rem_s:
            rem_off = target_off_days[s] - off_counts[s]
            rem_days_for_s = len(days_labels) - d_idx
            streak = get_streak(s, d_idx)
            
            score = 0
            if streak >= 3: score += 50000 
            if rem_off >= rem_days_for_s: score += 10000 
            
            expected_offs = ((d_idx + 1) / len(days_labels)) * target_off_days[s]
            if off_counts[s] < expected_offs: score += 500
            else: score -= 500
            
            if is_sp_day:
                score += (max(holiday_off_counts.values()) - holiday_off_counts[s]) * 200
            
            candidates.append((score, random.random(), s))
            
        candidates.sort(reverse=True)
        
        for score, rand_val, s in candidates:
            if len(selected_staff) - len(todays_away) <= 2: break 
            
            rem_off = target_off_days[s] - off_counts[s]
            streak = get_streak(s, d_idx)
            
            is_mandatory = (streak >= 3) or (rem_off >= len(days_labels) - d_idx)
            # 強制休みの人以外は、今日の「休み枠（理想人数）」が空いている時だけ休ませる
            is_good_pace = (current_offs_today < ideal_offs_today) and (rem_off > 0)
            
            if is_mandatory or is_good_pace:
                res_df.at[s, day_label] = "休"
                todays_away.append(s)
                off_counts[s] += 1
                current_offs_today += 1
                if is_sp_day: holiday_off_counts[s] += 1

        # C. シフト割り当て
        working = [s for s in selected_staff if res_df.at[s, day_label] == ""]
        random.shuffle(working)
        pool = (earlies + lates) * 2
        
        for s in working:
            prev = res_df.at[s, days_labels[d_idx-1]] if d_idx > 0 else "休"
            assigned = False
            for p in pool:
                if prev in lates and p in earlies: continue
                res_df.at[s, day_label] = p
                pool.remove(p)
                assigned = True
                break
            if not assigned: res_df.at[s, day_label] = "遅(調)"

    st.success("人数バランスが完璧に調整されたシフトが完成しました！")
    
    def style_df(val):
        if val == '休': return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
        if val == '出張': return 'background-color: #e6fffa; color: #006666;'
        if "※" in val: return 'color: #ff0000;' 
        return ''
    
    st.dataframe(res_df.style.applymap(style_df), height=400)
    
    st.subheader("📊 公平性のチェック")
    stats = []
    for s in selected_staff:
        stats.append({
            "スタッフ": s,
            "出張日数": f"{sum(edited_trip.loc[s])}日",
            "休み数（実績/目標）": f"{off_counts[s]}日 / {target_off_days[s]}日",
            "土日祝の休み回数": f"{holiday_off_counts[s]}回"
        })
    st.table(pd.DataFrame(stats))

    csv = res_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 CSV保存", csv, f"shift_{year}_{month}.csv", "text/csv")
