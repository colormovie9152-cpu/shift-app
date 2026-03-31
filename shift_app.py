import streamlit as st
import pandas as pd
import calendar
from datetime import datetime, date
import random
import math
import jpholiday

# --- ロゴの読み込み ---
try:
    logo_image = "image_0.png" # GitHubに保存したロゴのファイル名
except:
    logo_image = None

# --- アプリの設定 ---
st.set_page_config(
    layout="wide",
    page_title="PILATES KASANE - Schedule Management",
    page_icon="🧘‍♀️"
)

# --- 💡オシャレなデザインのCSS適用 ---
st.markdown("""
<style>
    /* 全体の背景色とフォント */
    .stApp {
        background-color: #fcfcfc;
        color: #555555;
    }
    /* ヘッダーのロゴとタイトル */
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
        color: #5d5d4d; /* ロゴのトープ色 */
        font-weight: 400;
        letter-spacing: 0.1rem;
    }
    /* サイドバー */
    .css-1d391kg {
        background-color: #ffffff;
        border-right: 1px solid #e6e6e6;
        padding-top: 2rem;
    }
    /* サイドバーのタイトル */
    .css-163utfp, .css-1dp555/*, .st-b5*/ {
        color: #5d5d4d;
        font-weight: 400;
    }
    /* メインエリアのタイトル */
    .stHeader h2, .stHeader h3, .stHeader h4, .stHeader h5 {
        color: #5d5d4d;
        font-weight: 400;
        margin-top: 1.5rem;
    }
    /* データエディタ（チェック表）の調整 */
    div[data-testid="stDataEditor"] div {
        cursor: pointer !important;
    }
    /* ボタンの調整 */
    .stButton > button {
        background-color: #ffffff;
        color: #5d5d4d;
        border: 1px solid #5d5d4d;
        border-radius: 5px;
        font-weight: 400;
        letter-spacing: 0.05rem;
        padding: 0.5rem 1.5rem;
    }
    .stButton > button:hover {
        background-color: #5d5d4d;
        color: #ffffff;
    }
    /* 主要ボタン（トープ色） */
    .stButton > button.st-b6 {
        background-color: #5d5d4d;
        color: #ffffff;
        border: none;
    }
    .stButton > button.st-b6:hover {
        background-color: #4a4a3e;
    }
</style>
""", unsafe_allow_html=True)

# --- ヘッダー（ロゴとタイトル） ---
st.markdown("<div class='stHeader'>", unsafe_allow_html=True)
if logo_image:
    st.image(logo_image) # ロゴを表示
st.markdown("<h1>Schedule Management</h1></div>", unsafe_allow_html=True)

# --- 1. スタッフ・設定管理 ---
if 'staff_list' not in st.session_state:
    st.session_state.staff_list = ["スタッフA", "スタッフB", "スタッフC"] # デフォルト3人に変更

with st.sidebar:
    st.header("1. Staff & Month Settings")
    
    # スタッフ選択（動的なスタッフ数に対応）
    st.subheader("Select staff list from a selected predefined month.")
    if 'holiday_data' not in st.session_state:
        st.session_state.holiday_data = {} # メンバー変更時のリセット用

    active_staff = []
    for s in st.session_state.staff_list:
        if st.checkbox(s, value=True, key=f"active_{s}"):
            active_staff.append(s)
            
    # スタッフ追加・削除（クリーンなデザイン）
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
    # 年月の選択（クリーンなdropdown）
    year = st.selectbox("Year", range(date.today().year - 1, date.today().year + 3), index=1)
    month = st.selectbox("Month", range(1, 13), index=date.today().month - 1)

    # 各スタッフの純粋な休み数（月8日を基本に個別設定）
    st.header("Off Days")
    extra_off_days = {}
    for staff in active_staff:
        # Aさんは5日いないから、この月は3日休み、みたいな設定ができる！
        extra_off_days[staff] = st.number_input(f"{staff}の追加休み", min_value=0, max_value=20, value=8)

# --- カレンダー計算（曜日・祝日・おしゃれ表示対応） ---
days_in_month = calendar.monthrange(year, month)[1]
weekday_ja = ["(月)", "(火)", "(水)", "(木)", "(金)", "(土)", "(日)"]
days_labels = [] # 表示用：1日(月)
is_holiday_list = [] # 祝日判定フラグ

for i in range(1, days_in_month + 1):
    curr_date = date(year, month, i)
    wd = weekday_ja[curr_date.weekday()]
    holiday_name = jpholiday.is_holiday_name(curr_date)
    
    label = f"{i}日{wd}"
    if holiday_name:
        label += f" ※{holiday_name}"
        is_holiday_list.append(True)
    elif curr_date.weekday() >= 5: # 土日
        is_holiday_list.append(True)
    else:
        is_holiday_list.append(False)
    
    days_labels.append(label)

