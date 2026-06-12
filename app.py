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
st.title("💎 Yashasvi Imitations — Hub Console")
st.write("---")

# --- INITIALIZE MULTI-ROW LOCAL STATE STAGING BUFFERS ---
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
    inventory_worksheet = sheet.get_worksheet(1)  # Tab 2: General Inventory
    sales_worksheet = sheet.get_worksheet(2)      # Tab 3: Sales Log
    expense_worksheet = sheet.get_worksheet(3)    # Tab 4: Expense Log
    
    # Safely find or initialize Tab 5 with "Colour" header injection
    try:
        bangles_log_worksheet = sheet.get_worksheet(4)
        if bangles_log_worksheet is None:
            bangles_log_worksheet = sheet.add_worksheet(title="Bangles Detailed Log", rows="2000", cols="10")
            bangles_log_worksheet.update('A1', [["Log ID", "Transaction Type", "Bangle Name", "Colour", "Size", "Cost Price (₹)", "Selling Price (₹)", "Channel", "Shipping Cost (₹)", "Timestamp"]])
    except Exception:
        bangles_log_worksheet = sheet.add_worksheet(title="Bangles Detailed Log", rows="2000", cols="10")
        bangles_log_worksheet.update('A1', [["Log ID", "Transaction Type", "Bangle Name", "Colour", "Size", "Cost Price (₹)", "Selling Price (₹)", "Channel", "Shipping Cost (₹)", "Timestamp"]])

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

# --- DEFENSIVE DATA NORMALIZATION ---
# Inject business segment and colour columns if legacy schemas missing them
if "Business Segment" not in df_expenses.columns:
    df_expenses["Business Segment"] = "Jewelry (Stall)"
if "Colour" not in df_bangles_detailed.columns:
    df_bangles_detailed["Colour"] = "Default"

# Standardize data formatting
for df in [df_sales, df_expenses, df_bangles_detailed]:
    df.columns = df.columns.str.strip()

# --- THE 5-PAGE RECONCILED HIGH-SPEED LAYOUT ---
p1, p2, p3, p4, p5 = st.tabs([
    "📈 1. Business Executive Dashboard",
    "⭕ 2. Bangles Stock & Query Desk",
    "🎯 3. Fast Checkout Terminal",
    "💸 4. Expense Control Ledger",
    "📦 5. Master Backends Database"
])

