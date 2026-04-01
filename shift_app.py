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
        st.success("👍 チェック内容を記憶しました！")

with col_btn2:
    if st.button("🗑️ 記憶をリセット（白紙に戻す）", use_container_width=True):
        if df_key in st.session_state.sched_data:
            del st.session_state.sched_data[df_key]
            save_schedule_data(st.session_state.sched_data)
        if f"temp_shift_{df_key}" in st.session_state:
            del st.session_state[f"temp_shift_{df_key}"]
        st.rerun()

with col_btn3:
    manager_staff = st.selectbox("💪 どうしても無理な時に「4連勤」を引き受ける人", ["指定なし"] + active_staff)
    create_clicked = st.button("🚀 シフトを自動作成する", type="primary", use_container_width=True)

# --- 5. 本物のAIエンジン（スマートスタート＆店長集中版） ---
if create_clicked:
    num_days = len(days_labels)
    
    fixed_manual = {s: [False]*num_days for s in active_staff}
    for s in active_staff:
        for d in range(num_days):
            if edited_trip.at[s, days_labels[d]]: fixed_manual[s][d] = True
            elif edited_off.at[s, days_labels[d]]: fixed_manual[s][d] = True

    must_work_arr = [edited_must_work.at["全員出勤にする日", days_labels[d]] for d in range(num_days)]
    is_sp_arr = is_holiday_list
    min_s_arr = [2 if is_sp_arr[d] else (1 if len(active_staff) <= 3 else 2) for d in range(num_days)]

    def get_penalty(sched):
        penalty = 0
        
        # 【絶対ルール1】お店の最低人数
        for d in range(num_days):
            working = sum(1 for s in active_staff if sched[s][d] == "") 
            if working < min_s_arr[d]: 
                penalty += (min_s_arr[d] - working) * 100000000 
            if must_work_arr[d]:
                non_trip = sum(1 for s in active_staff if sched[s][d] != "出張")
                if working < non_trip: penalty += (non_trip - working) * 100000000

        # 【連勤・連休の超厳格チェック】
        for s in active_staff:
            current_work = 0
            current_off = 0
            four_day_streaks = 0

            for d in range(num_days):
                val = sched[s][d]
                if val in ["休", "出張"]:
                    if current_work == 4:
                        four_day_streaks += 1
                    elif current_work >= 5:
                        penalty += current_work * 10000000 # 5連勤絶対禁止
                    
                    if current_work == 1:
                        penalty += 5000 # 1日だけの出勤も少し嫌がる（2~3連勤推奨）
                    
                    current_work = 0
                    if val == "休": current_off += 1
                    else: current_off = 0 
                else: 
                    if current_off >= 3:
                        penalty += current_off * 1000000 # 3連休絶対禁止
                    current_off = 0
                    current_work += 1

            if current_work == 4:
                four_day_streaks += 1
            elif current_work >= 5:
                penalty += current_work * 10000000
            if current_work == 1:
                penalty += 5000
            if current_off >= 3:
                penalty += current_off * 1000000

            # 🌟 4連勤の「徹底排除＆店長なすりつけ」ロジック 🌟
            if s == manager_staff:
                pass # 店長は4連勤何回でもペナルティ0！AIは喜んで店長に押し付ける
            else:
                if four_day_streaks > 0:
                    # 一般スタッフは1回目から「100万点」の超特大ペナルティ！
                    # （これにより、AIは意地でも一般スタッフの4連勤を崩しにかかる）
                    penalty += four_day_streaks * 1000000

        return penalty

    best_overall_schedule = None
    best_overall_penalty = float('inf')

    with st.spinner('AIが「全員を等間隔の綺麗なシフト」で配置し、店長へ微調整を行っています...（約5秒）'):
        for attempt in range(5): 
            if best_overall_penalty == 0: break 
            
            # 🌟🌟 根本的改善：最初から「等間隔の美しいシフト」を作る！ 🌟🌟
            current_schedule = {s: [""] * num_days for s in active_staff}
            for s in active_staff:
                for d in range(num_days):
                    if edited_trip.at[s, days_labels[d]]: current_schedule[s][d] = "出張"
                    elif edited_off.at[s, days_labels[d]]: current_schedule[s][d] = "休"
                
                current_offs = sum(1 for d in range(num_days) if current_schedule[s][d] == "休")
                needed_offs = target_off_days[s] - current_offs
                empty_days = [d for d in range(num_days) if current_schedule[s][d] == ""]
                
                if needed_offs > 0:
                    # ランダムではなく、数学的に等間隔に配置して「2〜3連勤」を最初から作る！
                    step = len(empty_days) / needed_offs
                    for i in range(needed_offs):
                        idx = int(i * step + step / 2) # 中間地点を狙う
                        if idx >= len(empty_days): idx = len(empty_days) - 1
                        current_schedule[s][empty_days[idx]] = "休"
            
            local_penalty = get_penalty(current_schedule)
            local_best_schedule = {s: current_schedule[s][:] for s in active_staff}
            local_best_penalty = local_penalty

            T = 100.0 
            cooling_rate = 0.9995 

            for i in range(40000): 
                if local_best_penalty == 0: break 

                mutation = random.random()
                
                # 休み日数は絶対に変わらないようにカレンダー内で日を交換する
                if mutation < 0.5:
                    s1 = random.choice(active_staff)
                    d1, d2 = random.sample(range(num_days), 2)
                    
                    if fixed_manual[s1][d1] or fixed_manual[s1][d2]: continue
                    if current_schedule[s1][d1] == current_schedule[s1][d2]: continue
                    
                    current_schedule[s1][d1], current_schedule[s1][d2] = current_schedule[s1][d2], current_schedule[s1][d1]
                    new_penalty = get_penalty(current_schedule)
                    
                    if new_penalty < local_penalty or random.random() < math.exp((local_penalty - new_penalty) / max(T, 0.1)):
                        local_penalty = new_penalty
                        if new_penalty < local_best_penalty:
                            local_best_penalty = new_penalty
                            local_best_schedule = {s: current_schedule[s][:] for s in active_staff}
                    else:
                        current_schedule[s1][d1], current_schedule[s1][d2] = current_schedule[s1][d2], current_schedule[s1][d1] 
                
                else:
                    if len(active_staff) < 2: continue
                    s1, s2 = random.sample(active_staff, 2)
                    d1, d2 = random.sample(range(num_days), 2)
                    
                    if fixed_manual[s1][d1] or fixed_manual[s1][d2] or fixed_manual[s2][d1] or fixed_manual[s2][d2]: continue
                    
                    v_s1_d1, v_s1_d2 = current_schedule[s1][d1], current_schedule[s1][d2]
                    v_s2_d1, v_s2_d2 = current_schedule[s2][d1], current_schedule[s2][d2]
                    
                    if (v_s1_d1 == "休" and v_s2_d1 == "" and v_s1_d2 == "" and v_s2_d2 == "休") or \
                       (v_s1_d1 == "" and v_s2_d1 == "休" and v_s1_d2 == "休" and v_s2_d2 == ""):
                       
                       current_schedule[s1][d1], current_schedule[s2][d1] = current_schedule[s2][d1], current_schedule[s1][d1]
                       current_schedule[s1][d2], current_schedule[s2][d2] = current_schedule[s2][d2], current_schedule[s1][d2]
                       
                       new_penalty = get_penalty(current_schedule)
                       if new_penalty < local_penalty or random.random() < math.exp((local_penalty - new_penalty) / max(T, 0.1)):
                           local_penalty = new_penalty
                           if new_penalty < local_best_penalty:
                               local_best_penalty = new_penalty
                               local_best_schedule = {s: current_schedule[s][:] for s in active_staff}
                       else:
                           current_schedule[s1][d1], current_schedule[s2][d1] = current_schedule[s2][d1], current_schedule[s1][d1]
                           current_schedule[s1][d2], current_schedule[s2][d2] = current_schedule[s2][d2], current_schedule[s1][d2]

                T *= cooling_rate
                
            if local_best_penalty < best_overall_penalty:
                best_overall_penalty = local_best_penalty
                best_overall_schedule = {s: local_best_schedule[s][:] for s in active_staff}

    # 早番・遅番の割り振り
    res_df = pd.DataFrame.from_dict(best_overall_schedule, orient='index', columns=days_labels)
    
    shift_types = ["早1", "早2", "遅1", "遅2"]
    earlies, lates = ["早1", "早2"], ["遅1", "遅2"]
    shift_counts = {s: {stype: 0 for stype in shift_types} for s in active_staff}

    for d_idx, day_label in enumerate(days_labels):
        working_staff = [s for s in active_staff if res_df.at[s, day_label] == ""]
        random.shuffle(working_staff)
        pool = shift_types * 3 
        
        for s in working_staff:
            prev = res_df.at[s, days_labels[d_idx-1]] if d_idx > 0 else "休"
            available = sorted(pool, key=lambda p: shift_counts[s][p] + random.random() * 0.1)
            
            assigned = False
            for p in available:
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

    st.session_state[f"temp_shift_{df_key}"] = res_df.to_dict()
    
    if manager_staff != "指定なし":
        m_streak = 0
        m_fours = 0
        for d in days_labels:
            if best_overall_schedule[manager_staff][days_labels.index(d)] in ["休", "出張"]:
                if m_streak == 4: m_fours += 1
                m_streak = 0
            else:
                m_streak += 1
        if m_streak == 4: m_fours += 1
        
        if m_fours >= 1:
            st.warning(f"⚠️ 他のスタッフの連勤を防ぐため、指定通り {manager_staff} さんに4連勤を【{m_fours}回】引き受けてもらいました！")

