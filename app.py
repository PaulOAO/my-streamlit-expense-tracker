import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- 網頁介面設定 ---
st.set_page_config(page_title="我的雲端記帳本", page_icon="💰", layout="wide")
st.title("💰 我的個人記帳 Web App (Google Sheets 雲端同步版)")

# --- 建立 Google Sheets 連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_all_records():
    """從 Google Sheets 讀取所有資料"""
    try:
        df = conn.read(ttl=0)
        if df.empty:
            return pd.DataFrame(columns=["date", "type", "category", "amount", "note"])
        df = df.sort_values(by="date", ascending=False)
        return df
    except Exception as e:
        return pd.DataFrame(columns=["date", "type", "category", "amount", "note"])

def add_record(date, type_, category, amount, note):
    """新增一筆紀錄到 Google Sheets"""
    df = get_all_records()
    new_data = pd.DataFrame([{
        "date": date,
        "type": type_,
        "category": category,
        "amount": float(amount),
        "note": note
    }])
    updated_df = pd.concat([df, new_data], ignore_index=True)
    conn.update(data=updated_df)

def delete_record_by_index(original_index):
    """根據 Pandas 的原始 index 刪除紀錄"""
    df = get_all_records()
    updated_df = df.drop(original_index)
    conn.update(data=updated_df)


# --- 側邊欄：新增記帳資料 ---
st.sidebar.header("✍️ 新增收支紀錄")

with st.sidebar.form(key="add_form", clear_on_submit=True):
    date = st.date_input("日期", datetime.now())
    type_ = st.selectbox("類型", ["支出", "收入"])
    
    if type_ == "支出":
        category = st.selectbox("分類", ["餐飲", "交通", "娛樂", "購物", "居住", "醫療", "其他"])
    else:
        category = st.selectbox("分類", ["薪資", "投資", "獎金", "副業", "其他"])
        
    amount = st.number_input("金額", min_value=0.0, step=10.0, format="%.1f")
    note = st.text_input("備註（選填）")
    
    submit_button = st.form_submit_button(label="送出紀錄")

if submit_button:
    if amount > 0:
        add_record(date.strftime("%Y-%m-%d"), type_, category, amount, note)
        st.sidebar.success("🎉 雲端同步成功！")
        st.rerun()
    else:
        st.sidebar.error("金額必須大於 0 喔！")

# --- 主畫面：數據儀表板 ---
df = get_all_records()

if not df.empty and "amount" in df.columns:
    df["amount"] = pd.to_numeric(df["amount"], errors='coerce').fillna(0)
    total_income = df[df["type"] == "收入"]["amount"].sum()
    total_expense = df[df["type"] == "支出"]["amount"].sum()
    balance = total_income - total_expense
else:
    total_income, total_expense, balance = 0, 0, 0

col1, col2, col3 = st.columns(3)
col1.metric(label="📈 總收入", value=f"${total_income:,.1f}")
col2.metric(label="📉 總支出", value=f"${total_expense:,.1f}")
col3.metric(label="💼 淨資產 (結餘)", value=f"${balance:,.1f}")

st.write("---")
main_col, side_col = st.columns([2, 1])

with main_col:
    st.subheader("📊 消費與收入分析")
    if not df.empty and total_income + total_expense > 0:
        fig = px.pie(df, values='amount', names='category', color='type',
                     title='各分類比例圖', hole=0.3,
                     color_discrete_map={'收入':'#2ecc71', '支出':'#e74c3c'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("目前雲端尚無數據，快在左側新增第一筆吧！")

    st.subheader("📜 歷史記帳明細 (同步自 Google Sheets)")
    if not df.empty:
        st.dataframe(df[["date", "type", "category", "amount", "note"]], use_container_width=True, hide_index=True)
    else:
        st.text("暫無明細")

with side_col:
    st.subheader("⚙️ 紀錄管理")
    if not df.empty:
        st.write("🗑️ 刪除特定紀錄：")
        delete_options = []
        for idx, row in df.iterrows():
            delete_options.append((idx, f"{row['date']} | {row['category']} | ${row['amount']}"))
            
        record_to_delete = st.selectbox(
            "請選擇要刪除的紀錄",
            options=delete_options,
            format_func=lambda x: x[1]
        )
        if st.button("確認刪除", type="primary"):
            delete_record_by_index(record_to_delete[0])
            st.success("已成功從雲端刪除該筆紀錄！")
            st.rerun()
    else:
        st.write("暫無可管理的紀錄")
