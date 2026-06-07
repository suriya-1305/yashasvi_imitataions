import base64
import json
from datetime import datetime
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Yashasvi Cloud Console", page_icon="💎", layout="wide")
st.title("💎 Yashasvi Imitations — Cloud Terminal")
st.write("---")

# --- BULLETPROOF BASE64 DECRYPTION ENGINE ---
@st.cache_resource
def get_gspread_client():
    if "encoded_creds" not in st.secrets:
        st.error("🔒 Cloud Configuration Missing: Please add 'encoded_creds' to your Streamlit Secrets box.")
        st.stop()
    
    try:
        raw_json_bytes = base64.b64decode(st.secrets["encoded_creds"])
        creds_dict = json.loads(raw_json_bytes)
            
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Base64 Decryption Engine failed: {e}")
        st.stop()

# Initialize the authenticated connection
client = get_gspread_client()
SPREADSHEET_ID = "1hcxENlBErHhNMMxuv_rdtqsSnXaRp5af2rhflrrwDBg"

# Initialize empty diagnostics variables to prevent NameErrors inside the except block
all_worksheets = []

try:
    sheet = client.open_by_key(SPREADSHEET_ID)
    all_worksheets = sheet.worksheets()
    
    # Map sheets by position (0-indexed: 1 is the 2nd tab, 2 is the 3rd tab)
    inventory_worksheet = sheet.get_worksheet(1)
    sales_worksheet = sheet.get_worksheet(2)
    
    if inventory_worksheet is None or sales_worksheet is None:
        st.error(f"❌ Position Mapping Error: Your workbook only has {len(all_worksheets)} tab(s). It must have at least 3 tabs.")
        st.stop()

    # Read raw string matrices to prevent column header formatting crashes
    raw_inv_data = inventory_worksheet.get_all_values()
    if raw_inv_data:
        df_inventory = pd.DataFrame(raw_inv_data[1:], columns=raw_inv_data[0])
    else:
        df_inventory = pd.DataFrame(columns=["Item Type", "Item Code", "Selling Price", "Remaining Quantity", "Total"])
        
    raw_sales_data = sales_worksheet.get_all_values()
    if raw_sales_data:
        df_sales = pd.DataFrame(raw_sales_data[1:], columns=raw_sales_data[0])
    else:
        df_sales = pd.DataFrame(columns=["Order ID", "Item Code", "Item Type", "Original Price (₹)", "Discount (%)", "Final Revenue (₹)", "Timestamp"])

except Exception as e:
    st.error(f"❌ Structural Ingestion Failure: {e}")
    
    # SAFE LIVE DIAGNOSTIC DEBUGGER FOR MOBILE
    st.markdown("### 🛠️ Live Workbook Schema Diagnostic Dump")
    if not all_worksheets:
        st.warning("⚠️ Could not connect to the file at all. Please verify your SPREADSHEET_ID and make sure the Service Account email is added as an **Editor** in the Google Sheet's Share menu.")
    else:
        st.info(f"Total Detected Tabs: `{len(all_worksheets)}`")
        for idx, w_sheet in enumerate(all_worksheets):
            try:
                first_row = w_sheet.get_all_values()
                headers = first_row[0] if first_row else ["EMPTY SHEET"]
                st.markdown(f"**Tab Position {idx + 1}:** `{w_sheet.title}` | **Detected Headers:** `{headers}`")
            except Exception as row_err:
                st.markdown(f"**Tab Position {idx + 1}:** `{w_sheet.title}` | *Could not read row headers: {row_err}*")
    st.stop()

# Strip accidental whitespaces from headers to prevent KeyErrors
df_inventory.columns = df_inventory.columns.str.strip()
df_sales.columns = df_sales.columns.str.strip()

