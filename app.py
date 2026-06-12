import base64
import json
import math
from datetime import datetime
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Yashasvi Cloud Console", page_icon="💎", layout="wide")
st.title("💎 Yashasvi Imitations — Executive Command Hub")
st.markdown("##### Connected Cloud Google Sheet ID: `1hcxENlBErHhNMMxuv_rdtqsSnXaRp5af2rhflrrwDBg`")
st.write("---")

# --- INITIALIZE MULTI-ROW STAGING BUFFERS ---
if "staged_bangle_purchases" not in st.session_state:
    st.session_state.staged_bangle_purchases = []
if "staged_bangle_sales" not in st.session_state:
    st.session_state.staged_bangle_sales = []

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
    
    # Map worksheets dynamically by position (Tabs 2, 3, 4, 5)
    inventory_worksheet = sheet.get_worksheet(1)  # Tab 2: Inventory
    sales_worksheet = sheet.get_worksheet(2)      # Tab 3: Sales Log
    expense_worksheet = sheet.get_worksheet(3)    # Tab 4: Expense Log
    
    # Safely find or initialize Tab 5 (Bangles Detailed Log)
    try:
        bangles_log_worksheet = sheet.get_worksheet(4)
        if bangles_log_worksheet is None:
            bangles_log_worksheet = sheet.add_worksheet(title="Bangles Detailed Log", rows="2000", cols="9")
            bangles_log_worksheet.update('A1', [["Log ID", "Transaction Type", "Bangle Name", "Size", "Cost Price (₹)", "Selling Price (₹)", "Channel", "Shipping Cost (₹)", "Timestamp"]])
    except Exception:
        bangles_log_worksheet = sheet.add_worksheet(title="Bangles Detailed Log", rows="2000", cols="9")
        bangles_log_worksheet.update('A1', [["Log ID", "Transaction Type", "Bangle Name", "Size", "Cost Price (₹)", "Selling Price (₹)", "Channel", "Shipping Cost (₹)", "Timestamp"]])

    # --- INVENTORY DATA SNAPSHOT ---
    raw_inv_data = inventory_worksheet.get_all_values()
    header_idx = 0
    for i, row in enumerate(raw_inv_data):
        row_cleaned = [str(cell).strip().lower() for cell in row]
        if "item code" in row_cleaned or "item type" in row_cleaned:
            header_idx = i
            break

    if raw_inv_data and len(raw_inv_data) > header_idx:
        inv_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_inv_data[header_idx]]
        df_inventory = pd.DataFrame(raw_inv_data[header_idx + 1:], columns=inv_headers)
        df_inventory.columns = df_inventory.columns.str.strip()
    else:
        df_inventory = pd.DataFrame()

    # --- SALES DATA SNAPSHOT ---
    raw_sales_data = sales_worksheet.get_all_values()
    if raw_sales_data and len(raw_sales_data) > 0:
        sales_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_sales_data[0]]
        df_sales = pd.DataFrame(raw_sales_data[1:], columns=sales_headers)
        df_sales.columns = df_sales.columns.str.strip()
    else:
        df_sales = pd.DataFrame(columns=["Order ID", "Item Code", "Item Type", "Original Price (₹)", "Discount (%)", "Final Revenue (₹)", "Cost Price (₹)", "Timestamp"])

    # --- EXPENSE DATA SNAPSHOT ---
    raw_exp_data = expense_worksheet.get_all_values()
    if raw_exp_data and len(raw_exp_data) > 0:
        exp_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_exp_data[0]]
        df_expenses = pd.DataFrame(raw_exp_data[1:], columns=exp_headers)
        df_expenses.columns = df_expenses.columns.str.strip()
    else:
        df_expenses = pd.DataFrame(columns=["Expense ID", "Category", "Amount (₹)", "Description", "Item Cost Price Mapping", "Timestamp"])

    # --- NEW: BANGLES DETAILED DATA SNAPSHOT ---
    raw_bangle_data = bangles_log_worksheet.get_all_values()
    if raw_bangle_data and len(raw_bangle_data) > 0:
        bangle_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_bangle_data[0]]
        df_bangles_detailed = pd.DataFrame(raw_bangle_data[1:], columns=bangle_headers)
        df_bangles_detailed.columns = df_bangles_detailed.columns.str.strip()
    else:
        df_bangles_detailed = pd.DataFrame(columns=["Log ID", "Transaction Type", "Bangle Name", "Size", "Cost Price (₹)", "Selling Price (₹)", "Channel", "Shipping Cost (₹)", "Timestamp"])

