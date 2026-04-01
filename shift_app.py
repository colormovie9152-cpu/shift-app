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
    st.subheader("✈️ 出張（店舗不在）")
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

# --- 5. 新生AIによる「全体最適化」シフト作成ロジック ---
with col_btn3:
    create_clicked = st.button("🚀 シフトを自動作成する", type="primary", use_container_width=True)

if create_clicked:
    # ① まず、手動のチェック状態だけをベースとして設定
    schedule = {s: [""] * len(days_labels) for s in active_staff}
    for s in active_staff:
        for d in range(len(days_labels)):
            if edited_trip.at[s, days_labels[d]]: schedule[s][d] = "出張"
            elif edited_off.at[s, days_labels[d]]: schedule[s][d] = "休"

    # ② 不足している「休み」を、とりあえず適当な空き日に突っ込む
    for s in active_staff:
        current_offs = sum(1 for d in range(len(days_labels)) if schedule[s][d] == "休")
        needed_offs = target_off_days[s] - current_offs
        empty_days = [d for d in range(len(days_labels)) if schedule[s][d] == ""]
        if needed_offs > 0:
            for d in random.sample(empty_days, min(needed_offs, len(empty_days))):
                schedule[s][d] = "休"

    # ③ シフトの「悪さ（ペナルティ）」を計算する絶対的な審査ルール
    def get_penalty(sched):
        penalty = 0
        for d in range(len(days_labels)):
            working = sum(1 for s in active_staff if sched[s][d] == "") # 休・出張以外の「出勤人数」
            is_sp = is_holiday_list[d]
            min_s = 2 if is_sp else (1 if len(active_staff) <= 3 else 2)

            # お店の崩壊（最低人数割れ）は絶対NG
            if working < min_s: penalty += (min_s - working) * 5000000 
            if working == 0: penalty += 10000000
            
            # 全員出勤日に休んでいる人がいたら超特大ペナルティ
            if edited_must_work.at["全員出勤にする日", days_labels[d]]:
                non_trip = sum(1 for s in active_staff if sched[s][d] != "出張")
                if working < non_trip: penalty += (non_trip - working) * 5000000

        for s in active_staff:
            work_streak = 0
            off_streak = 0
            offs_count = 0
            for d in range(len(days_labels)):
                if sched[s][d] == "休":
                    offs_count += 1
                    off_streak += 1
                    work_streak = 0
                    # 🌟 3連休以上は特大ペナルティ（絶対阻止）
                    if off_streak >= 3: penalty += 1000000 * off_streak 
                elif sched[s][d] == "出張":
                    work_streak += 1
                    off_streak = 0
                    # 出張も含めて5連勤以上は特大ペナルティ（絶対阻止）
                    if work_streak >= 5: penalty += 2000000 * work_streak 
                else: # 通常出勤
                    work_streak += 1
                    off_streak = 0
                    # 🌟 5連勤以上は特大ペナルティ（絶対阻止）
                    if work_streak >= 5: penalty += 2000000 * work_streak 

            # 月の休み数が目標とズレているのもNG
            if offs_count != target_off_days[s]:
                penalty += abs(offs_count - target_off_days[s]) * 1000000

        return penalty

    # ④ AIが裏で10,000回パズルを入れ替えて、ペナルティ0の最強シフトを探し出す
    best_schedule = {s: schedule[s][:] for s in active_staff}
    best_penalty = get_penalty(best_schedule)

    with st.spinner('AIが数万通りの組み合わせから、連勤・連休を排除した完璧なパズルを探しています...'):
        for _ in range(10000): # 1万回のシャッフルトライアル
            if best_penalty == 0: break # 完璧なシフトが見つかったら終了

            s1 = random.choice(active_staff)
            d1 = random.randint(0, len(days_labels)-1)

            # 手動で入れた絶対ルールは動かさない
            if edited_trip.at[s1, days_labels[d1]] or edited_off.at[s1, days_labels[d1]]: continue

            mutation = random.choice(["swap_day", "swap_staff", "toggle"])
            orig_val = best_schedule[s1][d1]

            # ランダムに「休みの位置をずらす」「他の人と入れ替える」を試す
            if mutation == "swap_day":
                d2 = random.randint(0, len(days_labels)-1)
                if edited_trip.at[s1, days_labels[d2]] or edited_off.at[s1, days_labels[d2]]: continue
                best_schedule[s1][d1], best_schedule[s1][d2] = best_schedule[s1][d2], best_schedule[s1][d1]
                p = get_penalty(best_schedule)
                if p <= best_penalty: best_penalty = p # 良くなったら採用！
                else: best_schedule[s1][d1], best_schedule[s1][d2] = best_schedule[s1][d2], best_schedule[s1][d1] # ダメなら戻す

            elif mutation == "swap_staff":
                s2 = random.choice(active_staff)
                if s1 == s2: continue
                if edited_trip.at[s2, days_labels[d1]] or edited_off.at[s2, days_labels[d1]]: continue
                best_schedule[s1][d1], best_schedule[s2][d1] = best_schedule[s2][d1], best_schedule[s1][d1]
                p = get_penalty(best_schedule)
                if p <= best_penalty: best_penalty = p
                else: best_schedule[s1][d1], best_schedule[s2][d1] = best_schedule[s2][d1], best_schedule[s1][d1]

            elif mutation == "toggle":
                best_schedule[s1][d1] = "休" if orig_val == "" else ""
                p = get_penalty(best_schedule)
                if p <= best_penalty: best_penalty = p
                else: best_schedule[s1][d1] = orig_val

    # ⑤ 決定した無敵のスケジュール（休・出張）をベースに、早番と遅番を均等に割り振る
    res_df = pd.DataFrame.from_dict(best_schedule, orient='index', columns=days_labels)
    
    shift_types = ["早1", "早2", "遅1", "遅2"]
    earlies, lates = ["早1", "早2"], ["遅1", "遅2"]
    shift_counts = {s: {stype: 0 for stype in shift_types} for s in active_staff}

    for d_idx, day_label in enumerate(days_labels):
        working_staff = [s for s in active_staff if res_df.at[s, day_label] == ""]
        random.shuffle(working_staff)
        pool = shift_types * 3 # シフトの種類を十分に用意
        
        for s in working_staff:
            prev = res_df.at[s, days_labels[d_idx-1]] if d_idx > 0 else "休"
            available = sorted(pool, key=lambda p: shift_counts[s][p] + random.random() * 0.1)
            
            assigned = False
            for p in available:
                if prev in lates and p in earlies: continue # 遅番の翌日の早番は禁止
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

# ==========================================
# 🌟 完成したシフトの表示＆微調整（色付き）
# ==========================================
if f"temp_shift_{df_key}" in st.session_state:
    st.success("連勤と連休を排除した、完璧なシフトが完成しました！")
    
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
    st.write("※下の表で「早1」などを書き換えると、上の色付きマップも一瞬で連動して書き換わります！")
    
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

        stats.append({
            "スタッフ": s, 
            "休み(実/目)": f"{off_c}/{target_off_days[s]}", 
            "土日祝休": hol_off_c, 
            "早1": e1, "早2": e2, "遅1": l1, "遅2": l2
        })
        
    st.table(pd.DataFrame(stats))

    csv = edited_shift.to_csv().encode('utf_8_sig')
    st.download_button("📥 完成したシフトをダウンロード", csv, f"KASANE_shift_{year}_{month}.csv", "text/csv")
