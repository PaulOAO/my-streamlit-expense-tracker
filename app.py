import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
from pathlib import Path

# --- 資料庫安全設定（適合雲端部署） ---
# 確保資料庫檔案會建立在專案的根目錄下，避免 Streamlit Cloud 權限錯誤
DB_DIR = Path(__file__).parent
DB_FILE = DB_DIR / "expense_tracker.db"

def init_db():
    """初始化資料庫，建立記帳資料表"""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            category TEXT,
            amount REAL,
            note TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_record(date, type_, category, amount, note):
    """新增一筆紀錄"""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute(
        "INSERT INTO records (date, type, category, amount, note) VALUES (?, ?, ?, ?, ?)",
        (date, type_, category, amount, note)
    )
    conn.commit()
    conn.close()

def get_all_records():
    """取得所有紀錄並轉為 DataFrame"""
    conn = sqlite3.connect(str(DB_FILE))
    df = pd.read_sql_query("SELECT * FROM records ORDER BY date DESC, id DESC", conn)
    conn.close()
    return df

def delete_record(record_id):
    """刪除指定 ID 的紀錄"""
    conn = sqlite3.connect(str(DB_FILE))
    c = conn.cursor()
    c.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

# 執行初始化資料庫
init_db()

# --- 網頁介面設定 ---
st.set_page_config(page_title="我的個人記帳本", page_icon="💰", layout="wide")
st.title("💰 我的個人記帳 Web App")

# --- 側邊欄：新增記帳資料 ---
st.sidebar.header("✍️ 新增收支紀錄")

with st.sidebar.form(key="add_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.now())
    type_ = st.selectbox("類型", ["支出", "收入"])
    
    # 根據收支類型提供不同的預設分類
    if type_ == "支出":
        category = st.selectbox("分類", ["餐飲", "交通", "娛樂", "購物", "居住", "醫療", "其他"])
    else:
        category = st.selectbox("分類", ["薪資", "投資", "獎金", "副業", "其他"])
        
    amount = st.number_input("金額", min_value=0.0, step=10.0, format="%.1f")
    note = st.text_input("備註（選填）")
    
    submit_button = st.form_submit_button(label="送出紀錄")

if submit_button:
    if amount > 0:
        # 將日期轉為字串儲存
        add_record(date.strftime("%Y-%m-%d"), type_, category, amount, note)
        st.sidebar.success("🎉 紀錄成功！")
        # 重新整理網頁以更新數據
        st.rerun()
    else:
        st.sidebar.error("金額必須大於 0 喔！")

# --- 主畫面：數據儀表板 ---
df = get_all_records()

# 計算總資產
if not df.empty:
    total_income = df[df["type"] == "收入"]["amount"].sum()
    total_expense = df[df["type"] == "支出"]["amount"].sum()
    balance = total_income - total_expense
else:
    total_income, total_expense, balance = 0, 0, 0

# 顯示摘要卡片（三欄式設計）
col1, col2, col3 = st.columns(3)
col1.metric(label="📈 總收入", value=f"${total_income:,.1f}", delta_color="normal")
col2.metric(label="📉 總支出", value=f"${total_expense:,.1f}", delta_color="inverse")
col3.metric(label="💼 淨資產 (結餘)", value=f"${balance:,.1f}")

st.write("---")

# 區分左右兩欄：左邊放圖表與明細，右邊放管理操作
main_col, side_col = st.columns([2, 1])

with main_col:
    st.subheader("📊 消費與收入分析")
    if not df.empty:
        # 畫圓餅圖
        fig = px.pie(df, values='amount', names='category', color='type',
                     title='各分類比例圖', hole=0.3,
                     color_discrete_map={'收入':'#2ecc71', '支出':'#e74c3c'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("目前還沒有任何數據，快在左側新增第一筆吧！")

    st.subheader("📜 歷史記帳明細")
    if not df.empty:
        # 整理顯示的欄位，隱藏不易閱讀的 index
        display_df = df[["id", "date", "type", "category", "amount", "note"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.text("暫無明細")

with side_col:
    st.subheader("⚙️ 紀錄管理")
    if not df.empty:
        st.write("🗑️ 刪除特定紀錄：")
        # 讓使用者選擇要刪除的 ID，並在下拉選單顯示該筆資料的摘要
        record_to_delete = st.selectbox(
            "請選擇要刪除的紀錄 ID",
            options=df["id"].tolist(),
            format_func=lambda x: f"ID: {x} | {df[df['id']==x]['date'].values[0]} | {df[df['id']==x]['category'].values[0]} | ${df[df['id']==x]['amount'].values[0]}"
        )
        if st.button("確認刪除", type="primary"):
            delete_record(record_to_delete)
            st.success(f"已成功刪除 ID: {record_to_delete} 的紀錄")
            st.rerun()
    else:
        st.write("暫無可管理的紀錄")