except Exception as e:
    st.error(f"❌ Failed to extract Google Sheet matrix blocks: {e}")
    st.stop()

# --- RESOLVE DYNAMIC COLUMN LABELS CASE-INSENSITIVELY ---
def resolve_column(df, keywords, default_name):
    for col in df.columns:
        if any(kw in col.lower() for kw in keywords):
            return col
    return default_name

if not df_inventory.empty:
    item_code_col = resolve_column(df_inventory, ["item code", "sku"], "Item Code")
    item_type_col = resolve_column(df_inventory, ["item type", "category"], "Item Type")
    selling_price_col = resolve_column(df_inventory, ["selling", "price", "sp"], "Selling Price")
    cost_price_col = resolve_column(df_inventory, ["cost price", "buying", "cp", "cost"], "Cost Price")
    total_col = resolve_column(df_inventory, ["total"], "Total")
    
    remaining_qty_col = None
    for col in df_inventory.columns:
        if "remaining" in col.lower():
            remaining_qty_col = col
            break
    if not remaining_qty_col:
        remaining_qty_col = resolve_column(df_inventory, ["qty", "quantity", "stock"], "Remaining Quantity")

    df_inventory = df_inventory[df_inventory[item_code_col].astype(str).str.strip() != ""]
    df_inventory[item_code_col] = df_inventory[item_code_col].astype(str).str.strip().str.upper()
else:
    st.error("❌ Inventory columns configuration is unreadable.")
    st.stop()

# Defensive column validation across datasets
if not df_sales.empty and "Order ID" in df_sales.columns:
    df_sales = df_sales[df_sales["Order ID"].astype(str).str.strip() != ""]
required_sales_cols = ["Order ID", "Item Code", "Item Type", "Original Price (₹)", "Discount (%)", "Final Revenue (₹)", "Cost Price (₹)", "Timestamp"]
for r_col in required_sales_cols:
    if r_col not in df_sales.columns:
        df_sales[r_col] = 0.0 if "Price" in r_col or "Revenue" in r_col or "Discount" in r_col else ""

if not df_expenses.empty and "Expense ID" in df_expenses.columns:
    df_expenses = df_expenses[df_expenses["Expense ID"].astype(str).str.strip() != ""]

if not df_bangles_detailed.empty and "Log ID" in df_bangles_detailed.columns:
    df_bangles_detailed = df_bangles_detailed[df_bangles_detailed["Log ID"].astype(str).str.strip() != ""]

# --- THE 7-PAGE STRATIFIED COMMAND STRUCTURE ---
p1, p2, p3, p4, p5, p6, p7 = st.tabs([
    "📦 1. General Stock Summary", 
    "🎯 2. General Order Billing", 
    "💸 3. Expense Ledger Form",
    "⭕ 4. Bangles Granular Terminal",
    "📊 5. Bangles Lot Analytics", 
    "📿 6. Chains & Rings Dashboard",
    "💰 7. Financial P&L Control Command"
])

# --- PAGE 1: LIVE STOCK DASHBOARD ---
with p1:
    st.subheader("Current Operational Stock Summary")
    display_columns = [item_type_col, item_code_col, cost_price_col, selling_price_col, remaining_qty_col]
    available_cols = [col for col in display_columns if col in df_inventory.columns]
    
    total_units = int(pd.to_numeric(df_inventory[remaining_qty_col], errors='coerce').sum())
    st.metric(label="Total Volumetric Units in Stock", value=f"{total_units} units")
    st.dataframe(
        df_inventory[available_cols], width="stretch", hide_index=True,
        column_config={
            remaining_qty_col: st.column_config.NumberColumn("Quantity Available", width=140),
            item_code_col: st.column_config.TextColumn("Item Code", width=100),
            cost_price_col: st.column_config.NumberColumn("Cost Price (₹)", width=110),
            selling_price_col: st.column_config.NumberColumn("Selling Price (₹)", width=120),
            item_type_col: st.column_config.TextColumn("Item Type / Category", width=260)
        }
    )

