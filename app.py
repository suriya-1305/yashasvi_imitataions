import base64
import json
from datetime import datetime
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Yashasvi Cloud Console", page_icon="💎", layout="wide")
st.title("💎 Yashasvi Imitations — Billing and Inventory Management")
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

try:
    sheet = client.open_by_key(SPREADSHEET_ID)
    
    # Map sheets dynamically by position (Tab 2 and Tab 3)
    inventory_worksheet = sheet.get_worksheet(1)
    sales_worksheet = sheet.get_worksheet(2)
    
    if inventory_worksheet is None or sales_worksheet is None:
        st.error("❌ Position Mapping Error: Your Google Sheet must have at least 3 tabs.")
        st.stop()

    # --- INVENTORY DATA INGESTION & AUTOMATIC SANITIZATION ---
    raw_inv_data = inventory_worksheet.get_all_values()
    
    # Auto-discover where the true header row starts (bypasses empty rows/titles)
    header_idx = 0
    for i, row in enumerate(raw_inv_data):
        row_cleaned = [str(cell).strip().lower() for cell in row]
        if "item code" in row_cleaned or "item type" in row_cleaned:
            header_idx = i
            break

    if raw_inv_data and len(raw_inv_data) > header_idx:
        # Sanitize headers of raw non-breaking spaces (\xa0)
        inv_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_inv_data[header_idx]]
        df_inventory = pd.DataFrame(raw_inv_data[header_idx + 1:], columns=inv_headers)
        df_inventory.columns = df_inventory.columns.str.strip()
    else:
        df_inventory = pd.DataFrame()

    # --- SALES DATA INGESTION ---
    raw_sales_data = sales_worksheet.get_all_values()
    if raw_sales_data and len(raw_sales_data) > 0:
        sales_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_sales_data[0]]
        df_sales = pd.DataFrame(raw_sales_data[1:], columns=sales_headers)
        df_sales.columns = df_sales.columns.str.strip()
    else:
        df_sales = pd.DataFrame(columns=["Order ID", "Item Code", "Item Type", "Original Price (₹)", "Discount (%)", "Final Revenue (₹)", "Timestamp"])

except Exception as e:
    st.error(f"❌ Failed to extract workbook dimensions: {e}")
    st.stop()

# --- DYNAMIC COLUMN NAME RESOLVER ---
def resolve_column(df, keywords, default_name):
    for col in df.columns:
        if any(kw in col.lower() for kw in keywords):
            return col
    return default_name

if not df_inventory.empty:
    item_code_col = resolve_column(df_inventory, ["item code", "sku"], "Item Code")
    item_type_col = resolve_column(df_inventory, ["item type", "category"], "Item Type")
    selling_price_col = resolve_column(df_inventory, ["selling", "price"], "Selling Price")
    total_col = resolve_column(df_inventory, ["total"], "Total")
    
    # CRITICAL FIX: Explicitly target "Remaining Quantity" case-insensitively, avoiding generic "Quantity"
    remaining_qty_col = None
    for col in df_inventory.columns:
        if "remaining" in col.lower():
            remaining_qty_col = col
            break
    if not remaining_qty_col:
        remaining_qty_col = resolve_column(df_inventory, ["qty", "quantity", "stock"], "Remaining Quantity")

    # Clean out empty spreadsheet artifact rows at the bottom
    df_inventory = df_inventory[df_inventory[item_code_col].astype(str).str.strip() != ""]
    df_inventory[item_code_col] = df_inventory[item_code_col].astype(str).str.strip().str.upper()
else:
    st.error("❌ The selected Inventory tab appears to have no data columns.")
    st.stop()

if not df_sales.empty and "Order ID" in df_sales.columns:
    df_sales = df_sales[df_sales["Order ID"].astype(str).str.strip() != ""]

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
    display_columns = [item_type_col, item_code_col, remaining_qty_col]
    available_cols = [col for col in display_columns if col in df_inventory.columns]
    
    total_units = int(pd.to_numeric(df_inventory[remaining_qty_col], errors='coerce').sum())
    st.metric(label="Total Volumetric Units in Stock", value=f"{total_units} units")
    
    st.dataframe(
        df_inventory[available_cols], 
        use_container_width=True, 
        hide_index=True,
        column_config={
            remaining_qty_col: st.column_config.NumberColumn("Quantity Available", width=140),
            item_code_col: st.column_config.TextColumn("Item Code", width=100),
            item_type_col: st.column_config.TextColumn("Item Type / Category", width=260)
        }
    )

# --- PAGE 2: ACTIVE ORDER BILLING ---
with p2:
    st.subheader("Checkout Counter Terminal")
    
    with st.form("checkout_form", clear_on_submit=True):
        sku_options = df_inventory[item_code_col].dropna().tolist()
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
                    row_idx = df_inventory[df_inventory[item_code_col] == sku].index[0]
                    stock_val = pd.to_numeric(df_inventory.at[row_idx, remaining_qty_col], errors='coerce')
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
                        row_idx = df_inventory[df_inventory[item_code_col] == sku].index[0]
                        current_stock = int(pd.to_numeric(df_inventory.at[row_idx, remaining_qty_col]))
                        
                        item_type_val = df_inventory.at[row_idx, item_type_col]
                        base_price_val = float(pd.to_numeric(df_inventory.at[row_idx, selling_price_col], errors='coerce'))
                        
                        final_selling_price = base_price_val * (1.0 - (actual_discount / 100.0))
                        total_bill_amount += final_selling_price
                        next_order_id = len(df_sales) + len(new_sales_entries) + 1
                        
                        # FIXED: Mutating ONLY remaining_qty_col, keeping 'Quantity' pristine
                        df_inventory.at[row_idx, remaining_qty_col] = str(current_stock - 1)
                        if total_col in df_inventory.columns:
                            df_inventory.at[row_idx, total_col] = str(int(df_inventory.at[row_idx, remaining_qty_col]) * base_price_val)
                        
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
        
        st.dataframe(
            df_sales.sort_values(by="Order ID", ascending=False), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Order ID": st.column_config.TextColumn("ID", width=60),
                "Item Code": st.column_config.TextColumn("Item Code", width=100),
                "Item Type": st.column_config.TextColumn("Item Type / Category", width=200),
                "Original Price (₹)": st.column_config.NumberColumn("Price", width=90),
                "Discount (%)": st.column_config.NumberColumn("Disc%", width=80),
                "Final Revenue (₹)": st.column_config.NumberColumn("Revenue", width=100),
                "Timestamp": st.column_config.TextColumn("Date & Time", width=160)
            }
        )

# --- PAGE 4: FINANCIAL HEALTH CHART ---
with p4:
    st.subheader("Asset Value Metrics Summary")
    if df_inventory.empty:
        st.info("Populate stock configurations to load the analytics charts.")
    else:
        sell_price = pd.to_numeric(df_inventory[selling_price_col], errors='coerce')
        rem_qty = pd.to_numeric(df_inventory[remaining_qty_col], errors='coerce')
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
