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
    
    # Map worksheets dynamically by position (Tab 2, Tab 3, Tab 4)
    inventory_worksheet = sheet.get_worksheet(1)  # Tab 2: Inventory
    sales_worksheet = sheet.get_worksheet(2)      # Tab 3: Sales Log
    
    # Safely find or initialize Tab 4 (Expense Log)
    try:
        expense_worksheet = sheet.get_worksheet(3)
        if expense_worksheet is None:
            expense_worksheet = sheet.add_worksheet(title="Expense Log", rows="1000", cols="6")
            expense_worksheet.update('A1', [["Expense ID", "Category", "Amount (₹)", "Description", "Item Cost Price Mapping", "Timestamp"]])
    except Exception:
        expense_worksheet = sheet.add_worksheet(title="Expense Log", rows="1000", cols="6")
        expense_worksheet.update('A1', [["Expense ID", "Category", "Amount (₹)", "Description", "Item Cost Price Mapping", "Timestamp"]])

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

    # Clean empty layout metadata artifacts
    df_inventory = df_inventory[df_inventory[item_code_col].astype(str).str.strip() != ""]
    df_inventory[item_code_col] = df_inventory[item_code_col].astype(str).str.strip().str.upper()
else:
    st.error("❌ Inventory columns configuration is unreadable.")
    st.stop()

if not df_sales.empty and "Order ID" in df_sales.columns:
    df_sales = df_sales[df_sales["Order ID"].astype(str).str.strip() != ""]

if not df_expenses.empty and "Expense ID" in df_expenses.columns:
    df_expenses = df_expenses[df_expenses["Expense ID"].astype(str).str.strip() != ""]

# --- THE 6-PAGE RECONCILED TERMINAL STRUCTURE ---
p1, p2, p3, p4, p5, p6 = st.tabs([
    "📦 1. Live Stock Dashboard", 
    "🎯 2. Active Order Billing", 
    "💸 3. Expense Ledger Form",
    "⭕ 4. Bangles Lot Dashboard",
    "📿 5. Chains & Rings Dashboard",
    "📊 6. Profit & Break-Even Command"
])

