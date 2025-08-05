import streamlit as st
import mysql.connector
from datetime import datetime
from dotenv import load_dotenv
import os
load_dotenv()

# Database Configuration
db_config = {
    'host': os.environ.get("DB_HOST"),
    'user': os.environ.get("DB_USER"),
    'password': os.environ.get("DB_PASSWORD"),
    'database': os.environ.get("DB_NAME"),
}


def connect_db():
    try:
        return mysql.connector.connect(**db_config)    
    except mysql.connector.Error as err:
        st.error(f"Database connection failed: {err}")
        return None

# Create sales log table if not exists
def create_sales_log_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            item_id VARCHAR(50),
            name VARCHAR(100),
            quantity_sold INT,
            timestamp DATETIME
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Inventory CRUD
def read_inventory():
    conn = connect_db()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inventory")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

def add_item(item_id, name, price, quantity):
    conn = connect_db()
    cursor = conn.cursor()     

    cursor.execute("SELECT * FROM inventory WHERE id = %s", (item_id,))
    if cursor.fetchone():
        st.warning("Item ID already exists!")
    else:
        cursor.execute("INSERT INTO inventory (id, name, price, quantity) VALUES (%s, %s, %s, %s)",
                    (item_id, name, price, quantity))
        conn.commit()
        st.success("Item added successfully!")
    cursor.close()
    conn.close()

def update_item(item_id, name, price, quantity):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE inventory SET name=%s, price=%s, quantity=%s WHERE id=%s",
                   (name, price, quantity, item_id))
    conn.commit()
    cursor.close()
    conn.close()
    st.success("Item updated successfully!")

def delete_item(item_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM inventory WHERE id=%s", (item_id,))
    conn.commit()
    cursor.close()
    conn.close()
    st.success("Item deleted!")

def sell_item(item_id, quantity_sold):
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inventory WHERE id = %s", (item_id,))
    item = cursor.fetchone()

    if item and item['quantity'] >= quantity_sold:
        new_quantity = item['quantity'] - quantity_sold
        cursor.execute("UPDATE inventory SET quantity = %s WHERE id = %s", (new_quantity, item_id))

        # Log the sale
        cursor.execute("INSERT INTO sales_log (item_id, name, quantity_sold, timestamp) VALUES (%s, %s, %s, %s)",
                       (item_id, item['name'], quantity_sold, datetime.now()))
        conn.commit()
        st.success(f"Sold {quantity_sold} units of {item['name']}")
    else:
        st.error("Insufficient stock or item not found!")
    cursor.close()
    conn.close()

def read_sales_log():
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sales_log ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    return logs

# UI Design
st.set_page_config(page_title="Sports Inventory Dashboard", layout="wide")
st.title("🏟️ Sports Merchandise Inventory System")
create_sales_log_table()

menu = ["📦 Inventory", "🛒 Sell", "📊 Dashboard", "🧾 Sales Log"]
choice = st.sidebar.radio("Navigate", menu)

if choice == "📦 Inventory":
    st.subheader("Inventory Management")
    inventory = read_inventory()

    # KPI Display
    col1, col2, col3 = st.columns(3)
    total_items = sum(item['quantity'] for item in inventory)
    total_value = sum(item['quantity'] * item['price'] for item in inventory)
    out_of_stock = sum(1 for item in inventory if item['quantity'] == 0)
    col1.metric("Total Items", total_items)
    col2.metric("Potential Revenue", f"${total_value:,.2f}")
    col3.metric("Out of Stock", out_of_stock)

    with st.expander("➕ Add New Item"):
        with st.form("add_item_form"):
            item_id = st.text_input("Item ID")
            name = st.text_input("Name")
            price = st.number_input("Price", min_value=0.0)
            quantity = st.number_input("Quantity", min_value=0, step=1)
            submitted = st.form_submit_button("Add")
            if submitted:
                add_item(item_id, name, price, quantity)

    with st.expander("✏️ Update Item"):
        with st.form("update_item_form"):
            item_id = st.text_input("Item ID to Update")
            name = st.text_input("Updated Name")
            price = st.number_input("Updated Price", min_value=0.0)
            quantity = st.number_input("Updated Quantity", min_value=0, step=1)
            if st.form_submit_button("Update"):
                update_item(item_id, name, price, quantity)

    with st.expander("❌ Delete Item"):
        del_id = st.text_input("Item ID to Delete")
        if st.button("Delete"):
            delete_item(del_id)

    st.write("📋 Current Inventory")
    search_term = st.text_input("Search by Name or ID")
    if search_term:
        filtered = [item for item in inventory if search_term.lower() in item['name'].lower() or search_term in item['id']]
        st.table(filtered)
    else:
        st.table(inventory)

elif choice == "🛒 Sell":
    st.subheader("Sell Merchandise")
    item_id = st.text_input("Enter Item ID")
    quantity_sold = st.number_input("Quantity Sold", min_value=1, step=1)
    if st.button("Sell Item"):
        sell_item(item_id, quantity_sold)

elif choice == "📊 Dashboard":
    st.subheader("📈 Business Insights")
    inventory = read_inventory()
    if inventory:
        total_value = sum(item['price'] * item['quantity'] for item in inventory)
        st.write(f"**Total Inventory Value:** 💲{total_value:,.2f}")
        st.bar_chart({item['name']: item['quantity'] for item in inventory})
    else:
        st.warning("Inventory is empty.")

elif choice == "🧾 Sales Log":
    st.subheader("📄 Sales Transaction History")
    logs = read_sales_log()
    st.table(logs)