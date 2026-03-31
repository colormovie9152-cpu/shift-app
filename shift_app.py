import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date
import random
import math
import jpholiday
import os

# --- ロゴの設定 ---
logo_image = "logo.jpg" 

# --- アプリの設定（タイトルを本厚木店に変更！） ---
st.set_page_config(layout="wide", page_title="KASANE本厚木店シフト管理", page_icon="🧘‍♀️")

# --- 💡オシャレなデザインのCSS適用 ---
st.markdown("""
<style>
    .stApp { background-color: #fcfcfc; color: #555555; }
    .stHeader {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding-top: 2rem; padding-bottom: 2rem; background-color: #ffffff;
        border-bottom: 1px solid #e6e6e6; margin-bottom: 2rem;
    }
    .stHeader img { max-width: 150px; margin-bottom: 1rem; }
    .stHeader h1 { font-size: 1.8rem; color: #5d5d4d; font-weight: 400; letter-spacing: 0.1rem; }
    .css-1d391kg { background-color: #ffffff; border-right: 1px solid #e6e6e6; padding-top: 2rem; }
    .stHeader h2, .stHeader h3, .stHeader h4, .stHeader h5 { color: #5d5d4d; font-weight: 400; margin-top: 1.5rem; }
    /* チェックボックスを押しやすくする調整 */
    div[data-testid="stDataEditor"] div { cursor: pointer !important; }
</style>
""", unsafe_allow_html=True)

# --- ヘッダー（ロゴとタイトル） ---
st.markdown("<div class='stHeader'>", unsafe_allow_html=True)
if os.path.exists(logo_image):
    st.image(logo_image)
else:
    st.markdown("<p style='color:#ccc; font-size:12px;'>※ここにロゴが表示されます</p>", unsafe_allow_html=True)
st.markdown("<h1>KASANE本厚木店シフト管理</h1></div>", unsafe_allow_html=True)

# --- 1. スタッフ・設定管理 ---
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = ["スタッフA", "スタッフB", "スタッフC"]

with st.sidebar:
    st.header("1. Staff & Month Settings")
    st.subheader("Select staff list")
    
    active_staff = []
    for s in st.session_state.staff_list:
        if st.checkbox(s, value=True, key=f"active_{s}"):
            active_staff.append(s)
            
    with st.expander("Add/Remove Staff"):
        new_staff = st.text_input("Name")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Add"):
                if new_staff and new_staff not in st.session_state.staff_list:
                    st.session_state.staff_list.append(new_staff)
                    st.rerun()
        with c2:
            staff_to_delete = st.selectbox("Staff", [""] + st.session_state.staff_list)
            if st.button("Delete"):
                if staff_to_delete in st.session_state.staff_list:
                    st.session_state.staff_list.remove(staff_to_delete)
                    st.rerun()

    st.header("Date")
    year = st.selectbox("Year", range(date.today().year - 1, date.today().year + 3), index=1)
    month = st.selectbox("Month", range(1, 13), index=date.today().month - 1)

    st.header("Off Days")
    target_off_days = {}
    for staff in active_staff:
        target_off_days[staff] = st.number_input(f"{staff}の休み数", min_value=0, max_value=20, value=8)

# --- カレンダー計算 ---
days_in_month = calendar.monthrange(year, month)[1]
weekday_ja = ["(月)", "(火)", "(水)", "(木)", "(金)", "(土)", "(日)"]
days_labels = [] 
is_holiday_list = [] 

for i in range(1, days_in_month + 1):
    curr_date = date(year, month, i)
    wd = weekday_ja[curr_date.weekday()]
    holiday_name = jpholiday.is_holiday_name(curr_date)
    
    label = f"{i}日{wd}"
    if holiday_name:
        label += f" ※{holiday_name}"
        is_holiday_list.append(True)
    elif curr_date.weekday() >= 5: 
        is_holiday_list.append(True)
    else:
        is_holiday_list.append(False)
    
    days_labels.append(label)

# --- 2. 出張・特別休みの設定 ---
st.header("2. Business Trip & Special Off-Day Settings")
st.info("左が『出張（仕事だけど不在）』、右が『希望休（絶対に休む日）』です。")

df_key = f"{year}_{month}_{''.join(active_staff)}"

if 'trip_df_dict' not in st.session_state:
    st.session_state.trip_df_dict = {}
if 'off_df_dict' not in st.session_state:
    st.session_state.off_df_dict = {}

if df_key not in st.session_state.trip_df_dict:
    st.session_state.trip_df_dict[df_key] = pd.DataFrame(False, index=active_staff, columns=days_labels)
if df_key not in st.session_state.off_df_dict:
    st.session_state.off_df_dict[df_key] = pd.DataFrame(False, index=active_staff, columns=days_labels)