# --- 2. 出張・特別休みの設定（洗練されたチェック表） ---
st.header("2. Business Trip & Special Off-Day Settings (15th-24th Trip for Staff A)")
st.info("出張は『仕事だけど不在の日』、希望休は『絶対に休む日』としてチェックしてください。複数人・飛び石も自由自在です。")

# データの保持（リロード・メンバー変更・月変更対策）
df_key = f"{year}_{month}_{''.join(active_staff)}"
if 'holiday_df_raw' not in st.session_state:
    st.session_state.holiday_df_raw = {}

if df_key not in st.session_state.holiday_df_raw:
    st.session_state.holiday_df_raw[df_key] = pd.DataFrame(False, index=active_staff, columns=days_labels)

# ★ココを修正！「メンバー」か「月（列）」が変わったら表を作り直す！★
edited_raw = st.data_editor(st.session_state.holiday_df_raw[df_key], key=f"editor_{df_key}")
st.session_state.holiday_df_raw[df_key] = edited_raw

# --- 5. シフト作成ロジック ---
if st.button("Automatically Create Shift (Minimum 1 Staff Check Enabled)", type="primary"):
    earlies = ["早1", "早2"]
    lates = ["遅1", "遅2"]
    
    # 結果用データフレーム
    res_df = pd.DataFrame("", index=active_staff, columns=days_labels)
    
    # 統計用
    off_counts = {s: 0 for s in active_staff}
    weekend_off_counts = {s: 0 for s in active_staff}
    total_off_target = {}
    
    # 各スタッフの「目標合計休み数」を計算（チェックした数 + 追加の休み）
    for s in active_staff:
        fixed_count = sum(edited_raw.loc[s])
        total_off_target[s] = fixed_count + extra_off_days[s]

    for d_idx, day_label in enumerate(days_labels):
        is_sp_day = is_holiday_list[d_idx] 
        todays_fixed_off = []
        todays_trip = []
        
        # A. 手動設定の反映
        for s in active_staff:
            if edited_raw.at[s, day_label]:
                # もし出張か休みかまだ決まっていないなら、後でペース配分で決める
                todays_fixed_off.append(s)
                off_counts[s] += 1
                if is_sp_day: weekend_off_counts[s] += 1
                res_df.at[s, day_label] = "休" # 後で出張か休に書き換える

        # B. 【改善】3人以下のスタッフ数での「最低1人出勤」ルールを追加
        # 目標の休み数に達していなければ休ませる
        rem_s = [s for s in active_staff if s not in todays_fixed_off]
        random.shuffle(rem_s)
        rem_s.sort(key=lambda s: (weekend_off_counts[s] if is_sp_day else 0, off_counts[s] / total_off_target[s] if total_off_target[s] > 0 else 1.0))
        
        for s in rem_s:
            if off_counts[s] < total_off_target[s]:
                # ★ココを修正！最低2人出勤を死守するが、スタッフ数が少ない時は最低1人に許可！
                current_away = len(todays_fixed_off) + 1 + sum(edited_raw.loc[:, day_label])
                
                # アクティブなスタッフが3人以下なら、最低1人出勤を許可する
                min_working_staff = 2
                if len(active_staff) <= 3:
                    min_working_staff = 1

                if len(active_staff) - current_away >= min_working_staff:
                    todays_fixed_off.append(s)
                    off_counts[s] += 1
                    if is_sp_day: weekend_off_counts[s] += 1
                    res_df.at[s, day_label] = "休"

        # C. シフト割り当て
        working = [s for s in active_staff if s not in todays_fixed_off]
        random.shuffle(working)
        # その日の人数分、シフトを用意する（多めに2セット用意）
        pool = earlies + lates + earlies + lates
        
        for s in working:
            prev = res_df.at[s, days_labels[d_idx-1]] if d_idx > 0 else "休"
            assigned = False
            for p in pool:
                # 遅番の翌日に早番になる組み合わせはパスする（命を守るルール）
                if prev in lates and p in earlies: continue
                res_df.at[s, day_label] = p
                pool.remove(p) # プールから消費
                assigned = True
                break
                
            # もし禁止ルール等でどうしても割り当てられなかった場合の最終手段
            if not assigned: res_df.at[s, day_label] = "調整"

    st.success("間隔が調整された綺麗なシフトが完成しました！")
    
    # 💡色付けして美しく表示 (Styler)
    def style_shift(val):
        color = ''
        if val == '休': color = '#ffcccc' # 穏やかな赤
        elif val == '出張': color = '#ccffcc' # 淡い緑
        elif val == '調整': color = '#ffffcc' # 薄い黄色
        return f'background-color: {color}'

    # ★画像の「Minimum 1 Staff Check Enabled」を、表の下にst.infoとして追加して明示
    st.info("💡 この月はスタッフ数が少ないため、現場崩壊を防ぐために『最低1人出勤（ Minimum 1 Staff Check Enabled ）』のルールを適用しました。")
    st.dataframe(res_df.style.applymap(style_shift), height=400)
    
    # 📊 集計確認（不在日の合計）
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