# --- PAGE 1: LIVE STOCK DASHBOARD ---
with p1:
    st.subheader("Current Operational Stock Summary")
    # Dynamically display Cost Price alongside Selling Price
    display_columns = [item_type_col, item_code_col, cost_price_col, selling_price_col, remaining_qty_col]
    available_cols = [col for col in display_columns if col in df_inventory.columns]
    
    total_units = int(pd.to_numeric(df_inventory[remaining_qty_col], errors='coerce').sum())
    st.metric(label="Total Volumetric Units in Stock", value=f"{total_units} units")
    st.dataframe(
        df_inventory[available_cols], use_container_width=True, hide_index=True,
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
                        
                        # Apply live stock mutations strictly to Remaining Quantity
                        df_inventory.at[row_idx, remaining_qty_col] = str(current_stock - 1)
                        if total_col in df_inventory.columns:
                            df_inventory.at[row_idx, total_col] = str(int(df_inventory.at[row_idx, remaining_qty_col]) * base_price_val)
                        
                        # Pass Cost Price directly into the sale log schema block
                        new_sales_entries.append({
                            "Order ID": next_order_id, "Item Code": sku, "Item Type": item_type_val,
                            "Original Price (₹)": base_price_val, "Discount (%)": actual_discount,
                            "Final Revenue (₹)": final_selling_price, "Cost Price (₹)": base_cost_val, "Timestamp": timestamp_str
                        })
                    
                    if new_sales_entries:
                        # Append columns matching previous layout schema definitions
                        df_new_sales = pd.DataFrame(new_sales_entries)
                        for col in df_sales.columns:
                            if col not in df_new_sales.columns:
                                df_new_sales[col] = ""
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
        st.dataframe(
            df_expenses.sort_values(by="Expense ID", ascending=False), use_container_width=True, hide_index=True,
            column_config={
                "Expense ID": st.column_config.TextColumn("ID", width=60),
                "Category": st.column_config.TextColumn("Category", width=180),
                "Amount (₹)": st.column_config.NumberColumn("Amount Out (₹)", width=120),
                "Description": st.column_config.TextColumn("Transaction Memo", width=380),
                "Timestamp": st.column_config.TextColumn("Date Entered", width=160)
            }
        )

# --- PAGE 4: BANGLES LOT DASHBOARD (LOT B) ---
with p4:
    st.subheader("Isolated Lot B: Handmade, Glass & Customized Bangles Analytics")
    df_sales_bangles = df_sales[df_sales["Item Type"].astype(str).str.lower().str.contains("bangle")]
    
    if df_sales_bangles.empty:
        st.info("No bangles lot conversions registered in this tracking frame.")
    else:
        bangle_rev = pd.to_numeric(df_sales_bangles["Final Revenue (₹)"], errors='coerce').sum()
        bangle_cost = pd.to_numeric(df_sales_bangles["Cost Price (₹)"], errors='coerce').sum()
        bangle_margin = bangle_rev - bangle_cost
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Bangle Lots Sold", f"{len(df_sales_bangles)} Pcs")
        c2.metric("Gross Revenue Receipts", f"₹{bangle_rev:,.2f}")
        c3.metric("Product Gross Margin", f"₹{bangle_margin:,.2f}")
        
        st.markdown("#### Lot B Sales Feed")
        st.dataframe(
            df_sales_bangles.sort_values(by="Order ID", ascending=False), use_container_width=True, hide_index=True,
            column_config={
                "Order ID": st.column_config.TextColumn("ID", width=60),
                "Item Code": st.column_config.TextColumn("SKU Code", width=100),
                "Item Type": st.column_config.TextColumn("Specification", width=220),
                "Final Revenue (₹)": st.column_config.NumberColumn("Revenue (SP)", width=120),
                "Cost Price (₹)": st.column_config.NumberColumn("Product Cost (CP)", width=120),
                "Timestamp": st.column_config.TextColumn("Timestamp", width=160)
            }
        )

# --- PAGE 5: CHAINS & RINGS DASHBOARD (LOT A) ---
with p5:
    st.subheader("Isolated Lot A: Necklaces, Chains, Bracelets & Rings Analytics")
    df_sales_jewelry = df_sales[~df_sales["Item Type"].astype(str).str.lower().str.contains("bangle")]
    
    if df_sales_jewelry.empty:
        st.info("No jewelry lots sales registered in this tracking frame.")
    else:
        jew_rev = pd.to_numeric(df_sales_jewelry["Final Revenue (₹)"], errors='coerce').sum()
        jew_cost = pd.to_numeric(df_sales_jewelry["Cost Price (₹)"], errors='coerce').sum()
        jew_margin = jew_rev - jew_cost
        
        cj1, cj2, cj3 = st.columns(3)
        cj1.metric("Jewelry Units Sold", f"{len(df_sales_jewelry)} Pcs")
        cj2.metric("Gross Revenue Receipts", f"₹{jew_rev:,.2f}")
        cj3.metric("Product Gross Margin", f"₹{jew_margin:,.2f}")
        
        st.markdown("#### Lot A Sales Feed")
        st.dataframe(
            df_sales_jewelry.sort_values(by="Order ID", ascending=False), use_container_width=True, hide_index=True,
            column_config={
                "Order ID": st.column_config.TextColumn("ID", width=60),
                "Item Code": st.column_config.TextColumn("SKU Code", width=100),
                "Item Type": st.column_config.TextColumn("Category Lot", width=220),
                "Final Revenue (₹)": st.column_config.NumberColumn("Revenue (SP)", width=120),
                "Cost Price (₹)": st.column_config.NumberColumn("Product Cost (CP)", width=120),
                "Timestamp": st.column_config.TextColumn("Timestamp", width=160)
            }
        )

# --- PAGE 6: PROFIT & BREAK-EVEN COMMAND ---
with p6:
    st.subheader("Comprehensive Reconciled Financial Engine")
    
    # Cast variables cleanly
    total_revenue_gross = pd.to_numeric(df_sales["Final Revenue (₹)"], errors='coerce').sum()
    total_cogs_products = pd.to_numeric(df_sales["Cost Price (₹)"], errors='coerce').sum()
    total_operational_expenses = pd.to_numeric(df_expenses["Amount (₹)"], errors='coerce').sum()
    
    # Financial Matrix Reconcile
    gross_profit = total_revenue_gross - total_cogs_products
    net_profit_loss = gross_profit - total_operational_expenses
    
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Gross Sales Receipts", f"₹{total_revenue_gross:,.2f}")
    mc2.metric("Total Product Sunk CP (COGS)", f"₹{total_cogs_products:,.2f}")
    mc3.metric("Operational Expenses (Levers)", f"₹{total_operational_expenses:,.2f}")
    
    if net_profit_loss >= 0:
        mc4.metric("Net Profit (Take Home)", f"₹{net_profit_loss:,.2f}", delta="PROFITABLE OPERATION")
    else:
        mc4.metric("Net Profit (Take Home)", f"₹{net_profit_loss:,.2f}", delta="- LOSS SNAPSHOT", delta_color="inverse")
        
    st.write("---")
    st.subheader("Free Shipping & Overhead Break-Even Analysis")
    
    # Categorize Operational Expenses into Fixed Overhead vs Variable Shipping/Logistics
    fixed_cats = ["Stall Setup", "Electronics", "Lodging", "Operations", "Miscellaneous"]
    variable_cats = ["Free Shipping", "Packaging", "Direct Lot Material"]
    
    fixed_costs = 0.0
    variable_costs = 0.0
    
    for _, row in df_expenses.iterrows():
        cat_lower = str(row["Category"]).lower()
        amt_val = pd.to_numeric(row["Amount (₹)"], errors='coerce')
        if pd.isna(amt_val): continue
        if any(f_c.lower() in cat_lower for f_c in fixed_cats):
            fixed_costs += amt_val
        else:
            variable_costs += amt_val
            
    total_units_sold = len(df_sales)
    col_bep1, col_bep2 = st.columns(2)
    
    with col_bep1:
        st.markdown("#### Cost Allocation Structure")
        st.markdown(f"🔹 **Fixed Operating Structural Investments:** `₹{fixed_costs:,.2f}` *(Stalls, Lodging, Devices)*")
        st.markdown(f"🔹 **Logistics & Sunk Variable Outflows:** `₹{variable_costs:,.2f}` *(Free Shipping, Packaging)*")
        
        if total_units_sold > 0:
            avg_sp_per_unit = total_revenue_gross / total_units_sold
            avg_cp_per_unit = total_cogs_products / total_units_sold
            avg_shipping_per_unit = variable_costs / total_units_sold
            
            # Unit Contribution Margin = SP - CP - Shipping Cost per unit
            unit_contribution_margin = avg_sp_per_unit - avg_cp_per_unit - avg_shipping_per_unit
            
            st.markdown(f"🔹 **Average Retail Price (SP):** `₹{avg_sp_per_unit:,.2f}`")
            st.markdown(f"🔹 **Average Product Base Cost (CP):** `₹{avg_cp_per_unit:,.2f}`")
            st.markdown(f"🔹 **Average Shipping Burden per Pc:** `₹{avg_shipping_per_unit:,.2f}`")
            st.markdown(f"🔹 **True Net Margin Contribution per Pc:** `₹{unit_contribution_margin:,.2f}`")
        else:
            unit_contribution_margin = 0.0
            st.warning("Awaiting initial conversions to chart average lot contribution values.")
            
    with col_bep2:
        st.markdown("#### Structural Breakeven Milestones")
        if unit_contribution_margin > 0:
            units_to_break_even = math.ceil(fixed_costs / unit_contribution_margin)
            st.info(f"📈 **Break-Even Target Volume:** `{units_to_break_even} total units` must be sold to completely cover your fixed operating expenses at your current margins.")
            
            progress_ratio = min(1.0, total_units_sold / max(1, units_to_break_even))
            st.progress(progress_ratio)
            st.markdown(f"🎯 *Current Run Clearance Progress:* **{progress_ratio * 100:.1f}% completed** ({total_units_sold} / {units_to_break_even} units cleared).")
        else:
            if total_units_sold > 0:
                st.error("🚨 Margin Deficit: Your product acquisition costs combined with free shipping overhead currently exceed your average unit sale receipts. Re-evaluate your base retail price lots.")
            else:
                st.info("Log your active product conversion units to calculate your exact breakeven volume progress bars.")