# --- PAGE 2: ACTIVE ORDER BILLING ---
with p2:
    st.subheader("Checkout Counter Terminal")
    with st.form("checkout_form", clear_on_submit=True):
        sku_options = df_inventory[item_code_col].dropna().tolist()
        chosen_skus = st.multiselect("Select Target Item Code(s)", options=sku_options)
        discount_pct = st.number_input("Applied Discount Percentage (%)", min_value=0.0, max_value=100.0, value=None, step=5.0, placeholder="Type discount percentage (leave empty for 0%)")
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
                        base_cost_val = float(pd.to_numeric(df_inventory.at[row_idx, cost_price_col], errors='coerce')) if cost_price_col in df_inventory.columns else 0.0
                        
                        final_selling_price = base_price_val * (1.0 - (actual_discount / 100.0))
                        total_bill_amount += final_selling_price
                        next_order_id = len(df_sales) + len(new_sales_entries) + 1
                        
                        df_inventory.at[row_idx, remaining_qty_col] = str(current_stock - 1)
                        if total_col in df_inventory.columns:
                            df_inventory.at[row_idx, total_col] = str(int(df_inventory.at[row_idx, remaining_qty_col]) * base_price_val)
                        
                        new_sales_entries.append({
                            "Order ID": next_order_id, "Item Code": sku, "Item Type": item_type_val,
                            "Original Price (₹)": base_price_val, "Discount (%)": actual_discount,
                            "Final Revenue (₹)": final_selling_price, "Cost Price (₹)": base_cost_val, "Timestamp": timestamp_str
                        })
                    
                    if new_sales_entries:
                        df_new_sales = pd.DataFrame(new_sales_entries)
                        df_sales = pd.concat([df_sales, df_new_sales], ignore_index=True)
                    
                    try:
                        inventory_worksheet.clear()
                        inventory_worksheet.update('A1', [df_inventory.columns.values.tolist()] + df_inventory.astype(str).values.tolist())
                        sales_worksheet.clear()
                        sales_worksheet.update('A1', [df_sales.columns.values.tolist()] + df_sales.astype(str).values.tolist())
                        st.success(f"Cloud Sync Successful! Total Bill: ₹{total_bill_amount:,.2f}")
                        st.rerun()
                    except Exception as sheet_err:
                        st.error(f"Cloud update failed: {sheet_err}")

# --- PAGE 3: EXPENSE LEDGER FORM ---
with p3:
    st.subheader("Stall Ledger & Outflow Entry Form")
    with st.form("expense_form", clear_on_submit=True):
        exp_cat = st.selectbox("Expense Allocation Category", options=[
            "Travel & Logistics (Train/Bus/Cabs/Fuel)", 
            "Free Shipping Sunk Costs (Delhivery/Logistics)", 
            "Stall Setup & Accessories (Hangers/Mirrors/Decor)",
            "Electronics & Equipment Rental (iPhone/Gimbal)",
            "Packaging & Branding (Boxes/Bubble Wrap/Stickers)",
            "Lodging & Food (Airbnb/Snacks)", 
            "Operations & Telecom Maintenance (SIM cards)",
            "Direct Lot Material Procurement",
            "Miscellaneous Outflows"
        ])
        exp_amt = st.number_input("Transaction Amount (₹)", min_value=0.0, step=50.0, format="%.2f")
        exp_desc = st.text_input("Expense Memo / Description", placeholder="e.g. Train ticket from BLR to HYD, Shipment - kavya, iPhone 17 pro rent 3 days")
        submit_expense = st.form_submit_button("Commit Outflow Entry to Google Sheet 💸")
        
        if submit_expense:
            if exp_amt <= 0:
                st.error("Transaction rejected: Outflow value must be greater than zero.")
            else:
                next_exp_id = len(df_expenses) + 1
                exp_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                new_row = {
                    "Expense ID": next_exp_id, "Category": exp_cat, "Amount (₹)": exp_amt,
                    "Description": exp_desc, "Item Cost Price Mapping": "Operational Outflow", "Timestamp": exp_ts
                }
                df_expenses = pd.concat([df_expenses, pd.DataFrame([new_row])], ignore_index=True)
                
                try:
                    expense_worksheet.clear()
                    expense_worksheet.update('A1', [df_expenses.columns.values.tolist()] + df_expenses.astype(str).values.tolist())
                    st.success(f"Expense logged securely: ₹{exp_amt:,.2f} assigned to {exp_cat}")
                    st.rerun()
                except Exception as ex_err:
                    st.error(f"Failed to log expense out: {ex_err}")

    st.write("---")
    st.subheader("Historical Expense Records")
    if df_expenses.empty:
        st.info("No corporate cash outflows registered yet.")
    else:
        st.dataframe(df_expenses.sort_values(by="Expense ID", ascending=False), width="stretch", hide_index=True)

