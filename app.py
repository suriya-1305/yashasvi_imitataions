from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Yashasvi Cloud Console", page_icon="💎", layout="wide")
st.title("💎 Yashasvi Imitations — Cloud Terminal")
st.write("---")

# --- ESTABLISH CLOUD GSHEETS CONNECTION ---
# Connects using credentials stored securely in Streamlit Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_inventory = conn.read(worksheet="Inventory", ttl=0)
    df_sales = conn.read(worksheet="Sales Log", ttl=0)
except Exception:
    st.error("🔒 Cloud Database Sync Connection Pending. Please configure your Secrets arrays.")
    st.stop()

# Clean dataframes
df_inventory.columns = df_inventory.columns.str.strip()
df_sales.columns = df_sales.columns.str.strip()
df_inventory["Item Code"] = df_inventory["Item Code"].astype(str).str.strip().str.upper()

# --- THE 4-PAGE DASHBOARD STRUCTURE ---
p1, p2, p3, p4 = st.tabs([
    "📦 1. Live Stock Dashboard", 
    "🎯 2. Active Order Billing", 
    "📈 3. Live Order Analytics", 
    "💰 4. Financial Health Chart"
])

# --- PAGE 1: LIVE STOCK DASHBOARD ---
with p1:
    st.subheader("Current Operational Stock Summary")
    display_columns = ["Item Type", "Item Code", "Remaining Quantity"]
    available_cols = [col for col in display_columns if col in df_inventory.columns]
    
    if df_inventory.empty:
        st.info("Cloud repository catalog is currently empty.")
    else:
        total_units = int(df_inventory["Remaining Quantity"].sum())
        st.metric(label="Total Volumetric Units in Stock", value=f"{total_units} units")
        st.dataframe(
            df_inventory[available_cols], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Remaining Quantity": st.column_config.NumberColumn("Quantity Available", width="small"),
                "Item Code": st.column_config.TextColumn("Item Code", width="small"),
                "Item Type": st.column_config.TextColumn("Item Type / Category", width="large")
            }
        )

# --- PAGE 2: ACTIVE ORDER BILLING ---
with p2:
    st.subheader("Checkout Counter Terminal")
    
    with st.form("checkout_form", clear_on_submit=True):
        sku_options = df_inventory["Item Code"].dropna().tolist()
        chosen_skus = st.multiselect("Select Target Item Code(s)", options=sku_options)
        
        discount_pct = st.number_input(
            "Applied Discount Percentage (%)", 
            min_value=0.0, max_value=100.0, value=None, step=5.0,
            placeholder="Type discount percentage (leave empty for 0%)"
        )
        
        confirm_transaction = st.form_submit_button("Log Order & Commit to Cloud Sheet 🚀")
        
        if confirm_transaction:
            if not chosen_skus:
                st.error("At least one item selection is required.")
            else:
                insufficient_stock = []
                for sku in chosen_skus:
                    row_idx = df_inventory[df_inventory["Item Code"] == sku].index[0]
                    if int(df_inventory.at[row_idx, "Remaining Quantity"]) <= 0:
                        insufficient_stock.append(sku)
                
                if insufficient_stock:
                    st.error(f"Transaction Blocked. Out of stock: {insufficient_stock}")
                else:
                    actual_discount = discount_pct if discount_pct is not None else 0.0
                    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    new_sales_entries = []
                    total_bill_amount = 0.0
                    
                    for sku in chosen_skus:
                        row_idx = df_inventory[df_inventory["Item Code"] == sku].index[0]
                        current_stock = int(df_inventory.at[row_idx, "Remaining Quantity"])
                        
                        item_type_val = df_inventory.at[row_idx, "Item Type"]
                        base_price_val = float(df_inventory.at[row_idx, "Selling Price"])
                        
                        final_selling_price = base_price_val * (1.0 - (actual_discount / 100.0))
                        total_bill_amount += final_selling_price
                        next_order_id = len(df_sales) + len(new_sales_entries) + 1
                        
                        # Update localized copy state
                        df_inventory.at[row_idx, "Remaining Quantity"] = current_stock - 1
                        if "Total" in df_inventory.columns:
                            df_inventory.at[row_idx, "Total"] = df_inventory.at[row_idx, "Remaining Quantity"] * base_price_val
                        
                        new_sales_entries.append({
                            "Order ID": next_order_id, "Item Code": sku, "Item Type": item_type_val,
                            "Original Price (₹)": base_price_val, "Discount (%)": actual_discount,
                            "Final Revenue (₹)": final_selling_price, "Timestamp": timestamp_str
                        })
                    
                    # Append rows and rewrite worksheets on Google Drive API
                    if new_sales_entries:
                        df_sales = pd.concat([df_sales, pd.DataFrame(new_sales_entries)], ignore_index=True)
                    
                    # Push updates live to cloud sheet tracking frames
                    conn.update(worksheet="Inventory", data=df_inventory)
                    conn.update(worksheet="Sales Log", data=df_sales)
                    
                    st.success(f"Cloud Transaction Confirmed! Total Bill: ₹{total_bill_amount:,.2f}")
                    st.rerun()

# --- PAGE 3: LIVE ORDER ANALYTICS ---
with p3:
    st.subheader("Real-Time Sales Ingestion Log")
    if df_sales.empty:
        st.info("Awaiting initial conversions.")
    else:
        stat_col1, stat_col2 = st.columns(2)
        stat_col1.metric("Total Items Sold Today", f"{len(df_sales)} Units")
        stat_col2.metric("Gross Revenue Realized", f"₹{df_sales['Final Revenue (₹)'].sum():,.2f}")
        st.dataframe(df_sales.sort_values(by="Order ID", ascending=False), use_container_width=True, hide_index=True)

# --- PAGE 4: FINANCIAL HEALTH CHART ---
with p4:
    st.subheader("Asset Value Metrics Summary")
    if df_inventory.empty:
        st.info("No active catalogs found.")
    else:
        remaining_inventory_value = (df_inventory["Selling Price"] * df_inventory["Remaining Quantity"]).sum()
        cash_earned_value = df_sales["Final Revenue (₹)"].sum() if not df_sales.empty else 0.0
        
        met1, met2 = st.columns(2)
        met1.metric("Unrealized Stock Book Value", f"₹{remaining_inventory_value:,.2f}")
        met2.metric("Liquid Cash Capitalized", f"₹{cash_earned_value:,.2f}")
        
        chart_df = pd.DataFrame({
            "Financial Dimension": ["Remaining Stock Value", "Liquid Cash Earned"],
            "Amount (₹)": [remaining_inventory_value, cash_earned_value]
        })
        st.bar_chart(data=chart_df, x="Financial Dimension", y="Amount (₹)", use_container_width=True)