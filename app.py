import base64
import json
import math
from datetime import datetime
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Yashasvi Executive Command", page_icon="💎", layout="wide")
st.title("💎 Yashasvi Imitations — Executive Command Hub")
st.write("---")

# --- INITIALIZE MULTI-PRODUCT SHOPPING CARTS & STAGING MEMORY ---
if "bangle_sales_cart" not in st.session_state:
    st.session_state.bangle_sales_cart = []
if "staged_bangle_purchases" not in st.session_state:
    st.session_state.staged_bangle_purchases = []
if "jewelry_sales_cart" not in st.session_state:
    st.session_state.jewelry_sales_cart = []
if "staged_jewelry_purchases" not in st.session_state:
    st.session_state.staged_jewelry_purchases = []

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
    inventory_worksheet = sheet.get_worksheet(1)  # Tab 2: General Inventory
    sales_worksheet = sheet.get_worksheet(2)      # Tab 3: Sales Log
    expense_worksheet = sheet.get_worksheet(3)    # Tab 4: Expense Log
    bangles_log_worksheet = sheet.get_worksheet(4) # Tab 5: Bangles Detailed Log

    # --- GENERAL INVENTORY ---
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

    # --- GENERAL SALES ---
    raw_sales_data = sales_worksheet.get_all_values()
    if raw_sales_data and len(raw_sales_data) > 0:
        sales_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_sales_data[0]]
        df_sales = pd.DataFrame(raw_sales_data[1:], columns=sales_headers)
        df_sales.columns = df_sales.columns.str.strip()
    else:
        df_sales = pd.DataFrame(columns=["Order ID", "Item Code", "Item Type", "Original Price (₹)", "Discount (%)", "Final Revenue (₹)", "Cost Price (₹)", "Timestamp"])

    # --- EXPENSES ---
    raw_exp_data = expense_worksheet.get_all_values()
    if raw_exp_data and len(raw_exp_data) > 0:
        exp_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_exp_data[0]]
        df_expenses = pd.DataFrame(raw_exp_data[1:], columns=exp_headers)
        df_expenses.columns = df_expenses.columns.str.strip()
    else:
        df_expenses = pd.DataFrame(columns=["Expense ID", "Category", "Business Segment", "Amount (₹)", "Description", "Timestamp"])

    # --- BANGLES DETAILED MASTER LOG ---
    raw_bangle_data = bangles_log_worksheet.get_all_values()
    if raw_bangle_data and len(raw_bangle_data) > 0:
        bangle_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_bangle_data[0]]
        df_bangles_detailed = pd.DataFrame(raw_bangle_data[1:], columns=bangle_headers)
        df_bangles_detailed.columns = df_bangles_detailed.columns.str.strip()
    else:
        df_bangles_detailed = pd.DataFrame(columns=["Log ID", "Transaction Type", "Bangle Name", "Colour", "Size", "Cost Price (₹)", "Selling Price (₹)", "Channel", "Shipping Cost (₹)", "Timestamp"])

except Exception as e:
    st.error(f"❌ Cloud Synchronization Unsuccessful: {e}")
    st.stop()

# --- STREAMLIT FREE-TEXT EXPENSE CLASSIFICATION ENGINE ---
def auto_classify_expense(description_text):
    desc = str(description_text).lower().strip()
    bangle_markers = ["bangle", "kavya", "ganapati", "ganpati", "delhivery", "shipment", "shipping", "bubble", "packing", "bangle box", "paper", "dandiya"]
    segment = "Jewelry"
    if any(marker in desc for marker in bangle_markers):
        segment = "Bangles"
        
    fixed_overhead_markers = ["ticket", "train", "bus", "cab", "auto", "fuel", "airbnb", "lodging", "hotel", "food", "snacks", "hanger", "mirror", "tray", "gimbal", "rent", "iphone", "decor", "flower", "sim", "maintenance", "clothes", "cash"]
    if any(marker in desc for marker in fixed_overhead_markers):
        category = "Fixed Operating Overhead"
    elif "ship" in desc or "delhivery" in desc or "pack" in desc or "bubble" in desc or "sticker" in desc or "card" in desc:
        category = "Variable Logistics & Fulfillment"
    elif "procure" in desc or "buying" in desc or "cost price" in desc or "stock in" in desc:
        category = "Direct Inventory Procurement"
    else:
        category = "General Operational Outflows"
    return segment, category

