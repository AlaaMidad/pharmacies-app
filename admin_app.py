# admin_app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

st.set_page_config(
    page_title="لوحة الإدارة والمراقبة - شبكة الصيدليات",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = 'pharmacy_system.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pharmacies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            whatsapp_number TEXT,
            location TEXT,
            status TEXT DEFAULT 'نشط'
        )
    ''')
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

init_db()

st.sidebar.title("🏢 قائمة الإدارة الموحدة")
page = st.sidebar.radio("انتقل إلى:", [
    "📊 لوحة المراقبة والأرباح",
    "🔄 دمج ومزامنة بيانات الفروع",
    "📦 المخزون العام والمنتجات"
])

conn = get_connection()

if page == "📊 لوحة المراقبة والأرباح":
    st.header("📊 لوحة الأداء المالي والمراقبة الشاملة")
    df_trans = pd.read_sql("SELECT * FROM transactions", conn)
    
    if not df_trans.empty:
        sales_df = df_trans[df_trans['type'] == 'بيع']
        total_sales = sales_df['amount'].sum() if not sales_df.empty else 0.0
        total_cost = sales_df['cost_amount'].sum() if not sales_df.empty else 0.0
        net_profit = total_sales - total_cost
    else:
        total_sales = total_cost = net_profit = 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("إجمالي المبيعات", f"{total_sales:,.2f} $")
    m2.metric("التكلفة", f"{total_cost:,.2f} $")
    m3.metric("صافي الأرباح", f"{net_profit:,.2f} $")
    
    st.divider()
    st.subheader("📋 تفاصيل الحركات والعمليات")
    st.dataframe(df_trans, use_container_width=True)

elif page == "🔄 دمج ومزامنة بيانات الفروع":
    st.header("🔄 استيراد ومزامنة العمليات والمخزون من الفروع")
    st.info("💡 قم برفع ملف المنتجات والمخزون لتحديث أسعار البيع والشراء، أو ملف الحركات لتحديث الميزانية.")
    
    uploaded_files = st.file_uploader("اختر ملفات (CSV) المصدّرة:", type=["csv", "xlsx"], accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("📥 دمج البيانات وتحديث الأسعار والمخزون", type="primary"):
            trans_added = 0
            prods_updated = 0
            
            for uploaded_file in uploaded_files:
                try:
                    df_up = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                    
                    if 'sell_price' in df_up.columns:
                        for _, row in df_up.iterrows():
                            barcode = str(row.get('barcode', ''))
                            p_name = str(row.get('name', ''))
                            b_price = float(row.get('buy_price', 0.0))
                            s_price = float(row.get('sell_price', 0.0))
                            qty = int(row.get('stock_quantity', 0))
                            
                            if barcode and p_name:
                                conn.execute("""
                                    INSERT INTO products (barcode, name, buy_price, sell_price, stock_quantity)
                                    VALUES (?, ?, ?, ?, ?)
                                    ON CONFLICT(barcode) DO UPDATE SET
                                        name = excluded.name,
                                        buy_price = excluded.buy_price,
                                        sell_price = excluded.sell_price,
                                        stock_quantity = excluded.stock_quantity
                                """, (barcode, p_name, b_price, s_price, qty))
                                prods_updated += 1
                                
                    elif 'amount' in df_up.columns:
                        for _, row in df_up.iterrows():
                            p_name = row.get('pharmacy_name', 'فرع غير محدد')
                            p_type = row.get('type', 'بيع')
                            barcode = str(row.get('barcode', ''))
                            prod_name = row.get('product_name', 'منتج')
                            qty = int(row.get('quantity', 1))
                            amt = float(row.get('amount', 0.0))
                            cost_amt = float(row.get('cost_amount', 0.0))
                            trans_date = str(row.get('date', datetime.now()))
                            
                            conn.execute("""
                                INSERT INTO transactions (pharmacy_name, type, barcode, product_name, quantity, amount, cost_amount, date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (p_name, p_type, barcode, prod_name, qty, amt, cost_amt, trans_date))
                            trans_added += 1
                            
                except Exception as e:
                    st.error(f"خطأ أثناء معالجة الملف {uploaded_file.name}: {e}")
            
            conn.commit()
            st.success(f"✅ تم تحديث {prods_updated} منتج بالأسعار الصحيحة، ودمج {trans_added} حركات بنجاح!")
            st.rerun()

elif page == "📦 المخزون العام والمنتجات":
    st.header("📦 حالة المخزون الموحد والأسعار")
    df_stock = pd.read_sql("SELECT barcode AS 'الباركود', name AS 'اسم المنتج', buy_price AS 'سعر الشراء', sell_price AS 'سعر البيع', stock_quantity AS 'الكمية المتاحة' FROM products", conn)
    st.dataframe(df_stock, use_container_width=True)

conn.close()