# ==============================================================================
# --- PAGE 1: BUSINESS EXECUTIVE DASHBOARD (THE FINANCIAL COMMAND CENTER) ---
# ==============================================================================
with p1:
    st.subheader("📊 Reconciled Multi-Channel Financial Engine")
    
    # Ingest baseline financial values securely
    gen_sales_revenue = pd.to_numeric(df_sales["Final Revenue (₹)"], errors='coerce').sum()
    gen_sales_cogs = pd.to_numeric(df_sales["Cost Price (₹)"], errors='coerce').sum()
    
    df_b_sales = df_bangles_detailed[df_bangles_detailed["Transaction Type"] == "Sale"]
    df_b_purchases = df_bangles_detailed[df_bangles_detailed["Transaction Type"] == "Purchase"]
    
    bangle_sales_revenue = pd.to_numeric(df_b_sales["Selling Price (₹)"], errors='coerce').sum()
    bangle_sales_cogs = pd.to_numeric(df_b_sales["Cost Price (₹)"], errors='coerce').sum()
    
    # Segmented operational expenses
    bangle_logged_expenses = pd.to_numeric(df_expenses[df_expenses["Business Segment"] == "Bangles (Online)"]["Amount (₹)"], errors='coerce').sum()
    bangle_shipping_expenses = pd.to_numeric(df_b_sales["Shipping Cost (₹)"], errors='coerce').sum()
    total_bangle_expenses = bangle_logged_expenses + bangle_shipping_expenses + pd.to_numeric(df_b_purchases["Cost Price (₹)"], errors='coerce').sum()
    
    jewelry_logged_expenses = pd.to_numeric(df_expenses[df_expenses["Business Segment"] == "Jewelry (Stall)"]["Amount (₹)"], errors='coerce').sum()
    
    # Channel calculations
    bangle_net_profit = bangle_sales_revenue - bangle_sales_cogs - (bangle_logged_expenses + bangle_shipping_expenses)
    jewelry_net_profit = gen_sales_revenue - gen_sales_cogs - jewelry_logged_expenses
    
    # Main corporate KPI display cards
    met_c1, met_c2, met_c3 = st.columns(3)
    met_c1.metric("Gross Revenue Realized", f"₹{(gen_sales_revenue + bangle_sales_revenue):,.2f}")
    met_c2.metric("Total Operational Outflows", f"₹{(bangle_logged_expenses + bangle_shipping_expenses + jewelry_logged_expenses):,.2f}")
    net_total_profit = bangle_net_profit + jewelry_net_profit
    met_c3.metric("Total Corporate Net Profit", f"₹{net_total_profit:,.2f}", 
                  delta="PROFITABLE NET" if net_total_profit >= 0 else "DEFICIT NET",
                  delta_color="normal" if net_total_profit >= 0 else "inverse")
    
    st.write("---")
    
    # Split channel performance layout columns
    col_chan1, col_chan2 = st.columns(2)
    
    with col_chan1:
        st.markdown("### ⭕ Bangles Lot Performance (Online)")
        st.write("⏱️ *Operational window timeline: 1 Month active tracking*")
        st.metric("Bangles Revenue Stream", f"₹{bangle_sales_revenue:,.2f}")
        st.markdown(f"🔹 **Sunk Product COGS Value:** `₹{bangle_sales_cogs:,.2f}`")
        st.markdown(f"🔹 **Isolated Logged Expenses:** `₹{bangle_logged_expenses:,.2f}`")
        st.markdown(f"🔹 **Free Shipping Cost Burden:** `₹{bangle_shipping_expenses:,.2f}`")
        st.markdown(f"🏁 **Net Channel Income:** `₹{bangle_net_profit:,.2f}`")
        
        # Break-even processing logic
        bangle_units_sold = len(df_b_sales)
        if bangle_units_sold > 0:
            avg_bangle_sp = bangle_sales_revenue / bangle_units_sold
            avg_bangle_cp = bangle_sales_cogs / bangle_units_sold
            avg_bangle_ship = bangle_shipping_expenses / bangle_units_sold
            bangle_unit_contribution = avg_bangle_sp - avg_bangle_cp - avg_bangle_ship
            
            if bangle_unit_contribution > 0:
                bangle_bep_volume = math.ceil(bangle_logged_expenses / bangle_unit_contribution)
                st.success(f"📈 **Online Bangles Break-Even Target Point:** `{bangle_bep_volume} units` sold.")
                bangle_progress = min(1.0, bangle_units_sold / max(1, bangle_bep_volume))
                st.progress(bangle_progress)
                st.caption(f"Progress execution: **{bangle_progress * 100:.1f}% met** ({bangle_units_sold} / {bangle_bep_volume} units)")
            else:
                st.error("🚨 Margin Deficit: Sunk unit product acquisition and shipping costs exceed unit price.")
        else:
            st.info("Awaiting initial online bangle order entry logs to analyze break-even parameters.")

    with col_chan2:
        st.markdown("### 📿 Jewelry Catalog Performance (Stall)")
        st.write("⏱️ *Operational window timeline: Physical Jayanagar Stall deployment*")
        st.metric("Jewelry Revenue Stream", f"₹{gen_sales_revenue:,.2f}")
        st.markdown(f"🔹 **Sunk Product COGS Value:** `₹{gen_sales_cogs:,.2f}`")
        st.markdown(f"🔹 **Isolated Logged Expenses:** `₹{jewelry_logged_expenses:,.2f}`")
        st.markdown(f"🏁 **Net Channel Income:** `₹{jewelry_net_profit:,.2f}`")
        
        # Break-even processing logic
        jewelry_units_sold = len(df_sales)
        if jewelry_units_sold > 0:
            avg_jew_sp = gen_sales_revenue / jewelry_units_sold
            avg_jew_cp = gen_sales_cogs / jewelry_units_sold
            jew_unit_contribution = avg_jew_sp - avg_jew_cp
            
            if jew_unit_contribution > 0:
                jew_bep_volume = math.ceil(jewelry_logged_expenses / jew_unit_contribution)
                st.success(f"📈 **Stall Jewelry Break-Even Target Point:** `{jew_bep_volume} units` sold.")
                jew_progress = min(1.0, jewelry_units_sold / max(1, jew_bep_volume))
                st.progress(jew_progress)
                st.caption(f"Progress execution: **{jew_progress * 100:.1f}% met** ({jewelry_units_sold} / {jew_bep_volume} units)")
            else:
                st.error("🚨 Margin Deficit: Average unit production cost baseline exceeds unit sales prices.")
        else:
            st.info("Awaiting initial stall order checks to analyze break-even metrics.")