# --- HELPER FUNCTION: DYNAMIC COLUMN NAME RESOLVER ---
def resolve_column(df, keywords, default_name):
    for col in df.columns:
        if any(kw in col.lower() for kw in keywords):
            return col
    return default_name

# --- INVENTORY COLUMNS RESOLUTIONS ---
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

# --- SALES COLUMNS RESOLUTIONS ---
sales_id_col = resolve_column(df_sales, ["order id", "id"], "Order ID")
sales_code_col = resolve_column(df_sales, ["item code", "sku", "code"], "Item Code")
sales_type_col = resolve_column(df_sales, ["item type", "category", "model"], "Item Type")
sales_orig_col = resolve_column(df_sales, ["original price", "price"], "Original Price (₹)")
sales_discount_col = resolve_column(df_sales, ["discount"], "Discount (%)")
sales_rev_col = resolve_column(df_sales, ["revenue", "final", "selling price", "sp", "amount"], "Final Revenue (₹)")
sales_cost_col = resolve_column(df_sales, ["cost price", "buying price", "cp", "cost"], "Cost Price (₹)")
sales_ts_col = resolve_column(df_sales, ["timestamp", "date", "time"], "Timestamp")

for col_name in ["Order ID", "Item Code", "Item Type", "Original Price (₹)", "Discount (%)", "Final Revenue (₹)", "Cost Price (₹)", "Timestamp"]:
    if col_name not in df_sales.columns:
        df_sales[col_name] = 0.0 if "Price" in col_name or "Revenue" in col_name or "Cost" in col_name or "Discount" in col_name else ""
if not df_sales.empty:
    df_sales = df_sales[df_sales[sales_id_col].astype(str).str.strip() != ""]

# Standardize data matrices across frames
if "Business Segment" not in df_expenses.columns: df_expenses["Business Segment"] = "Jewelry"
if "Category" not in df_expenses.columns: df_expenses["Category"] = "General Operational Outflows"
if "Colour" not in df_bangles_detailed.columns: df_bangles_detailed["Colour"] = "Default"

if not df_expenses.empty: df_expenses = df_expenses[df_expenses["Expense ID"].astype(str).str.strip() != ""]
if not df_bangles_detailed.empty: df_bangles_detailed = df_bangles_detailed[df_bangles_detailed["Log ID"].astype(str).str.strip() != ""]

# --- PRE-COMPUTE GRANULAR BANGLES INVENTORY FOR THE METRICS ---
df_b_detailed_clean = df_bangles_detailed.copy()
if not df_b_detailed_clean.empty:
    df_b_detailed_clean["Bangle Name"] = df_b_detailed_clean["Bangle Name"].astype(str).str.strip().str.upper()
    df_b_detailed_clean["Colour"] = df_b_detailed_clean["Colour"].astype(str).str.strip().str.upper()
    df_b_detailed_clean["Size"] = df_b_detailed_clean["Size"].astype(str).str.strip()
    
    computed_bangle_inventory_list = []
    grouped_bangles = df_b_detailed_clean.groupby(["Bangle Name", "Colour", "Size"])
    for (b_name, b_col, b_sz), group in grouped_bangles:
        purchased_lot_volume = len(group[group["Transaction Type"] == "Purchase"])
        sold_lot_volume = len(group[group["Transaction Type"] == "Sale"])
        available_lot_volume = purchased_lot_volume - sold_lot_volume
        computed_bangle_inventory_list.append({
            "Model (Bangle Name)": b_name, "Colour Variant": b_col, "Size": b_sz,
            "Total Purchased": purchased_lot_volume, "Total Sold": sold_lot_volume, "Available Stock Volume": available_lot_volume
        })
    df_computed_bangles_master = pd.DataFrame(computed_bangle_inventory_list)
else:
    df_computed_bangles_master = pd.DataFrame(columns=["Model (Bangle Name)", "Colour Variant", "Size", "Total Purchased", "Total Sold", "Available Stock Volume"])

# Compute absolute total sums for high-level cards
global_bangle_units_available = int(df_computed_bangles_master["Available Stock Volume"].sum()) if not df_computed_bangles_master.empty else 0

# --- THE 5-PAGE RECONCILED RUNTIME CONTROL ---
p1, p2, p3, p4, p5 = st.tabs([
    "📈 1. Business Executive Dashboard",
    "⭕ 2. Bangles Stock & Query Desk",
    "🛒 3. Fast Checkout Terminal",
    "💸 4. Expense Control Ledger",
    "📦 5. Master Backends Database"
])

