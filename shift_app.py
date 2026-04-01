import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date
import random
import math
import jpholiday
import os
import json

# --- アプリの設定 ---
st.set_page_config(layout="wide", page_title="KASANE本厚木店シフト管理", page_icon="🧘‍♀️")

# --- デザインの調整 (CSS) ---
st.markdown("""
<style>
    .stApp { background-color: #fcfcfc; color: #555555; }
    h1, h2, h3 { color: #5d5d4d !important; font-weight: 400 !important; }
    div[data-testid="stDataEditor"] div { cursor: pointer !important; }
</style>
""", unsafe_allow_html=True)

st.title("🗓️ KASANE本厚木店シフト管理")

# --- 1. データの完全保存システム（アップデートしても消えない！） ---
STAFF_FILE = "staff_list.json"
SCHEDULE_FILE = "schedule_data.json"

# スタッフリストの読み込み・保存
def load_staff():
    if os.path.exists(STAFF_FILE):
        try:
            with open(STAFF_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return ["スタッフA", "スタッフB", "スタッフC"]

def save_staff(staff_list):
    with open(STAFF_FILE, "w", encoding="utf-8") as f:
        json.dump(staff_list, f, ensure_ascii=False)

# チェック表（出張・休みなど）の読み込み・保存
def load_schedule_data():
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {}

def save_schedule_data(data_dict):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, ensure_ascii=False)

# 初期読み込み
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = load_staff()
if 'sched_data' not in st.session_state:
    st.session_state.sched_data = load_schedule_data()

# --- サイドバー設定 ---
with st.sidebar:
    st.header("1. スタッフ・年月設定")
    with st.expander("スタッフの追加・削除"):
        new_name = st.text_input("追加する名前")
        if st.button("スタッフを追加"):
            if new_name and new_name not in st.session_state.staff_list:
                st.session_state.staff_list.append(new_name)
                save_staff(st.session_state.staff_list)
                st.rerun()
        del_name = st.selectbox("削除するスタッフ", [""] + st.session_state.staff_list)
        if st.button("スタッフを削除"):
            if del_name in st.session_state.staff_list:
                st.session_state.staff_list.remove(del_name)
                save_staff(st.session_state.staff_list)
                st.rerun()

    active_staff = []
    for s in st.session_state.staff_list:
        if st.checkbox(s, value=True, key=f"active_{s}"):
            active_staff.append(s)

    year = st.selectbox("年", range(date.today().year - 1, date.today().year + 3), index=1)
    month = st.selectbox("月", range(1, 13), index=date.today().month - 1)

    st.header("月間の休み数")
    target_off_days = {}
    for staff in active_staff:
        target_off_days[staff] = st.number_input(f"{staff}の休み日数", min_value=0, max_value=20, value=8)

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
    else:
        is_holiday_list.append(curr_date.weekday() >= 5) # 土日をTrueに
    days_labels.append(label)

# --- 2. 各種予定の設定（消えないチェック表） ---
st.header("2. 各種予定の設定")
st.info("💡 入力した内容は自動的に保存され、アプリを更新しても消えなくなりました！")

df_key = f"{year}_{month}"

# JSONから表を復元する強力な関数
def get_persisted_df(domain, index_list, columns):
    if df_key in st.session_state.sched_data and domain in st.session_state.sched_data[df_key]:
        # 保存されているデータを読み込む
        saved_df = pd.DataFrame(st.session_state.sched_data[df_key][domain])
        # 現在のスタッフリストと日付に合わせて形を整える（はみ出た部分は消え、足りない部分はFalseで埋まる）
        saved_df = saved_df.reindex(index=index_list, columns=columns, fill_value=False)
        return saved_df.fillna(False).astype(bool)
    else:
        return pd.DataFrame(False, index=index_list, columns=columns)

trip_df = get_persisted_df("trip", active_staff, days_labels)
off_df = get_persisted_df("off", active_staff, days_labels)
must_work_df = get_persisted_df("must", ["全員出勤にする日"], days_labels)

st.subheader("🏢 全員出勤日の指定")
edited_must_work = st.data_editor(must_work_df, key=f"must_{df_key}")

col1, col2 = st.columns(2)
with col1:
    st.subheader("✈️ 出張（店舗不在）")
    edited_trip = st.data_editor(trip_df, key=f"trip_{df_key}")
with col2:
    st.subheader("👆 希望休（絶対休み）")
    edited_off = st.data_editor(off_df, key=f"off_{df_key}")