# ==============================================================================
# --- PAGE 2: BANGLES STOCK & QUERY DESK (COLOR LOGIC & MATRIX OVERVIEW) ---
# ==============================================================================
with p2:
    st.subheader("⭕ Granular Bangles Color-Model Matrix & Query Terminal")
    
    # Parse dynamic quantities across lines
    df_b_detailed_clean = df_bangles_detailed.copy()
    if not df_b_detailed_clean.empty:
        df_b_detailed_clean["Bangle Name"] = df_b_detailed_clean["Bangle Name"].astype(str).str.strip().str.upper()
        df_b_detailed_clean["Colour"] = df_b_detailed_clean["Colour"].astype(str).str.strip().str.upper()
        df_b_detailed_clean["Size"] = df_b_detailed_clean["Size"].astype(str).str.strip()
        
        # Build calculated stock pivot frame
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

    # UI LAYOUT SEGREGATION FOR QUERY AND DISTRIBUTION TABLE
    q_col1, q_col2 = st.columns([1, 2])
    
    with q_col1:
        st.markdown("#### 🔍 Interactive Query Lots Tool")
        with st.container(border=True):
            query_name = st.text_input("Enter Target Model / Bangle Name", placeholder="e.g. KAVYA BANGLES").strip().upper()
            query_color = st.text_input("Enter Target Colour Variant", placeholder="e.g. ROSE GOLD").strip().upper()
            query_size = st.text_input("Enter Target Size Dimension", placeholder="e.g. 2.6").strip()
            
            run_query = st.button("Query Lot Availability Terminal ⚡", type="primary")
            
            if run_query:
                if not query_name or not query_color or not query_size:
                    st.warning("All verification query field keys are required.")
                else:
                    match_df = df_computed_bangles_master[
                        (df_computed_bangles_master["Model (Bangle Name)"] == query_name) &
                        (df_computed_bangles_master["Colour Variant"] == query_color) &
                        (df_computed_bangles_master["Size"] == query_size)
                    ]
                    
                    if not match_df.empty:
                        available_stock_count = match_df.iloc[0]["Available Stock Volume"]
                        if available_stock_count > 0:
                            st.success(f"📦 Stock Verified! **`{available_stock_count} unit lots`** available for {query_name} ({query_color} - Size {query_size}).")
                        else:
                            st.error(f"❌ Out of Stock! 0 units available for {query_name} ({query_color} - Size {query_size}).")
                    else:
                        st.error(f"❌ Record Void! No matching entry found for {query_name} ({query_color} - Size {query_size}).")

    with q_col2:
        st.markdown("#### 🎨 Color & Model Distribution Matrix View")
        if df_computed_bangles_master.empty:
            st.info("No distribution values recorded.")
        else:
            # Render pivot representation for clear color vs model visibility mapping
            df_active_matrix_view = df_computed_bangles_master[df_computed_bangles_master["Available Stock Volume"] > 0]
            if not df_active_matrix_view.empty:
                df_pivot_matrix = df_active_matrix_view.pivot_table(
                    index="Model (Bangle Name)", 
                    columns="Colour Variant", 
                    values="Available Stock Volume", 
                    aggfunc="sum", 
                    fill_value=0
                )
                st.dataframe(df_pivot_matrix, width="stretch")
            else:
                st.info("No active available stock lines available to map onto the distribution matrix visual charts.")

    st.write("---")
    st.markdown("#### Complete Granular Inventory Lot Ingestion Breakdown")
    st.dataframe(df_computed_bangles_master, width="stretch", hide_index=True)