# ==============================================================================
# --- PAGE 1: BUSINESS EXECUTIVE DASHBOARD (WITH UNIT SUMMARY REVENUE CARDS) ---
# ==============================================================================
with p1:
    st.subheader("📊 Reconciled Multi-Channel Financial Engine")
    
    gen_sales_revenue = pd.to_numeric(df_sales[sales_rev_col], errors='coerce').sum()
    gen_sales_cogs = pd.to_numeric(df_sales[sales_cost_col], errors='coerce').sum()
    
    df_b_sales = df_bangles_detailed[df_bangles_detailed["Transaction Type"] == "Sale"]
    bangle_sales_revenue = pd.to_numeric(df_b_sales["Selling Price (₹)"], errors='coerce').sum()
    bangle_sales_cogs = pd.to_numeric(df_b_sales["Cost Price (₹)"], errors='coerce').sum()
    
    bangle_mask = df_expenses["Business Segment"].astype(str).str.lower().str.contains("bangle")
    jewelry_mask = df_expenses["Business Segment"].astype(str).str.lower().str.contains("jewel")
    
    bangle_logged_expenses = pd.to_numeric(df_expenses[bangle_mask]["Amount (₹)"], errors='coerce').sum()
    bangle_shipping_expenses = pd.to_numeric(df_b_sales["Shipping Cost (₹)"], errors='coerce').sum()
    bangle_total_outflow = bangle_logged_expenses + bangle_shipping_expenses
    
    jewelry_logged_expenses = pd.to_numeric(df_expenses[jewelry_mask]["Amount (₹)"], errors='coerce').sum()
    
    bangle_net_profit = bangle_sales_revenue - bangle_sales_cogs - bangle_total_outflow
    jewelry_net_profit = gen_sales_revenue - gen_sales_cogs - jewelry_logged_expenses
    
    met_c1, met_c2, met_c3 = st.columns(3)
    met_c1.metric("Gross Revenue Realized", f"₹{(gen_sales_revenue + bangle_sales_revenue):,.2f}")
    met_c2.metric("Total Operational Outflows", f"₹{(bangle_total_outflow + jewelry_logged_expenses):,.2f}")
    net_total_profit = bangle_net_profit + jewelry_net_profit
    met_c3.metric("Total Corporate Net Profit", f"₹{net_total_profit:,.2f}", 
                  delta="PROFITABLE NET" if net_total_profit >= 0 else "DEFICIT NET",
                  delta_color="normal" if net_total_profit >= 0 else "inverse")
    
    st.write("---")
    col_chan1, col_chan2 = st.columns(2)
    
    with col_chan1:
        st.markdown("### ⭕ Bangles Catalog Performance (Omnichannel)")
        
        # ADDED: Integrated unit tracking cards inside the executive overview panel
        ub1, ub2 = st.columns(2)
        ub1.metric("Bangles Units Sold", f"{len(df_b_sales)} Pcs")
        ub2.metric("Bangles Remaining Stock", f"{global_bangle_units_available} Pcs")
        
        st.metric("Bangles Total Receipts", f"₹{bangle_sales_revenue:,.2f}")
        b_online_count = len(df_b_sales[df_b_sales["Channel"].astype(str).str.lower().str.contains("online")])
        b_offline_count = len(df_b_sales[df_b_sales["Channel"].astype(str).str.lower().str.contains("offline")])
        st.caption(f"📦 Channel logs: **{b_online_count} Online** | **{b_offline_count} Offline Stall**")
        st.markdown(f"🔹 **Sunk Product COGS Value:** `₹{bangle_sales_cogs:,.2f}`")
        st.markdown(f"🔹 **Auto-Grouped Operations Cost:** `₹{bangle_logged_expenses:,.2f}`")
        st.markdown(f"🔹 **Fulfillment Shipping Sunk Cost:** `₹{bangle_shipping_expenses:,.2f}`")
        st.markdown(f"🏁 **Net Bangles Line Income:** `₹{bangle_net_profit:,.2f}`")
        
        b_fixed = pd.to_numeric(df_expenses[bangle_mask & (df_expenses["Category"] == "Fixed Operating Overhead")]["Amount (₹)"], errors='coerce').sum()
        b_var = pd.to_numeric(df_expenses[bangle_mask & (df_expenses["Category"] == "Variable Logistics & Fulfillment")]["Amount (₹)"], errors='coerce').sum() + bangle_shipping_expenses
        bangle_units_total = len(df_b_sales)
        
        if bangle_units_total > 0:
            avg_b_sp = bangle_sales_revenue / bangle_units_total
            avg_b_cp = bangle_sales_cogs / bangle_units_total
            avg_b_var = b_var / bangle_units_total
            b_contribution = avg_b_sp - avg_b_cp - avg_b_var
            if b_contribution > 0:
                bangle_bep = math.ceil(b_fixed / b_contribution) if b_fixed > 0 else 1
                st.success(f"📈 **Bangles Category Break-Even Point:** `{bangle_bep} units` sold.")
                b_progress = min(1.0, bangle_units_total / max(1, bangle_bep))
                st.progress(b_progress)
                st.caption(f"Category Progress: **{b_progress * 100:.1f}% met**")
            else:
                st.error("🚨 Margin Deficit: Variable costs per unit exceed retail prices.")
        else:
            st.info("Awaiting bangle transactions to map parameters.")

    with col_chan2:
        st.markdown("### 📿 Jewelry Catalog Performance (Stall Engine)")
        
        # Added symmetric piece matching metrics for jewelry lot catalogs
        jewelry_units_total = len(df_sales)
        uj1, uj2 = st.columns(2)
        uj1.metric("Jewelry Units Sold", f"{jewelry_units_total} Pcs")
        total_j_stock = int(pd.to_numeric(df_inventory[remaining_qty_col], errors='coerce').sum()) if not df_inventory.empty else 0
        uj2.metric("Jewelry Remaining Stock", f"{total_j_stock} Pcs")
        
        st.metric("Jewelry Total Receipts", f"₹{gen_sales_revenue:,.2f}")
        st.markdown(f"🔹 **Sunk Product COGS Value:** `₹{gen_sales_cogs:,.2f}`")
        st.markdown(f"🔹 **Auto-Grouped Operations Cost:** `₹{jewelry_logged_expenses:,.2f}`")
        st.markdown(f"🏁 **Net Jewelry Line Income:** `₹{jewelry_net_profit:,.2f}`")
        
        j_fixed = pd.to_numeric(df_expenses[jewelry_mask & (df_expenses["Category"] == "Fixed Operating Overhead")]["Amount (₹)"], errors='coerce').sum()
        
        if jewelry_units_total > 0:
            avg_j_sp = gen_sales_revenue / jewelry_units_total
            avg_j_cp = gen_sales_cogs / jewelry_units_total
            j_contribution = avg_j_sp - avg_j_cp
            if j_contribution > 0:
                jew_bep = math.ceil(j_fixed / j_contribution) if j_fixed > 0 else 1
                st.success(f"📈 **Jewelry Category Break-Even Point:** `{jew_bep} units` sold.")
                j_progress = min(1.0, jewelry_units_total / max(1, jew_bep))
                st.progress(j_progress)
                st.caption(f"Category Progress: **{j_progress * 100:.1f}% met**")
            else:
                st.error("🚨 Margin Deficit: Average unit product cost baseline exceeds unit sales prices.")
        else:
            st.info("Awaiting jewelry sales logs to map parameters.")

