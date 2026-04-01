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

# --- 1. データの保存システム ---
STAFF_FILE = "staff_list.json"
SCHEDULE_FILE = "schedule_data.json"

# 🌟🌟🌟 【絶対に消えない初期メンバー設定】 🌟🌟🌟
# ここを実際のスタッフの名前に書き換えて保存してください。
DEFAULT_STAFF = [
    "石水マリア", 
    "スタッフB", 
    "スタッフC", 
    "スタッフD", 
    "スタッフE"
]

def load_staff():
    if os.path.exists(STAFF_FILE):
        try:
            with open(STAFF_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return DEFAULT_STAFF.copy()

def save_staff(staff_list):
    with open(STAFF_FILE, "w", encoding="utf-8") as f:
        json.dump(staff_list, f, ensure_ascii=False)

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

if 'staff_list' not in st.session_state:
    st.session_state.staff_list = load_staff()
if 'sched_data' not in st.session_state:
    st.session_state.sched_data = load_schedule_data()

# --- 🌟 新機能：バックアップと復元 ---
with st.sidebar:
    st.header("💾 設定のバックアップと復元")
    st.write("サーバーのリセットでチェックが消えても、これがあれば一瞬で復元できます。")
    
    # ダウンロード
    all_data = {
        "staff": st.session_state.staff_list,
        "sched": st.session_state.sched_data
    }
    json_str = json.dumps(all_data, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 今の設定をファイルに保存",
        data=json_str,
        file_name=f"KASANE_settings_backup.json",
        mime="application/json",
        use_container_width=True
    )

    # アップロード
    uploaded_file = st.file_uploader("📤 保存した設定ファイルを読み込む", type="json")
    if uploaded_file is not None:
        try:
            backup = json.load(uploaded_file)
            st.session_state.staff_list = backup["staff"]
            st.session_state.sched_data = backup["sched"]
            save_staff(st.session_state.staff_list)
            save_schedule_data(st.session_state.sched_data)
            st.success("✅ 設定を復元しました！ページを更新してください。")
            if st.button("今すぐ反映（リロード）"):
                st.rerun()
        except:
            st.error("ファイルが正しくありません。")

    st.markdown("---")
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
        is_holiday_list.append(curr_date.weekday() >= 5) 
    days_labels.append(label)

# --- 2. 各種予定の設定 ---
st.header("2. 各種予定の設定")

df_key = f"{year}_{month}"

def get_persisted_df(domain, index_list, columns):
    if df_key in st.session_state.sched_data and domain in st.session_state.sched_data[df_key]:
        saved_df = pd.DataFrame(st.session_state.sched_data[df_key][domain])
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
    st.subheader("✈️ 出張（※連勤はリセットされます）")
    edited_trip = st.data_editor(trip_df, key=f"trip_{df_key}")
with col2:
    st.subheader("👆 希望休（絶対休み）")
    edited_off = st.data_editor(off_df, key=f"off_{df_key}")

# ==========================================
# 🌟 記憶・リセット・作成の3連ボタン
# ==========================================
st.markdown("---")
st.subheader("💾 予定の記憶とシフト作成")

col_btn1, col_btn2, col_btn3 = st.columns(3)

with col_btn1:
    if st.button("💾 今のチェックを記憶する", use_container_width=True):
        if df_key not in st.session_state.sched_data:
            st.session_state.sched_data[df_key] = {}
        st.session_state.sched_data[df_key]["trip"] = edited_trip.to_dict()
        st.session_state.sched_data[df_key]["off"] = edited_off.to_dict()
        st.session_state.sched_data[df_key]["must"] = edited_must_work.to_dict()
        save_schedule_data(st.session_state.sched_data)
        st.success("👍 チェック内容を一時記憶しました！確実に残すには左の『ファイルに保存』も使ってください。")

with col_btn2:
    if st.button("🗑️ 記憶をリセット（白紙に戻す）", use_container_width=True):
        if df_key in st.session_state.sched_data:
            del st.session_state.sched_data[df_key]
            save_schedule_data(st.session_state.sched_data)
        if f"temp_shift_{df_key}" in st.session_state:
            del st.session_state[f"temp_shift_{df_key}"]
        st.rerun()

with col_btn3:
    manager_staff = st.selectbox("💪 基本的に4連勤を引き受ける人（救世主）", ["指定なし"] + active_staff)
    create_clicked = st.button("🚀 シフトを自動作成する", type="primary", use_container_width=True)

# --- 5. 本物のAIエンジン（平等強制版） ---
if create_clicked:
    num_days = len(days_labels)
    schedule = {s: [""] * num_days for s in active_staff}
    fixed_manual = {s: [False]*num_days for s in active_staff}
    for s in active_staff:
        for d in range(num_days):
            if edited_trip.at[s, days_labels[d]]: 
                schedule[s][d] = "出張"
                fixed_manual[s][d] = True
            elif edited_off.at[s, days_labels[d]]: 
                schedule[s][d] = "休"
                fixed_manual[s][d] = True

    for s in active_staff:
        current_offs = sum(1 for d in range(num_days) if schedule[s][d] == "休")
        needed_offs = target_off_days[s] - current_offs
        empty_days = [d for d in range(num_days) if schedule[s][d] == ""]
        if needed_offs > 0:
            for d in random.sample(empty_days, min(needed_offs, len(empty_days))):
                schedule[s][d] = "休"

    must_work_arr = [edited_must_work.at["全員出勤にする日", days_labels[d]] for d in range(num_days)]
    is_sp_arr = is_holiday_list
    min_s_arr = [2 if is_sp_arr[d] else (1 if len(active_staff) <= 3 else 2) for d in range(num_days)]

    def get_penalty(sched):
        penalty = 0
        for d in range(num_days):
            working = sum(1 for s in active_staff if sched[s][d] == "") 
            if working < min_s_arr[d]: penalty += (min_s_arr[d] - working) * 10000000000 
            if must_work_arr[d]:
                non_trip = sum(1 for s in active_staff if sched[s][d] != "出張")
                if working < non_trip: penalty += (non_trip - working) * 10000000000

        normal_fours = []
        for s in active_staff:
            current_work, current_off, four_streaks = 0, 0, 0
            for d in range(num_days):
                val = sched[s][d]
                if val in ["休", "出張"]:
                    if current_work == 4: four_streaks += 1
                    elif current_work >= 5: penalty += 10000000000
                    current_work = 0
                    if val == "休": current_off += 1
                    else: current_off = 0
                else:
                    if current_off >= 3: penalty += 10000000000
                    current_off, current_work = 0, current_work + 1
            if current_work == 4: four_streaks += 1
            elif current_work >= 5: penalty += 10000000000
            if current_off >= 3: penalty += 10000000000

            if s != manager_staff:
                normal_fours.append(four_streaks)
            else:
                # 指定した人の4連勤はむしろ歓迎（ペナルティなし）
                pass

        if normal_fours:
            # 🌟 平等ルール：一般スタッフ間の回数差は絶対許さない
            penalty += (max(normal_fours) - min(normal_fours)) * 1000000000
            # 指定外に4連勤があること自体を嫌がるようにし、店長へ誘導する
            penalty += sum(normal_fours) * 100000 

        return penalty

    best_overall_schedule = None
    best_overall_penalty = float('inf')

    with st.spinner('AIが計算中...'):
        for attempt in range(5):
            if best_overall_penalty == 0: break
            current_sched = {s: schedule[s][:] for s in active_staff}
            curr_p = get_penalty(current_sched)
            local_best_s = {s: current_sched[s][:] for s in active_staff}
            local_best_p = curr_p
            T = 100.0
            for i in range(25000):
                if local_best_p == 0: break
                s1 = random.choice(active_staff)
                s1_offs = [d for d in range(num_days) if current_sched[s1][d] == "休" and not fixed_manual[s1][d]]
                s1_works = [d for d in range(num_days) if current_sched[s1][d] == "" and not fixed_manual[s1][d]]
                if s1_offs and s1_works:
                    d1, d2 = random.choice(s1_offs), random.choice(s1_works)
                    current_sched[s1][d1], current_sched[s1][d2] = "", "休"
                    new_p = get_penalty(current_sched)
                    if new_p <= curr_p or random.random() < math.exp((curr_p - new_p) / max(T, 0.1)):
                        curr_p = new_p
                        if new_p < local_best_p:
                            local_best_p, local_best_s = new_p, {s: current_sched[s][:] for s in active_staff}
                    else:
                        current_sched[s1][d1], current_sched[s1][d2] = "休", ""
                T *= 0.9995
            if local_best_p < best_overall_penalty:
                best_overall_penalty, best_overall_schedule = local_best_p, local_best_s

    res_df = pd.DataFrame.from_dict(best_overall_schedule, orient='index', columns=days_labels)
    # 早番・遅番割り振り
    shift_types = ["早1", "早2", "遅1", "遅2"]
    shift_counts = {s: {stype: 0 for stype in shift_types} for s in active_staff}
    for d_idx, day_label in enumerate(days_labels):
        working = [s for s in active_staff if res_df.at[s, day_label] == ""]
        random.shuffle(working)
        pool = shift_types * 3
        for s in working:
            prev = res_df.at[s, days_labels[d_idx-1]] if d_idx > 0 else "休"
            available = sorted(pool, key=lambda p: shift_counts[s][p] + random.random() * 0.1)
            assigned = False
            for p in available:
                if prev in ["遅1", "遅2"] and p in ["早1", "早2"]: continue
                res_df.at[s, day_label], assigned = p, True
                shift_counts[s][p] += 1
                pool.remove(p)
                break
            if not assigned:
                res_df.at[s, day_label] = pool[0] if pool else "遅2"

    st.session_state[f"temp_shift_{df_key}"] = res_df.to_dict()
    st.session_state[f"best_penalty_{df_key}"] = best_overall_penalty

# ==========================================
# 🌟 表示エリア
# ==========================================
if f"temp_shift_{df_key}" in st.session_state:
    def style_shift(val):
        if val == '休': return 'background-color: #ffb6c1; color: #555555; font-weight: bold;'
        if val == '出張': return 'background-color: #e0ffff; color: #555555;'
        if '早' in str(val): return 'background-color: #fffac8; color: #555555;'
        if '遅' in str(val): return 'background-color: #d0ebff; color: #555555;'
        return ''
    
    temp_shift_df = pd.DataFrame(st.session_state[f"temp_shift_{df_key}"]).reindex(index=active_staff, columns=days_labels, fill_value="")
    
    # メッセージ判定
    m_fours, normal_fours_list = 0, []
    for s in active_staff:
        streak, fours = 0, 0
        for d in days_labels:
            if temp_shift_df.at[s, d] in ["休", "出張"]:
                if streak == 4: fours += 1
                streak = 0
            else: streak += 1
        if streak == 4: fours += 1
        if s == manager_staff: m_fours = fours
        else: normal_fours_list.append(fours)

    best_p = st.session_state.get(f"best_penalty_{df_key}", 0)
    if best_p >= 100000000: st.error("🚨 ルールを守りきれませんでした。希望休を調整してください。")
    elif sum(normal_fours_list) > 0: st.warning(f"⚠️ 一般スタッフも全員平等に {normal_fours_list[0]}回 4連勤となりました。")
    elif m_fours > 0: st.info(f"💡 {manager_staff}さんが4連勤を引き受けてくれました！")
    else: st.success("✨ 全員4連勤なしの完璧なシフトです！")

    st.subheader("👀 確認用（色付き）")
    st.dataframe(temp_shift_df.style.applymap(style_shift), height=300, use_container_width=True)
    
    st.subheader("✏️ 微調整用（直接編集OK）")
    edited_shift = st.data_editor(temp_shift_df, key=f"temp_shift_editor_{df_key}", height=300)
    
    st.subheader("📊 最終実績")
    stats = []
    for s in active_staff:
        streak, f4, f5 = 0, 0, 0
        for d in days_labels:
            if edited_shift.at[s, d] in ["休", "出張"]:
                if streak == 4: f4 += 1
                elif streak >= 5: f5 += 1
                streak = 0
            else: streak += 1
        if streak == 4: f4 += 1
        elif streak >= 5: f5 += 1
        stats.append({
            "スタッフ": s, "休み(実/目)": f"{sum(edited_shift.loc[s]=='休')}/{target_off_days[s]}",
            "4連勤": f"{f4}回", "5連勤以上": f"{f5}回"
        })
    st.table(pd.DataFrame(stats))
    st.download_button("📥 シフトをCSVで保存", edited_shift.to_csv().encode('utf_8_sig'), f"shift_{year}_{month}.csv", "text/csv")