# ==============================================================================
# --- PAGE 3: FAST CHECKOUT TERMINAL (STAGING FORM CONTROLS) ---
# ==============================================================================
with p3:
    st.subheader("🎯 Active Product Ingestion Counters & Staging Buffers")
    
    term_c1, term_c2 = st.columns(2)
    
    with term_c1:
        st.markdown("#### ⭕ Granular Bangles Multi-Row Data Entry Desk")
        bangle_mode_type = st.radio("Select Workflow Type", options=["Stage Purchase Row (Stock In)", "Stage Sale Row (Stock Out)"], horizontal=True)
        
        with st.form("granular_bangle_staging_form", clear_on_submit=True):
            f_b_name = st.text_input("Bangle Model Name", placeholder="e.g. JAI GANAPATI BANGLES").strip().upper()
            f_b_color = st.text_input("Colour Specification", placeholder="e.g. EMERALD GREEN").strip().upper()
            f_b_size = st.text_input("Size Dimension", placeholder="e.g. 2.4").strip()
            f_b_cp = st.number_input("Cost Price (CP) (₹)", min_value=0.0, step=10.0, format="%.2f")
            
            f_b_sp = 0.0
            f_b_channel = "N/A"
            f_b_ship = 0.0
            
            if "Stock Out" in bangle_mode_type:
                f_b_sp = st.number_input("Selling Price (SP) (₹)", min_value=0.0, step=10.0, format="%.2f")
                f_b_channel = st.radio("Operations Delivery Vector", options=["Online Order", "Offline Stall"], horizontal=True)
                if f_b_channel == "Online Order":
                    f_b_ship = st.number_input("Free Shipping Sunk Outflow (₹)", min_value=0.0, step=10.0, format="%.2f")
            
            add_bangle_to_stage = st.form_submit_button("Add Row to Staging Buffer List ➕")
            
            if add_bangle_to_stage:
                if not f_b_name or not f_b_color or not f_b_size:
                    st.error("Model Name, Colour, and Size parameters are mandatory.")
                else:
                    if "Stock In" in bangle_mode_type:
                        st.session_state.staged_bangle_purchases.append({
                            "Transaction Type": "Purchase", "Bangle Name": f_b_name, "Colour": f_b_color, "Size": f_b_size,
                            "Cost Price (₹)": f_b_cp, "Selling Price (₹)": 0.0, "Channel": "N/A", "Shipping Cost (₹)": 0.0
                        })
                    else:
                        st.session_state.staged_bangle_sales.append({
                            "Transaction Type": "Sale", "Bangle Name": f_b_name, "Colour": f_b_color, "Size": f_b_size,
                            "Cost Price (₹)": f_b_cp, "Selling Price (₹)": f_b_sp, "Channel": f_b_channel, "Shipping Cost (₹)": f_b_ship
                        })
                    st.toast("Row added to flash memory staging grid!")

        # Process and render local buffers
        if st.session_state.staged_bangle_purchases:
            st.markdown("##### Staged Purchases Preview List")
            st.dataframe(pd.DataFrame(st.session_state.staged_bangle_purchases), width="stretch", hide_index=True)
            if st.button("Commit Staged Purchases to Cloud Sheet 🚀", type="primary"):
                c_rows = []
                c_idx = len(df_bangles_detailed)
                ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for entry in st.session_state.staged_bangle_purchases:
                    c_idx += 1
                    c_rows.append([c_idx, "Purchase", entry["Bangle Name"], entry["Colour"], entry["Size"], entry["Cost Price (₹)"], 0.0, "N/A", 0.0, ts_str])
                bangles_log_worksheet.append_rows(c_rows)
                st.session_state.staged_bangle_purchases = []
                st.success("Staged purchases committed successfully to Google Sheet Tab 5!")
                st.rerun()

        if st.session_state.staged_bangle_sales:
            st.markdown("##### Staged Sales Preview List")
            st.dataframe(pd.DataFrame(st.session_state.staged_bangle_sales), width="stretch", hide_index=True)
            if st.button("Commit Staged Sales to Cloud Sheet 🚀", type="primary"):
                c_rows = []
                c_idx = len(df_bangles_detailed)
                ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for entry in st.session_state.staged_bangle_sales:
                    c_idx += 1
                    c_rows.append([c_idx, "Sale", entry["Bangle Name"], entry["Colour"], entry["Size"], entry["Cost Price (₹)"], entry["Selling Price (₹)"], entry["Channel"], entry["Shipping Cost (₹)"], ts_str])
                bangles_log_worksheet.append_rows(c_rows)
                st.session_state.staged_bangle_sales = []
                st.success("Staged sales entries saved successfully to Google Sheet Tab 5!")
                st.rerun()

    with term_c2:
        st.markdown("#### 📿 General Jewelry Lot Order Checkout Terminal (Tab 3 Matrix)")
        if df_inventory.empty:
            st.info("General catalog dictionary payload empty.")
        else:
            sku_label_key = "Item Code" if "Item Code" in df_inventory.columns else df_inventory.columns[0]
            type_label_key = "Item Type" if "Item Type" in df_inventory.columns else df_inventory.columns[1]
            sp_label_key = "Selling Price" if "Selling Price" in df_inventory.columns else df_inventory.columns[2]
            cp_label_key = "Cost Price" if "Cost Price" in df_inventory.columns else df_inventory.columns[3]
            rem_label_key = "Remaining Quantity" if "Remaining Quantity" in df_inventory.columns else df_inventory.columns[4]
            
            with st.form("general_jewelry_checkout_form", clear_on_submit=True):
                chosen_jew_skus = st.multiselect("Select Checkout SKU Target Codes", options=df_inventory[sku_label_key].dropna().tolist())
                jew_discount = st.number_input("Applied Disc %", min_value=0.0, max_value=100.0, value=None, step=5.0, placeholder="0%")
                submit_jew_sale = st.form_submit_button("Log Jewelry Sale Transaction 🚀")
                
                if submit_jew_sale:
                    if not chosen_jew_skus:
                        st.error("Select at least one SKU target code to execute a transaction.")
                    else:
                        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        new_sales_entries = []
                        
                        for sku in chosen_jew_skus:
                            r_idx = df_inventory[df_inventory[sku_label_key] == sku].index[0]
                            curr_stock = int(pd.to_numeric(df_inventory.at[r_idx, rem_label_key], errors='coerce'))
                            
                            df_inventory.at[r_idx, rem_label_key] = str(curr_stock - 1)
                            
                            new_sales_entries.append([
                                len(df_sales) + len(new_sales_entries) + 1,
                                sku,
                                df_inventory.at[r_idx, type_label_key],
                                float(pd.to_numeric(df_inventory.at[r_idx, sp_label_key], errors='coerce')),
                                jew_discount if jew_discount is not None else 0.0,
                                float(pd.to_numeric(df_inventory.at[r_idx, sp_label_key], errors='coerce')) * (1.0 - ((jew_discount if jew_discount is not None else 0.0) / 100.0)),
                                float(pd.to_numeric(df_inventory.at[r_idx, cp_label_key], errors='coerce')),
                                timestamp_str
                            ])
                        try:
                            inventory_worksheet.clear()
                            inventory_worksheet.update('A1', [df_inventory.columns.values.tolist()] + df_inventory.astype(str).values.tolist())
                            sales_worksheet.append_rows(new_sales_entries)
                            st.success("Stall Jewelry transaction logged successfully!")
                            st.rerun()
                        except Exception as cloud_err:
                            st.error(f"Cloud update failed: {cloud_err}")