# ==============================================================================
# --- PAGE 2: BANGLES STOCK & QUERY DESK (WITH COMPREHENSIVE VOLUMES) ---
# ==============================================================================
with p2:
    st.subheader("⭕ Granular Bangles Color-Model Matrix & Query Terminal")
    
    # ADDED: Highly scannable high-level counter displaying total inventory on hand
    st.metric("Total Physical Bangle Stock Volume (All Variations Combined)", f"{global_bangle_units_available} Units Available")
    st.write("---")

    q_col1, q_col2 = st.columns([1, 2])
    with q_col1:
        st.markdown("#### 🔍 Interactive Query Lots Tool")
        with st.container(border=True):
            query_name = st.text_input("Enter Model / Bangle Name", placeholder="e.g. KAVYA BANGLES", key="q_b_n").strip().upper()
            query_color = st.text_input("Enter Colour Variant", placeholder="e.g. ROSE GOLD", key="q_b_c").strip().upper()
            query_size = st.text_input("Enter Size Dimension", placeholder="e.g. 2.6", key="q_b_s").strip()
            if st.button("Query Lot Availability Terminal ⚡", type="primary"):
                if not query_name or not query_color or not query_size:
                    st.warning("All fields are required.")
                else:
                    match_df = df_computed_bangles_master[
                        (df_computed_bangles_master["Model (Bangle Name)"] == query_name) &
                        (df_computed_bangles_master["Colour Variant"] == query_color) &
                        (df_computed_bangles_master["Size"] == query_size)
                    ]
                    if not match_df.empty:
                        available_stock_count = match_df.iloc[0]["Available Stock Volume"]
                        if available_stock_count > 0:
                            st.success(f"📦 Stock Verified! **`{available_stock_count} unit lots`** available.")
                        else:
                            st.error("❌ Out of Stock! 0 units remaining.")
                    else:
                        st.error("❌ Record Void! No matching entry tracked.")

    with q_col2:
        st.markdown("#### 🎨 Color & Model Distribution Matrix View")
        if not df_computed_bangles_master.empty:
            df_active_matrix_view = df_computed_bangles_master[df_computed_bangles_master["Available Stock Volume"] > 0]
            if not df_active_matrix_view.empty:
                df_pivot_matrix = df_active_matrix_view.pivot_table(index="Model (Bangle Name)", columns="Colour Variant", values="Available Stock Volume", aggfunc="sum", fill_value=0)
                st.dataframe(df_pivot_matrix, width="stretch")
            else:
                st.info("No active available stock lines found.")

    st.write("---")
    st.dataframe(df_computed_bangles_master, width="stretch", hide_index=True)

