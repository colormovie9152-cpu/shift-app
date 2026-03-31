import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date
import random
import math
import jpholiday
import os # 🌟エラーを防ぐための新しい部品を追加！

# --- ロゴの設定 ---
# GitHubにアップロードする画像の名前に合わせます
logo_image = "logo.jpg" 

# --- アプリの設定 ---
st.set_page_config(
    layout="wide",
    page_title="PILATES KASANE - Schedule Management",
    page_icon="🧘‍♀️"
)

# --- 💡オシャレなデザインのCSS適用 ---
st.markdown("""
<style>
    .stApp {
        background-color: #fcfcfc;
        color: #555555;
    }
    .stHeader {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding-top: 2rem;
        padding-bottom: 2rem;
        background-color: #ffffff;
        border-bottom: 1px solid #e6e6e6;
        margin-bottom: 2rem;
    }
    .stHeader img {
        max-width: 150px;
        margin-bottom: 1rem;
    }
    .stHeader h1 {
        font-size: 1.8rem;
        color: #5d5d4d;
        font-weight: 400;
        letter-spacing: 0.1rem;
    }
    .css-1d391kg {
        background-color: #ffffff;
        border-right: 1px solid #e6e6e6;
        padding-top: 2rem;
    }
    .stHeader h2, .stHeader h3, .stHeader h4, .stHeader h5 {
        color: #5d5d4d;
        font-weight: 400;
        margin-top: 1.5rem;
    }
    div[data-testid="stDataEditor"] div {
        cursor: pointer !important;
    }
</style>
""", unsafe_allow_html=True)

# --- ヘッダー（ロゴとタイトル） ---
st.markdown("<div class='stHeader'>", unsafe_allow_html=True)
# 🌟画像がGitHubにあるか確認してから表示する安全設計に修正！
if os.path.exists(logo_image):
    st.image(logo_image)
else:
    st.markdown("<p style='color:#ccc; font-size:12px;'>※ここにロゴが表示されます（GitHubに logo.jpg をアップロードしてください）</p>", unsafe_allow_html=True)
st.markdown("<h1>Schedule Management</h1></div>", unsafe_allow_html=True)

# --- 1. スタッフ・設定管理 ---
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = ["スタッフA", "スタッフB", "スタッフC"]

with st.sidebar:
    st.header("1. Staff & Month Settings")
    st.subheader("Select staff list")
    
    if 'holiday_data' not in st.session_state:
        st.session_state.holiday_data = {}

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
    extra_off_days = {}
    for staff in active_staff:
        extra_off_days[staff] = st.number_input(f"{staff}の追加休み", min_value=0, max_value=20, value=8)

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
st.info("出張は『仕事だけど不在の日』、希望休は『絶対に休む日』としてチェックしてください。")

df_key = f"{year}_{month}_{''.join(active_staff)}"
if 'holiday_df_raw' not in st.session_state:
    st.session_state.holiday_df_raw = {}

if df_key not in st.session_state.holiday_df_raw:
    st.session_state.holiday_df_raw[df_key] = pd.DataFrame(False, index=active_staff, columns=days_labels)

edited_raw = st.data_editor(st.session_state.holiday_df_raw[df_key], key=f"editor_{df_key}")
st.session_state.holiday_df_raw[df_key] = edited_raw

# --- 5. シフト作成ロジック ---
if st.button("Automatically Create Shift (Minimum 1 Staff Check Enabled)", type="primary"):
    earlies = ["早1", "早2"]
    lates = ["遅1", "遅2"]
    
    res_df = pd.DataFrame("", index=active_staff, columns=days_labels)
    off_counts = {s: 0 for s in active_staff}
    weekend_off_counts = {s: 0 for s in active_staff}
    total_off_target = {}
    
    for s in active_staff:
        fixed_count = sum(edited_raw.loc[s])
        total_off_target[s] = fixed_count + extra_off_days[s]

    for d_idx, day_label in enumerate(days_labels):
        is_sp_day = is_holiday_list[d_idx] 
        todays_fixed_off = []
        
        for s in active_staff:
            if edited_raw.at[s, day_label]:
                todays_fixed_off.append(s)
                off_counts[s] += 1
                if is_sp_day: weekend_off_counts[s] += 1
                res_df.at[s, day_label] = "休" 

        rem_s = [s for s in active_staff if s not in todays_fixed_off]
        random.shuffle(rem_s)
        rem_s.sort(key=lambda s: (weekend_off_counts[s] if is_sp_day else 0, off_counts[s] / total_off_target[s] if total_off_target[s] > 0 else 1.0))
        
        for s in rem_s:
            if off_counts[s] < total_off_target[s]:
                current_away = len(todays_fixed_off) + 1 + sum(edited_raw.loc[:, day_label])
                
                # スタッフが3人以下なら最低1人、それ以上なら最低2人を死守
                min_working_staff = 1 if len(active_staff) <= 3 else 2

                if len(active_staff) - current_away >= min_working_staff:
                    todays_fixed_off.append(s)
                    off_counts[s] += 1
                    if is_sp_day: weekend_off_counts[s] += 1
                    res_df.at[s, day_label] = "休"

        working = [s for s in active_staff if s not in todays_fixed_off]
        random.shuffle(working)
        pool = earlies + lates + earlies + lates
        
        for s in working:
            prev = res_df.at[s, days_labels[d_idx-1]] if d_idx > 0 else "休"
            assigned = False
            for p in pool:
                if prev in lates and p in earlies: continue
                res_df.at[s, day_label] = p
                pool.remove(p) 
                assigned = True
                break
                
            if not assigned: res_df.at[s, day_label] = "調整"

    st.success("間隔が調整された綺麗なシフトが完成しました！")
    
    def style_shift(val):
        color = ''
        if val == '休': color = '#ffcccc' 
        elif val == '出張': color = '#ccffcc' 
        elif val == '調整': color = '#ffffcc' 
        return f'background-color: {color}'

    st.info("💡 この月はスタッフ数が少ないため、現場崩壊を防ぐために『最低1人出勤（ Minimum 1 Staff Check Enabled ）』のルールを適用しました。")
    st.dataframe(res_df.style.applymap(style_shift), height=400)
    
    st.subheader("📊 公平性のチェック")
    stats = []
    for s in active_staff:
        trip_days = sum(edited_raw.loc[s])
        stats.append({
            "スタッフ": s,
            "出張日数": f"{trip_days}日間",
            "実際の休み数": f"{off_counts[s]}日間 / 目標{total_off_target[s]}日",
            "不在の合計": f"{trip_days + off_counts[s]}日間",
            "土日祝祝日休み": f"{weekend_off_counts[s]}回"
        })
    st.table(pd.DataFrame(stats))

    csv = res_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 ダウンロード", csv, f"pilates_shift_{year}_{month}.csv", "text/csv")