# ==========================================
# 🌟 完成したシフトの表示＆微調整（色付き）
# ==========================================
if f"temp_shift_{df_key}" in st.session_state:
    st.success("2〜3連勤をベースとした、最もバランスの良いシフトが完成しました！")
    
    def style_shift(val):
        val_str = str(val)
        if val_str == '休': return 'background-color: #ffb6c1; color: #555555; font-weight: bold;'
        if val_str == '出張': return 'background-color: #e0ffff; color: #555555;'
        if '早' in val_str: return 'background-color: #fffac8; color: #555555;'
        if '遅' in val_str: return 'background-color: #d0ebff; color: #555555;'
        return ''
    
    temp_shift_df = pd.DataFrame(st.session_state[f"temp_shift_{df_key}"])
    temp_shift_df = temp_shift_df.reindex(index=active_staff, columns=days_labels, fill_value="")
    
    st.subheader("👀 シフト確認用（完全色付きマップ）")
    st.write("※休み(ピンク)・早番(黄)・遅番(青)でマスの色を分けています！")
    
    colored_map_area = st.empty()

    st.subheader("✏️ シフト微調整用（ここで直接書き換えできます）")
    
    edited_shift = st.data_editor(
        temp_shift_df,
        key=f"temp_shift_editor_{df_key}",
        height=300
    )
    
    if hasattr(edited_shift.style, 'map'):
        styled_df = edited_shift.style.map(style_shift)
    else:
        styled_df = edited_shift.style.applymap(style_shift)
        
    colored_map_area.dataframe(styled_df, height=300, use_container_width=True)
    
    st.subheader("📊 最終実績の確認（微調整も反映されます）")
    stats = []
    for s in active_staff:
        off_c = sum(edited_shift.loc[s] == "休")
        trip_c = sum(edited_shift.loc[s] == "出張")
        hol_off_c = sum(1 for d_idx, day_label in enumerate(days_labels) if is_holiday_list[d_idx] and edited_shift.at[s, day_label] == "休")
                
        e1 = sum(edited_shift.loc[s] == "早1")
        e2 = sum(edited_shift.loc[s] == "早2")
        l1 = sum(edited_shift.loc[s] == "遅1")
        l2 = sum(edited_shift.loc[s] == "遅2")

        streak = 0
        four_streaks = 0
        five_streaks = 0
        for d in days_labels:
            if edited_shift.at[s, d] in ["休", "出張"]:
                if streak == 4: four_streaks += 1
                elif streak >= 5: five_streaks += 1
                streak = 0
            else:
                streak += 1
        if streak == 4: four_streaks += 1
        elif streak >= 5: five_streaks += 1

        stats.append({
            "スタッフ": s, 
            "休み(実/目)": f"{off_c}/{target_off_days[s]}", 
            "土日祝休": hol_off_c, 
            "早1": e1, "早2": e2, "遅1": l1, "遅2": l2,
            "4連勤": f"{four_streaks}回",
            "5連勤以上": f"{five_streaks}回"
        })
        
    st.table(pd.DataFrame(stats))

    csv = edited_shift.to_csv().encode('utf_8_sig')
    st.download_button("📥 完成したシフトをダウンロード", csv, f"KASANE_shift_{year}_{month}.csv", "text/csv")