# ==============================================================================
# --- PAGE 3: FAST CHECKOUT TERMINAL ---
# ==============================================================================
with p3:
    st.subheader("🎯 Active Product Shopping Carts (Order-Level Financial Controls)")
    term_c1, term_c2 = st.columns(2)
    
    with term_c1:
        st.markdown("### ⭕ 1. Bangles Comma-Separated Desk")
        bangle_form_mode = st.radio("Select Action Category", options=["Purchase (Stock In)", "Add to Sales Cart (Stock Out)"], horizontal=True)
        f_b_name = st.text_input("Bangle Model Name", placeholder="e.g. KAVYA BANGLES").strip().upper()
        
        st.markdown("##### 📝 Input Variant Streams:")
        with st.form("bangle_cart_item_form", clear_on_submit=True):
            f_b_colors_str = st.text_input("Colours List", placeholder="pink, maroon, gold")
            f_b_sizes_str = st.text_input("Sizes List", placeholder="2.4, 2.6, 2.8")
            f_b_qtys_str = st.text_input("Quantities List", placeholder="1, 2, 1")
            f_b_cp_str = st.text_input("Cost Price (CP) List", placeholder="110")
            
            f_b_sp_str = ""
            if "Sales Cart" in bangle_form_mode:
                f_b_sp_str = st.text_input("Base Selling Price (SP) List", placeholder="150")
                
            if st.form_submit_button("Explode Variant Strings Into Cart List ➕"):
                if not f_b_name or not f_b_colors_str or not f_b_sizes_str or not f_b_qtys_str or not f_b_cp_str:
                    st.error("Model Name and all comma-separated fields are mandatory.")
                else:
                    try:
                        colors_parsed = [c.strip().upper() for c in f_b_colors_str.split(",") if c.strip()]
                        sizes_parsed = [s.strip() for s in f_b_sizes_str.split(",") if s.strip()]
                        qtys_parsed = [int(q.strip()) for q in f_b_qtys_str.split(",") if q.strip()]
                        cp_parts = [float(p.strip()) for p in f_b_cp_str.split(",") if p.strip()]
                        
                        if len(cp_parts) == 1: cp_parsed = cp_parts * len(colors_parsed)
                        else: cp_parsed = cp_parts
                            
                        if not (len(colors_parsed) == len(sizes_parsed) == len(qtys_parsed) == len(cp_parsed)):
                            st.error(f"❌ Length Mismatch! Check list fields entry count alignment bounds.")
                        else:
                            if "Purchase" in bangle_form_mode:
                                for c, s, q, cp in zip(colors_parsed, sizes_parsed, qtys_parsed, cp_parsed):
                                    st.session_state.staged_bangle_purchases.append({
                                        "Bangle Name": f_b_name, "Colour":