# --- PAGE 4: NEW BANGLES GRANULAR TERMINAL (TAB 5 LOOKUP) ---
with p4:
    st.subheader("Isolated Bangles Granular Terminal (Batch Procurement & Checkout Logs)")
    
    sub_col1, sub_col2 = st.columns(2)
    
    with sub_col1:
        st.markdown("#### 📦 1. Multiple Data Entry: Staging Procurement (Purchases)")
        with st.form("bangle_purchase_form", clear_on_submit=True):
            p_name = st.selectbox("Bangle Selection", options=["Jai Ganapati Bangles", "Kavya Bangles", "Premium Glass Bangles", "Customized Handmade Bangles", "Other Bangle Lots"])
            p_size = st.text_input("Size Dimension", placeholder="e.g. 2.4, 2.6, 2.8")
            p_cp = st.number_input("Unit Cost Price (CP) (₹)", min_value=0.0, step=10.0, format="%.2f")
            add_p_stage = st.form_submit_button("Stage Purchase Row ➕")
            
            if add_p_stage:
                if p_cp <= 0 or not p_size:
                    st.error("Provide a valid size and cost price configuration.")
                else:
                    st.session_state.staged_bangle_purchases.append({
                        "Transaction Type": "Purchase", "Bangle Name": p_name, "Size": p_size,
                        "Cost Price (₹)": p_cp, "Selling Price (₹)": 0.0, "Channel": "N/A", "Shipping Cost (₹)": 0.0
                    })
                    st.toast("Purchase row staged successfully!")

        # Handle Staged Purchases Display and Cloud Sync Action
        if st.session_state.staged_bangle_purchases:
            st.markdown("##### Staged Purchases Preview List")
            df_p_stage = pd.DataFrame(st.session_state.staged_bangle_purchases)
            st.dataframe(df_p_stage, width="stretch", hide_index=True)
            
            c_p_btn1, c_p_btn2 = st.columns(2)
            if c_p_btn1.button("Clear Purchase Staging List 🗑️"):
                st.session_state.staged_bangle_purchases = []
                st.rerun()
                
            if c_p_btn2.button("Commit Staged Purchases to Cloud Sheet 🚀", type="primary"):
                cloud_rows = []
                current_count = len(df_bangles_detailed)
                ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                for entry in st.session_state.staged_bangle_purchases:
                    current_count += 1
                    cloud_rows.append([
                        current_count, entry["Transaction Type"], entry["Bangle Name"], entry["Size"],
                        entry["Cost Price (₹)"], entry["Selling Price (₹)"], entry["Channel"], entry["Shipping Cost (₹)"], ts_now
                    ])
                try:
                    bangles_log_worksheet.append_rows(cloud_rows)
                    st.session_state.staged_bangle_purchases = []
                    st.success("All purchases saved permanently to Google Sheets!")
                    st.rerun()
                except Exception as cloud_err:
                    st.error(f"Cloud update failed: {cloud_err}")

    with sub_col2:
        st.markdown("#### 💰 2. Multiple Data Entry: Staging Checkout Logs (Sales)")
        with st.form("bangle_sale_form", clear_on_submit=True):
            s_name = st.selectbox("Bangle Selection", options=["Jai Ganapati Bangles", "Kavya Bangles", "Premium Glass Bangles", "Customized Handmade Bangles", "Other Bangle Lots"])
            s_size = st.text_input("Size Dimension", placeholder="e.g. 2.4, 2.6, 2.8")
            s_sp = st.number_input("Selling Price (SP) (₹)", min_value=0.0, step=10.0, format="%.2f")
            s_cp = st.number_input("Associated Cost Price (CP) (₹)", min_value=0.0, step=10.0, format="%.2f", help="Matches CP to determine product profit accurately")
            s_channel = st.radio("Sales Operations Channel", options=["Offline Stall", "Online Order"], horizontal=True)
            
            s_ship = 0.0
            if s_channel == "Online Order":
                s_ship = st.number_input("Free Shipping Cost Sunk Weight (₹)", min_value=0.0, step=10.0, format="%.2f")
                
            add_s_stage = st.form_submit_button("Stage Sale Row ➕")
            
            if add_s_stage:
                if s_sp <= 0 or not s_size:
                    st.error("Provide a valid size and selling price configuration.")
                else:
                    st.session_state.staged_bangle_sales.append({
                        "Transaction Type": "Sale", "Bangle Name": s_name, "Size": s_size,
                        "Cost Price (₹)": s_cp, "Selling Price (₹)": s_sp, "Channel": s_channel, "Shipping Cost (₹)": s_ship
                    })
                    st.toast("Sale row staged successfully!")

        # Handle Staged Sales Display and Cloud Sync Action
        if st.session_state.staged_bangle_sales:
            st.markdown("##### Staged Sales Preview List")
            df_s_stage = pd.DataFrame(st.session_state.staged_bangle_sales)
            st.dataframe(df_s_stage, width="stretch", hide_index=True)
            
            c_s_btn1, c_s_btn2 = st.columns(2)
            if c_s_btn1.button("Clear Sales Staging List 🗑️"):
                st.session_state.staged_bangle_sales = []
                st.rerun()
                
            if c_s_btn2.button("Commit Staged Sales to Cloud Sheet 🚀", type="primary"):
                cloud_rows = []
                current_count = len(df_bangles_detailed)
                ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                for entry in st.session_state.staged_bangle_sales:
                    current_count += 1
                    cloud_rows.append([
                        current_count, entry["Transaction Type"], entry["Bangle Name"], entry["Size"],
                        entry["Cost Price (₹)"], entry["Selling Price (₹)"], entry["Channel"], entry["Shipping Cost (₹)"], ts_now
                    ])
                try:
                    bangles_log_worksheet.append_rows(cloud_rows)
                    st.session_state.staged_bangle_sales = []
                    st.success("All sales saved permanently to Google Sheets!")
                    st.rerun()
                except Exception as cloud_err:
                    st.error(f"Cloud update failed: {cloud_err}")

    st.write("---")
    st.subheader("Live Historical Log View (Tab 5 Master Data Backup)")
    if df_bangles_detailed.empty:
        st.info("No logs generated inside Tab 5 yet.")
    else:
        st.dataframe(df_bangles_detailed.sort_values(by="Log ID", ascending=False), width="stretch", hide_index=True)