# ★修正ポイント：2回クリックバグを解消！UIの表示のみ行い、即時保存の無限ループを防ぎます。
col_trip, col_off = st.columns(2)
with col_trip:
    st.subheader("✈️ 出張 (Business Trip)")
    edited_trip = st.data_editor(st.session_state.trip_df_dict[df_key], key=f"trip_{df_key}")
with col_off:
    st.subheader("👆 希望休 (Special Off)")
    edited_off = st.data_editor(st.session_state.off_df_dict[df_key], key=f"off_{df_key}")

# --- 5. シフト作成ロジック ---
if st.button("Automatically Create Shift", type="primary"):
    # ★作成ボタンを押した瞬間に、編集内容を保存するように変更！
    st.session_state.trip_df_dict[df_key] = edited_trip
    st.session_state.off_df_dict[df_key] = edited_off

    shift_types = ["早1", "早2", "遅1", "遅2"]
    earlies = ["早1", "早2"]
    lates = ["遅1", "遅2"]
    
    res_df = pd.DataFrame("", index=active_staff, columns=days_labels)
    off_counts = {s: 0 for s in active_staff}
    holiday_off_counts = {s: 0 for s in active_staff}
    shift_counts = {s: {stype: 0 for stype in shift_types} for s in active_staff}

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
        for s in active_staff:
            if edited_trip.at[s, day_label]:
                res_df.at[s, day_label] = "出張"
                todays_away.append(s)
            elif edited_off.at[s, day_label]:
                res_df.at[s, day_label] = "休"
                todays_away.append(s)
                off_counts[s] += 1
                if is_sp_day: holiday_off_counts[s] += 1

        # B. 休み人数の調整とペース配分
        rem_s = [s for s in active_staff if res_df.at[s, day_label] == ""]
        
        total_rem_offs = sum([max(0, target_off_days[s] - off_counts[s]) for s in active_staff])
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
            min_working_staff = 1 if len(active_staff) <= 3 else 2
            if len(active_staff) - len(todays_away) <= min_working_staff: break 
            
            rem_off = target_off_days[s] - off_counts[s]
            streak = get_streak(s, d_idx)
            
            is_mandatory = (streak >= 3) or (rem_off >= len(days_labels) - d_idx)
            is_good_pace = (current_offs_today < ideal_offs_today) and (rem_off > 0)
            
            if is_mandatory or is_good_pace:
                res_df.at[s, day_label] = "休"
                todays_away.append(s)
                off_counts[s] += 1
                current_offs_today += 1
                if is_sp_day: holiday_off_counts[s] += 1

        # C. シフト4種の均等割り当て
        working = [s for s in active_staff if res_df.at[s, day_label] == ""]
        random.shuffle(working)
        pool = shift_types * 2
        
        for s in working:
            prev = res_df.at[s, days_labels[d_idx-1]] if d_idx > 0 else "休"
            available_for_s = sorted(pool, key=lambda p: shift_counts[s][p] + random.random() * 0.1)
            
            assigned = False
            for p in available_for_s:
                if prev in lates and p in earlies: continue
                res_df.at[s, day_label] = p
                shift_counts[s][p] += 1 
                pool.remove(p) 
                assigned = True
                break
                
            if not assigned: 
                fallback = pool[0] if pool else "遅2"
                res_df.at[s, day_label] = fallback
                if fallback in shift_counts[s]: shift_counts[s][fallback] += 1
                if pool: pool.remove(fallback)

    st.success("完璧なシフトが完成しました！")
    
    def style_shift(val):
        color = ''
        if val == '休': color = '#ffcccc' 
        elif val == '出張': color = '#ccffcc' 
        return f'background-color: {color}'

    if len(active_staff) <= 3:
        st.info("💡 この月はスタッフ数が少ないため『最低1人出勤』のルールを適用しました。")
        
    st.dataframe(res_df.style.applymap(style_shift), height=400)
    
    st.subheader("📊 公平性のチェック（シフト4種の均等化）")
    stats = []
    for s in active_staff:
        trip_days = sum(edited_trip.loc[s])
        stats.append({
            "スタッフ": s,
            "出張日数": f"{trip_days}日",
            "休み（実績/目標）": f"{off_counts[s]} / {target_off_days[s]}",
            "土日祝休み": f"{holiday_off_counts[s]}回",
            "早1": shift_counts[s]["早1"],
            "早2": shift_counts[s]["早2"],
            "遅1": shift_counts[s]["遅1"],
            "遅2": shift_counts[s]["遅2"]
        })
    st.table(pd.DataFrame(stats))

    csv = res_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 ダウンロード", csv, f"KASANE_shift_{year}_{month}.csv", "text/csv")