# Normalize SKU key text styles
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
        st.info("Your remote inventory repository appears to be empty.")
    else:
        total_units = int(pd.to_numeric(df_inventory["Remaining Quantity"], errors='coerce').sum()) if "Remaining Quantity" in df_inventory.columns else 0
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
        
        confirm_transaction = st.form_submit_button("Log Order & Update Google Sheets Cloud 🚀")
        
        if confirm_transaction:
            if not chosen_skus:
                st.error("At least one item code selection is required.")
            else:
                insufficient_stock = []
                for sku in chosen_skus:
                    row_idx = df_inventory[df_inventory["Item Code"] == sku].index[0]
                    stock_val = pd.to_numeric(df_inventory.at[row_idx, "Remaining Quantity"], errors='coerce')
                    if pd.isna(stock_val) or int(stock_val) <= 0:
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
                        current_stock = int(pd.to_numeric(df_inventory.at[row_idx, "Remaining Quantity"]))
                        
                        item_type_val = df_inventory.at[row_idx, "Item Type"]
                        base_price_val = float(pd.to_numeric(df_inventory.at[row_idx, "Selling Price"], errors='coerce'))
                        
                        final_selling_price = base_price_val * (1.0 - (actual_discount / 100.0))
                        total_bill_amount += final_selling_price
                        next_order_id = len(df_sales) + len(new_sales_entries) + 1
                        
                        df_inventory.at[row_idx, "Remaining Quantity"] = current_stock - 1
                        if "Total" in df_inventory.columns:
                            df_inventory.at[row_idx, "Total"] = int(df_inventory.at[row_idx, "Remaining Quantity"]) * base_price_val
                        
                        new_sales_entries.append({
                            "Order ID": next_order_id, "Item Code": sku, "Item Type": item_type_val,
                            "Original Price (₹)": base_price_val, "Discount (%)": actual_discount,
                            "Final Revenue (₹)": final_selling_price, "Timestamp": timestamp_str
                        })
                    
                    if new_sales_entries:
                        df_sales = pd.concat([df_sales, pd.DataFrame(new_sales_entries)], ignore_index=True)
                    
                    try:
                        inventory_worksheet.clear()
                        inventory_worksheet.update('A1', [df_inventory.columns.values.tolist()] + df_inventory.astype(str).values.tolist())
                        
                        sales_worksheet.clear()
                        sales_worksheet.update('A1', [df_sales.columns.values.tolist()] + df_sales.astype(str).values.tolist())
                        
                        st.success(f"Cloud Sync Successful! Total Bill: ₹{total_bill_amount:,.2f}")
                        st.rerun()
                    except Exception as sheet_err:
                        st.error(f"Cloud update failed: {sheet_err}")

# --- PAGE 3: LIVE ORDER ANALYTICS ---
with p3:
    st.subheader("Real-Time Sales Ingestion Log")
    if df_sales.empty:
        st.info("Awaiting initial stall conversions.")
    else:
        revenue_sum = pd.to_numeric(df_sales['Final Revenue (₹)'], errors='coerce').sum()
        stat_col1, stat_col2 = st.columns(2)
        stat_col1.metric("Total Items Sold", f"{len(df_sales)} Units")
        stat_col2.metric("Gross Revenue Realized", f"₹{revenue_sum:,.2f}")
        st.dataframe(df_sales.sort_values(by="Order ID", ascending=False), use_container_width=True, hide_index=True)

# --- PAGE 4: FINANCIAL HEALTH CHART ---
with p4:
    st.subheader("Asset Value Metrics Summary")
    if df_inventory.empty:
        st.info("Populate stock configurations to load the analytics charts.")
    else:
        sell_price = pd.to_numeric(df_inventory["Selling Price"], errors='coerce')
        rem_qty = pd.to_numeric(df_inventory["Remaining Quantity"], errors='coerce')
        remaining_inventory_value = (sell_price * rem_qty).sum()
        
        cash_earned_value = pd.to_numeric(df_sales["Final Revenue (₹)"], errors='coerce').sum() if not df_sales.empty else 0.0
        
        met1, met2 = st.columns(2)
        met1.metric("Unrealized Stock Book Value", f"₹{remaining_inventory_value:,.2f}")
        met2.metric("Liquid Cash Capitalized", f"₹{cash_earned_value:,.2f}")
        
        st.markdown("#### Capital Distribution Ratio Visualization")
        chart_df = pd.DataFrame({
            "Financial Dimension": ["Remaining Stock Value", "Liquid Cash Earned"],
            "Amount (₹)": [remaining_inventory_value, cash_earned_value]
        })
        st.bar_chart(data=chart_df, x="Financial Dimension", y="Amount (₹)", use_container_width=True)
