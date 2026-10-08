# pharmacy_app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="نظام نقاط البيع - صيدلية الأمل", layout="wide")

LOCAL_DB_PATH = 'local_pharmacy.db'

def get_connection():
    return sqlite3.connect(LOCAL_DB_PATH)

def init_local_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            barcode TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            buy_price REAL,
            sell_price REAL,
            stock_quantity INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pharmacy_name TEXT,
            type TEXT,
            barcode TEXT,
            product_name TEXT,
            quantity INTEGER,
            amount REAL,
            cost_amount REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_local_db()

CURRENT_PHARMACY = "صيدلية الأمل"

st.title(f"🏥 {CURRENT_PHARMACY}")

if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "sale"

col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🛍️ عملية بيع جديدة", use_container_width=True):
        st.session_state.active_tab = "sale"
with col2:
    if st.button("📦 إدخال مواد جديدة", use_container_width=True):
        st.session_state.active_tab = "add"
with col3:
    if st.button("📊 الجرد الحالي", use_container_width=True):
        st.session_state.active_tab = "inventory"
with col4:
    if st.button("📤 تصدير للإدارة", use_container_width=True):
        st.session_state.active_tab = "export"

st.divider()
conn = get_connection()

if st.session_state.active_tab == "add":
    st.subheader("📦 إضافة أدوية ومواد جديدة للمخزن")
    with st.form("add_p"):
        final_barcode = st.text_input("رقم الباركود")
        product_name = st.text_input("اسم الدواء / المادة")
        buy_price = st.number_input("سعر الشراء", min_value=0.0, format="%.2f")
        sell_price = st.number_input("سعر البيع للمستهلك", min_value=0.0, format="%.2f")
        quantity = st.number_input("الكمية المدخلة", min_value=1, value=10)
        
        if st.form_submit_button("📥 حفظ في المخزون"):
            if final_barcode and product_name:
                conn.execute("""
                    INSERT INTO products (barcode, name, buy_price, sell_price, stock_quantity)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(barcode) DO UPDATE SET
                        stock_quantity = stock_quantity + excluded.stock_quantity,
                        buy_price = excluded.buy_price,
                        sell_price = excluded.sell_price
                """, (final_barcode, product_name, buy_price, sell_price, quantity))
                
                conn.execute("""
                    INSERT INTO transactions (pharmacy_name, type, barcode, product_name, quantity, amount, cost_amount, date)
                    VALUES (?, 'شراء/إدخال', ?, ?, ?, ?, ?, ?)
                """, (CURRENT_PHARMACY, final_barcode, product_name, quantity, quantity * buy_price, quantity * buy_price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                st.success("تم الحفظ بنجاح!")

elif st.session_state.active_tab == "inventory":
    st.subheader("📊 المخزون الحالي بالفرع")
    df_inv = pd.read_sql("SELECT barcode AS 'الباركود', name AS 'اسم الدواء', buy_price AS 'سعر الشراء', sell_price AS 'سعر البيع', stock_quantity AS 'الكمية المتاحة' FROM products", conn)
    st.dataframe(df_inv, use_container_width=True)

elif st.session_state.active_tab == "export":
    st.subheader("📤 تصدير البيانات إلى برنامج الإدارة")
    
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.markdown("### 1️⃣ تصدير سجل الحركات المالية")
        df_trans = pd.read_sql("SELECT * FROM transactions", conn)
        if not df_trans.empty:
            csv_trans = df_trans.to_csv(index=False).encode('utf-8')
            st.download_button(label="⬇️ تحميل الحركات (CSV)", data=csv_trans, file_name=f"{CURRENT_PHARMACY}_transactions.csv", mime="text/csv")
            
    with col_exp2:
        st.markdown("### 2️⃣ تصدير جدول المخزون والأسعار")
        df_prods = pd.read_sql("SELECT * FROM products", conn)
        if not df_prods.empty:
            csv_prods = df_prods.to_csv(index=False).encode('utf-8')
            st.download_button(label="⬇️ تحميل الأسعار والمخزون (CSV)", data=csv_prods, file_name=f"{CURRENT_PHARMACY}_products.csv", mime="text/csv", type="primary")

conn.close()
