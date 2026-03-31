import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import random

st.set_page_config(layout="wide", page_title="自動シフト作成くん")

st.title("🗓️ 自動シフト作成くん")

# --- サイドバー：設定 ---
st.sidebar.header("1. スタッフ設定")
if 'staff_list' not in st.session_state:
    # 4人でテストしやすいように初期設定を変更しました
    st.session_state.staff_list = ["スタッフA", "スタッフB", "スタッフC", "スタッフD"] 

new_staff = st.sidebar.text_input("名前を追加")
if st.sidebar.button("追加"):
    if new_staff and new_staff not in st.session_state.staff_list:
        st.session_state.staff_list.append(new_staff)

selected_staff = st.sidebar.multiselect("今月のメンバーを選択", st.session_state.staff_list, default=st.session_state.staff_list)

# --- 月の設定 ---
st.sidebar.header("2. 年月の設定")
year = st.sidebar.number_input("年", value=datetime.now().year)
month = st.sidebar.number_input("月", min_value=1, max_value=12, value=datetime.now().month)

days_in_month = calendar.monthrange(year, month)[1]
days = [f"{i}日" for i in range(1, days_in_month + 1)]

# --- イレギュラー休みの設定 ---
st.header("3. 個別休み設定（休みを入れたい箇所にチェック）")
holiday_df = pd.DataFrame(False, index=selected_staff, columns=days)
edited_holidays = st.data_editor(holiday_df)

# --- シフト作成ロジック ---
if st.button("✨ シフトを自動作成する"):
    # シフトの種類
    earlies = ["早1(7:30)", "早2(8:30)"]
    lates = ["遅1(11:30)", "遅2(12:30)"]
    
    result_df = pd.DataFrame("休", index=selected_staff, columns=days)
    
    for d_idx, day in enumerate(days):
        # 1. 過去の連勤日数を計算
        consec_work = {}
        for staff in selected_staff:
            count = 0
            for b in range(1, 4): # 最大3日前までチェック
                if d_idx - b >= 0 and result_df.at[staff, days[d_idx - b]] != "休":
                    count += 1
                else:
                    break
            consec_work[staff] = count

        # 2. 今日の「休み」メンバーを決める
        off_today = []
        
        # 絶対に休みの人（手動チェック）
        for staff in selected_staff:
            if edited_holidays.at[staff, day]:
                off_today.append(staff)
                
        # 残りのスタッフから「連勤が多い順」に休みを検討する
        remaining_staff = [s for s in selected_staff if s not in off_today]
        random.shuffle(remaining_staff) # 同じ条件の時に偏らないようにシャッフル
        remaining_staff.sort(key=lambda s: consec_work[s], reverse=True)
        
        for staff in remaining_staff:
            # 3連勤以上している ＆ 休みにしても「出勤が最低2人」をキープできるなら休ませる
            if consec_work[staff] >= 3:
                if len(selected_staff) - (len(off_today) + 1) >= 2:
                    off_today.append(staff)
                    
        # 休みを分散させる裏技：誰も休みじゃない日が続くと後で破綻するので、
        # 出勤が3人以上いるなら、一番連勤している人を1人休ませておく
        if len(selected_staff) - len(off_today) > 3:
            for staff in remaining_staff:
                if staff not in off_today and len(selected_staff) - (len(off_today) + 1) >= 2:
                    off_today.append(staff)
                    break

        # 3. 出勤メンバーにシフトを割り振る
        working_staff = [s for s in selected_staff if s not in off_today]
        random.shuffle(working_staff) # 出勤メンバーをシャッフル
        
        # 今日割り振るシフトの候補（人数に合わせて柔軟に対応できるように多めに用意）
        shift_pool = earlies + lates + earlies + lates 
        
        for staff in working_staff:
            prev_shift = "休"
            if d_idx > 0:
                prev_shift = result_df.at[staff, days[d_idx-1]]
                
            assigned = False
            for s_type in shift_pool:
                # 遅番の次の日に早番はNG
                if prev_shift in lates and s_type in earlies:
                    continue
                
                result_df.at[staff, day] = s_type
                shift_pool.remove(s_type) # 使った枠は消す
                assigned = True
                break
                
            # 万が一「遅番の次で早番の枠しか残っていない」など、割り振れない場合の救済措置
            if not assigned:
                result_df.at[staff, day] = "遅番(調整)"

    st.success("シフトを作成しました！")
    st.dataframe(result_df)

    # CSVダウンロード
    csv = result_df.to_csv().encode('utf_8_sig')
    st.download_button("📥 スプレッドシート用に保存(CSV)", csv, "shift.csv", "text/csv")

# --- 削除機能 ---
st.sidebar.markdown("---")
staff_to_delete = st.sidebar.selectbox("スタッフ削除", ["選択してください"] + st.session_state.staff_list)
if st.sidebar.button("削除実行"):
    if staff_to_delete in st.session_state.staff_list:
        st.session_state.staff_list.remove(staff_to_delete)
        st.rerun()