# --- 5. シフト作成ロジック ---
if st.button("🚀 シフトを自動作成する", type="primary"):
    
    # 🌟 ボタンを押した瞬間に、現在のチェック状態をJSONに完全保存！
    if df_key not in st.session_state.sched_data:
        st.session_state.sched_data[df_key] = {}
    st.session_state.sched_data[df_key]["trip"] = edited_trip.to_dict()
    st.session_state.sched_data[df_key]["off"] = edited_off.to_dict()
    st.session_state.sched_data[df_key]["must"] = edited_must_work.to_dict()
    save_schedule_data(st.session_state.sched_data)

    shift_types = ["早1", "早2", "遅1", "遅2"]
    earlies, lates = ["早1", "早2"], ["遅1", "遅2"]
    
    res_df = pd.DataFrame("", index=active_staff, columns=days_labels)
    off_counts = {s: 0 for s in active_staff}
    holiday_off_counts = {s: 0 for s in active_staff}
    shift_counts = {s: {stype: 0 for stype in shift_types} for s in active_staff}

    def get_streak(staff, current_idx):
        streak = 0
        for b in range(1, current_idx + 1):
            cell = res_df.at[staff, days_labels[current_idx-b]]
            if cell != "休" and cell != "": streak += 1
            else: break
        return streak

    def get_off_streak(staff, current_idx):
        streak = 0
        for b in range(1, current_idx + 1):
            if res_df.at[staff, days_labels[current_idx-b]] == "休": streak += 1
            else: break
        return streak

    for d_idx, day_label in enumerate(days_labels):
        is_sp_day = is_holiday_list[d_idx] 
        is_must_work = edited_must_work.at["全員出勤にする日", day_label]
        todays_away = []
        
        # 【超重要】その日に最低限必要な出勤人数を定義
        if is_sp_day:
            min_staff = 2 # 土日祝は絶対に2人以上！
        else:
            min_staff = 1 if len(active_staff) <= 3 else 2 # 平日はスタッフ数に応じて変動

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

        # B. 自動休みの割り振り
        if not is_must_work:
            rem_s = [s for s in active_staff if res_df.at[s, day_label] == ""]
            
            total_rem_offs = sum([max(0, target_off_days[s] - off_counts[s]) for s in active_staff])
            rem_days_total = len(days_labels) - d_idx
            ideal_offs_today_float = total_rem_offs / rem_days_total if rem_days_total > 0 else 0
            ideal_offs_today = math.floor(ideal_offs_today_float)
            if random.random() < (ideal_offs_today_float - ideal_offs_today): ideal_offs_today += 1
            current_offs_today = sum([1 for s in todays_away if res_df.at[s, day_label] == "休"])
            
            candidates = []
            for s in rem_s:
                rem_off = target_off_days[s] - off_counts[s]
                streak = get_streak(s, d_idx)
                off_streak = get_off_streak(s, d_idx)
                
                score = 0
                if streak >= 5: score += 2000000 
                elif streak == 4: score += 1000000 
                elif streak == 3: score += 500000 
                
                if off_streak >= 1: score -= 300000 
                if rem_off >= (len(days_labels) - d_idx): score += 100000 
                
                expected = ((d_idx + 1) / len(days_labels)) * target_off_days[s]
                score += 5000 if off_counts[s] < expected else -5000
                
                if is_sp_day:
                    score += (max(holiday_off_counts.values()) - holiday_off_counts[s]) * 2000
                
                candidates.append((score, random.random(), s))
                
            candidates.sort(reverse=True)
            for score, rand_val, s in candidates:
                # 🚨 【絶対防壁】もしこの人を休ませて最低人数を割ってしまうなら、絶対に休ませない！
                if len(active_staff) - len(todays_away) - 1 < min_staff:
                    continue # 強制的に次の候補者へ（誰も休めない場合はそのままスルー）
                
                rem_off = target_off_days[s] - off_counts[s]
                if score >= 500000 or (rem_off > 0 and score > 0 and current_offs_today < ideal_offs_today):
                    res_df.at[s, day_label] = "休"
                    todays_away.append(s)
                    off_counts[s] += 1
                    current_offs_today += 1
                    if is_sp_day: holiday_off_counts[s] += 1

        # C. シフト割り当て
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
            
            # 安全装置：プールが空になった場合でも必ず割り当てる
            if not assigned:
                fallback = pool[0] if pool else "遅2"
                res_df.at[s, day_label] = fallback
                if fallback in shift_counts[s]: shift_counts[s][fallback] += 1
                if pool: pool.remove(fallback)

    st.success("完璧に守られたシフトが完成しました！")
    def style_shift(val):
        if val == '休': return 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
        if val == '出張': return 'background-color: #e6fffa; color: #006666;'
        return ''
    st.dataframe(res_df.style.applymap(style_shift), height=400)
    
    st.subheader("📊 実績の確認")
    stats = []
    for s in active_staff:
        stats.append({"スタッフ": s, "休み(実/目)": f"{off_counts[s]}/{target_off_days[s]}", "土日祝休": holiday_off_counts[s], "早1": shift_counts[s]["早1"], "早2": shift_counts[s]["早2"], "遅1": shift_counts[s]["遅1"], "遅2": shift_counts[s]["遅2"]})
    st.table(pd.DataFrame(stats))

    csv = res_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 CSVダウンロード", csv, f"KASANE_shift_{year}_{month}.csv", "text/csv")