# --- PAGE 5: BANGLES LOT DYNAMICS ANALYTICS ---
with p5:
    st.subheader("Lot B: Consolidated Bangles Performance Analytics")
    
    # Calculate across general log + new isolated granular log
    df_gen_bangles = df_sales[df_sales["Item Type"].astype(str).str.lower().str.contains("bangle")]
    df_det_bangles_sales = df_bangles_detailed[df_bangles_detailed["Transaction Type"] == "Sale"]
    
    gen_bangle_rev = pd.to_numeric(df_gen_bangles["Final Revenue (₹)"], errors='coerce').sum()
    gen_bangle_cost = pd.to_numeric(df_gen_bangles["Cost Price (₹)"], errors='coerce').sum()
    
    det_bangle_rev = pd.to_numeric(df_det_bangles_sales["Selling Price (₹)"], errors='coerce').sum()
    det_bangle_cost = pd.to_numeric(df_det_bangles_sales["Cost Price (₹)"], errors='coerce').sum()
    det_bangle_shipping = pd.to_numeric(df_det_bangles_sales["Shipping Cost (₹)"], errors='coerce').sum()
    
    total_bangles_combined_revenue = gen_bangle_rev + det_bangle_rev
    total_bangles_combined_cost_basis = gen_bangle_cost + det_bangle_cost
    
    bc1, bc2, bc3 = st.columns(3)
    bc1.metric("Total Bangle Units Discharged", f"{len(df_gen_bangles) + len(df_det_bangles_sales)} Pcs")
    bc2.metric("Gross Bangles Receipts", f"₹{total_bangles_combined_revenue:,.2f}")
    bc3.metric("Bangles Specific Net Sunk Product Margin", f"₹{(total_bangles_combined_revenue - total_bangles_combined_cost_basis - det_bangle_shipping):,.2f}")

    st.markdown("#### Granular Bangle Sales Stream (Tab 5 Isolation Feed)")
    if df_det_bangles_sales.empty:
        st.info("No granular bangle checkouts executed via the Staging form yet.")
    else:
        st.dataframe(df_det_bangles_sales.sort_values(by="Log ID", ascending=False), width="stretch", hide_index=True)