# ==============================================================================
# --- PAGE 4: EXPENSE CONTROL LEDGER (STRATIFIED SEGMENT ASSIGNMENTS) ---
# ==============================================================================
with p4:
    st.subheader("💸 Segmented Operational Cost Allocation Board")
    
    with st.form("stratified_expense_form", clear_on_submit=True):
        f_exp_segment = st.selectbox("Assign Outflow Target Business Segment", options=["Bangles (Online)", "Jewelry (Stall)"])
        f_exp_cat = st.selectbox("Category Allocation Mapping", options=[
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
        f_exp_amt = st.number_input("Transaction Outflow Value (₹)", min_value=0.0, step=50.0, format="%.2f")
        f_exp_desc = st.text_input("Transaction Memo / Details", placeholder="e.g. Train ticket from BLR to HYD, Shipment - kavya, iPhone 17 pro rent")
        f_submit_exp = st.form_submit_button("Commit Segmented Expense Entry 💸")
        
        if f_submit_exp:
            if f_exp_amt <= 0 or not f_exp_desc:
                st.error("Provide a valid description memo and transaction amount configuration.")
            else:
                next_id = len(df_expenses) + 1
                ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                expense_worksheet.append_rows([[next_id, f_exp_cat, f_exp_segment, f_exp_amt, f_exp_desc, ts_now]])
                st.success(f"Outflow of ₹{f_exp_amt:,.2f} appended successfully to {f_exp_segment}!")
                st.rerun()

    st.write("---")
    st.markdown("#### Complete Reconciled Historical Expense Table Logs")
    if df_expenses.empty:
        st.info("No expense rows returned from Tab 4 workspace tables.")
    else:
        st.dataframe(df_expenses.sort_values(by="Expense ID", ascending=False), width="stretch", hide_index=True)

# ==============================================================================
# --- PAGE 5: MASTER BACKENDS DATABASE VIEWERS ---
# ==============================================================================
with p5:
    st.subheader("📦 Real-Time Cloud Sheet Sheet-Tab View Data Blocks")
    m_tabs = st.radio("Select Target Sheet-Tab Visual View Backups", options=["General Inventory (Tab 2)", "General Sales Log (Tab 3)", "Bangles Detailed Master Ingestion (Tab 5)"], horizontal=True)
    
    if "Tab 2" in m_tabs:
        st.dataframe(df_inventory, width="stretch", hide_index=True)
    elif "Tab 3" in m_tabs:
        st.dataframe(df_sales, width="stretch", hide_index=True)
    else:
        st.dataframe(df_bangles_detailed, width="stretch", hide_index=True)