# --- PAGE 6: CHAINS & RINGS DASHBOARD (LOT A) ---
with p6:
    st.subheader("Lot A: Necklaces, Chains, Bracelets & Rings Analytics")
    df_sales_jewelry = df_sales[~df_sales["Item Type"].astype(str).str.lower().str.contains("bangle")]
    
    if df_sales_jewelry.empty:
        st.info("No jewelry lots sales registered in this tracking frame.")
    else:
        jew_rev = pd.to_numeric(df_sales_jewelry["Final Revenue (₹)"], errors='coerce').sum()
        jew_cost = pd.to_numeric(df_sales_jewelry["Cost Price (₹)"], errors='coerce').sum()
        jew_margin = jew_rev - jew_cost
        
        cj1, cj2, cj3 = st.columns(3)
        cj1.metric("Jewelry Units Sold", f"{len(df_sales_jewelry)} Pcs")
        cj2.metric("Gross Jewelry Revenue", f"₹{jew_rev:,.2f}")
        cj3.metric("Product Gross Margin", f"₹{jew_margin:,.2f}")
        
        st.markdown("#### Lot A Sales Ingestion Feed")
        st.dataframe(df_sales_jewelry.sort_values(by="Order ID", ascending=False), width="stretch", hide_index=True)

# --- PAGE 7: RECONCILED P&L COMMAND ENGINE WITH BALANCED TAB 5 INTEGRATION ---
with p7:
    st.subheader("Comprehensive Reconciled Financial Engine")
    
    # 1. Base Revenue calculations (Tab 3 General + Tab 5 Detailed Bangle Sales)
    base_sales_revenue = pd.to_numeric(df_sales["Final Revenue (₹)"], errors='coerce').sum()
    bangles_granular_sales_revenue = pd.to_numeric(df_bangles_detailed[df_bangles_detailed["Transaction Type"] == "Sale"]["Selling Price (₹)"], errors='coerce').sum()
    reconciled_gross_revenue = base_sales_revenue + bangles_granular_sales_revenue
    
    # 2. Base Product Sunk Cost Basis (Tab 3 General Cost + Tab 5 Detailed Bangle Sales Cost)
    base_product_cogs = pd.to_numeric(df_sales["Cost Price (₹)"], errors='coerce').sum()
    bangles_granular_product_cogs = pd.to_numeric(df_bangles_detailed[df_bangles_detailed["Transaction Type"] == "Sale"]["Cost Price (₹)"], errors='coerce').sum()
    reconciled_total_cogs = base_product_cogs + bangles_granular_product_cogs
    
    # 3. Operations Expenses (Tab 4 General Operational Outflows + Tab 5 Detailed Purchases + Tab 5 Detailed Sunk Shipping Costs)
    base_operational_expenses = pd.to_numeric(df_expenses["Amount (₹)"], errors='coerce').sum()
    bangles_granular_procurement_expenses = pd.to_numeric(df_bangles_detailed[df_bangles_detailed["Transaction Type"] == "Purchase"]["Cost Price (₹)"], errors='coerce').sum()
    bangles_granular_online_shipping_burden = pd.to_numeric(df_bangles_detailed[df_bangles_detailed["Transaction Type"] == "Sale"]["Shipping Cost (₹)"], errors='coerce').sum()
    reconciled_total_expenses = base_operational_expenses + bangles_granular_procurement_expenses + bangles_granular_online_shipping_burden
    
    # Final Balanced Financial Equation Calculations
    gross_operating_profit = reconciled_gross_revenue - reconciled_total_cogs
    net_balanced_profit_loss = gross_operating_profit - reconciled_total_expenses
    
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("Gross Sales Receipts", f"₹{reconciled_gross_revenue:,.2f}")
    rc2.metric("Total Product Sunk CP (COGS)", f"₹{reconciled_total_cogs:,.2f}")
    rc3.metric("Reconciled Expenses & Shipping", f"₹{reconciled_total_expenses:,.2f}")
    
    if net_balanced_profit_loss >= 0:
        rc4.metric("Net Profit Margin (Take Home)", f"₹{net_balanced_profit_loss:,.2f}", delta="PROFITABLE STALL MARGIN")
    else:
        rc4.metric("Net Profit Margin (Take Home)", f"₹{net_balanced_profit_loss:,.2f}", delta="- LOSS SNAPSHOT", delta_color="inverse")
        
    st.write("---")
    st.subheader("Free Shipping & Structural Break-Even Analytics Dashboard")
    
    # Break down costs dynamically for break-even charts
    fixed_operating_categories = ["Stall Setup", "Electronics", "Lodging", "Operations", "Miscellaneous"]
    
    structural_fixed_overhead = 0.0
    variable_logistics_overhead = bangles_granular_online_shipping_burden
    
    for _, row in df_expenses.iterrows():
        cat_lower = str(row["Category"]).lower()
        amt_val = pd.to_numeric(row["Amount (₹)"], errors='coerce')
        if pd.isna(amt_val): continue
        if any(f_c.lower() in cat_lower for f_c in fixed_operating_categories):
            structural_fixed_overhead += amt_val
        else:
            variable_logistics_overhead += amt_val
            
    total_reconciled_sold_units = len(df_sales) + len(df_bangles_detailed[df_bangles_detailed["Transaction Type"] == "Sale"])
    
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        st.markdown("#### Reconciled Cost Structure Allocation")
        st.markdown(f"🔹 **Fixed Operating Baseline Overhead:** `₹{structural_fixed_overhead:,.2f}` *(Stall setup, travel tickets, SIMs)*")
        st.markdown(f"🔹 **Sunk Free Shipping & Logistics Burden:** `₹{variable_logistics_overhead:,.2f}` *(Delhivery, packaging boxes)*")
        st.markdown(f"🔹 **Bangles Inventory Restocking Outflow:** `₹{bangles_granular_procurement_expenses:,.2f}` *(Direct material procurement values)*")
        
        if total_reconciled_sold_units > 0:
            avg_sp = reconciled_gross_revenue / total_reconciled_sold_units
            avg_cp = reconciled_total_cogs / total_reconciled_sold_units
            avg_ship_cost = variable_logistics_overhead / total_reconciled_sold_units
            unit_contribution_margin = avg_sp - avg_cp - avg_ship_cost
            
            st.markdown(f"🔹 **Average Sale Price (SP) per Pc:** `₹{avg_sp:,.2f}`")
            st.markdown(f"🔹 **Average Base Cost (CP) per Pc:** `₹{avg_cp:,.2f}`")
            st.markdown(f"🔹 **Average Free Shipping Sunk Burden per Pc:** `₹{avg_ship_cost:,.2f}`")
            st.markdown(f"🔹 **True Net Unit Contribution Margin:** `₹{unit_contribution_margin:,.2f}`")
        else:
            unit_contribution_margin = 0.0
            st.warning("⚠️ Log item sale units across dashboards to calculate contribution margins.")
            
    with b_col2:
        st.markdown("#### Structural Breakeven Milestones")
        if unit_contribution_margin > 0:
            units_to_break_even = math.ceil(structural_fixed_overhead / unit_contribution_margin)
            st.info(f"📈 **Break-Even Target Volume:** `{units_to_break_even} total units` must be sold across catalogs to completely offset your fixed structural investments.")
            
            progress_ratio = min(1.0, total_reconciled_sold_units / max(1, units_to_break_even))
            st.progress(progress_ratio)
            st.markdown(f"🎯 *Current Run Clearance Progress:* **{progress_ratio * 100:.1f}% completed** ({total_reconciled_sold_units} / {units_to_break_even} units cleared).")
        else:
            if total_reconciled_sold_units > 0:
                st.error("🚨 Margin Deficit: Your variable product costs combined with free shipping overhead exceed your average unit sales receipts. Re-evaluate base lot prices.")
            else:
                st.info("Log your active checkout units to calculate your exact breakeven volume progress runways.")
