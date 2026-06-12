### Full Updated Code (`app.py`)

```python
import base64
import json
from datetime import datetime
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Yashasvi Executive Cloud", page_icon="💎", layout="wide")
st.title("💎 Yashasvi Imitations — Executive Command Hub")
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
SPREADSHEET_ID = "15pLvkO6T7hlNy2Oe2W6tJ47j0TPZmaFJ"

try:
    sheet = client.open_by_key(SPREADSHEET_ID)
    
    # Dynamic worksheet sheet tab indexing
    inventory_worksheet = sheet.get_worksheet(1) # Tab 2
    sales_worksheet = sheet.get_worksheet(2)     # Tab 3
    
    # Safely look for or initialize Tab 4 (Expense Log)
    try:
        expense_worksheet = sheet.get_worksheet(3)
        if expense_worksheet is None:
            expense_worksheet = sheet.add_worksheet(title="Expense Log", rows="1000", cols="5")
            expense_worksheet.update('A1', [["Expense ID", "Category", "Amount (₹)", "Description", "Timestamp"]])
    except Exception:
        expense_worksheet = sheet.add_worksheet(title="Expense Log", rows="1000", cols="5")
        expense_worksheet.update('A1', [["Expense ID", "Category", "Amount (₹)", "Description", "Timestamp"]])

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
        df_sales = pd.DataFrame(columns=["Order ID", "Item Code", "Item Type", "Original Price (₹)", "Discount (%)", "Final Revenue (₹)", "Timestamp"])

    # --- EXPENSE DATA SNAPSHOT ---
    raw_exp_data = expense_worksheet.get_all_values()
    if raw_exp_data and len(raw_exp_data) > 0:
        exp_headers = [str(h).strip().replace('\u00a0', ' ') for h in raw_exp_data[0]]
        df_expenses = pd.DataFrame(raw_exp_data[1:], columns=exp_headers)
        df_expenses.columns = df_expenses.columns.str.strip()
    else:
        df_expenses = pd.DataFrame(columns=["Expense ID", "Category", "Amount (₹)", "Description", "Timestamp"])

except Exception as e:
    st.error(f"❌ Failed to parse Google Sheet tabs: {e}")
    st.stop()

# --- RESOLVE DYNAMIC COLUMNS ONSCREEN ---
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
    st.error("❌ Inventory dataframe structure is unmapped.")
    st.stop()

if not df_sales.empty and "Order ID" in df_sales.columns:
    df_sales = df_sales[df_sales["Order ID"].astype(str).str.strip() != ""]

if not df_expenses.empty and "Expense ID" in df_expenses.columns:
    df_expenses = df_expenses[df_expenses["Expense ID"].astype(str).str.strip() != ""]

# --- THE 6-PAGE RECONCILED TERMINAL STRUCTURE ---
p1, p2, p3, p4, p5, p6 = st.tabs([
    "📦 1. Live Stock Dashboard", 
    "🎯 2. Active Order Billing", 
    "💸 3. Operational Expense Logger",
    "📿 4. Chains & Rings Dashboard", 
    "⭕ 5. Bangles Lot Dashboard",
    "📊 6. Profit & Break-Even Command"
])

# --- PAGE 1: LIVE STOCK DASHBOARD ---
with p1:
    st.subheader("Current Operational Stock Summary")
    display_columns = [item_type_col, item_code_col, remaining_qty_col]
    available_cols = [col for col in display_columns if col in df_inventory.columns]
    
    total_units = int(pd.to_numeric(df_inventory[remaining_qty_col], errors='coerce').sum())
    st.metric(label="Total Volumetric Units in Stock", value=f"{total_units} units")
    st.dataframe(
        df_inventory[available_cols], use_container_width=True, hide_index=True,
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
                        
                        final_selling_price = base_price_val * (1.0 - (actual_discount / 100.0))
                        total_bill_amount += final_selling_price
                        next_order_id = len(df_sales) + len(new_sales_entries) + 1
                        
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

# --- PAGE 3: OPERATIONAL EXPENSE LOGGER ---
with p3:
    st.subheader("Stall Ledger & Outflow Entry Form")
    with st.form("expense_form", clear_on_submit=True):
        exp_cat = st.selectbox("Expense Allocation Category", options=[
            "Material Procurement", 
            "Shipping Costs", 
            "Stall Setup / Rent", 
            "Travel Expenses", 
            "Marketing / Cards", 
            "Miscellaneous"
        ])
        exp_amt = st.number_input("Transaction Amount (₹)", min_value=0.0, step=100.0, format="%.2f")
        exp_desc = st.text_input("Expense Memo / Description", placeholder="e.g. Jayanagar Stall booking advance, Sarjapur customer delivery flight freight")
        submit_expense = st.form_submit_button("Commit Outflow Entry to Google Sheet 💸")
        
        if submit_expense:
            if exp_amt <= 0:
                st.error("Transaction rejected: Outflow value must be greater than zero.")
            else:
                next_exp_id = len(df_expenses) + 1
                exp_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                new_row = {
                    "Expense ID": next_exp_id,
                    "Category": exp_cat,
                    "Amount (₹)": exp_amt,
                    "Description": exp_desc,
                    "Timestamp": exp_ts
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
                "Category": st.column_config.TextColumn("Category", width=150),
                "Amount (₹)": st.column_config.NumberColumn("Amount Out (₹)", width=120),
                "Description": st.column_config.TextColumn("Transaction Memo", width=350),
                "Timestamp": st.column_config.TextColumn("Date Entered", width=160)
            }
        )

# --- PAGE 4: CHAINS & RINGS DASHBOARD (LOT A) ---
with p4:
    st.subheader("Lot A: Necklaces, Chains, Bracelets & Rings Analytics")
    # Filter everything that is NOT a bangle
    df_sales_jewelry = df_sales[~df_sales["Item Type"].astype(str).str.lower().str.contains("bangle")]
    
    if df_sales_jewelry.empty:
        st.info("No jewelry lots sales registered in this tracking frame.")
    else:
        jew_rev = pd.to_numeric(df_sales_jewelry["Final Revenue (₹)"], errors='coerce').sum()
        jew_units = len(df_sales_jewelry)
        
        sc1, sc2 = st.columns(2)
        sc1.metric("Jewelry Units Sold", f"{jew_units} Pcs")
        sc2.metric("Gross Jewelry Revenue", f"₹{jew_rev:,.2f}")
        
        st.markdown("#### Lot A Sales Ingestion Feed")
        st.dataframe(
            df_sales_jewelry.sort_values(by="Order ID", ascending=False), use_container_width=True, hide_index=True,
            column_config={
                "Order ID": st.column_config.TextColumn("ID", width=60),
                "Item Code": st.column_config.TextColumn("SKU Code", width=100),
                "Item Type": st.column_config.TextColumn("Category / Description", width=220),
                "Final Revenue (₹)": st.column_config.NumberColumn("Collected Revenue", width=130),
                "Timestamp": st.column_config.TextColumn("Timestamp", width=160)
            }
        )

# --- PAGE 5: BANGLES LOT DASHBOARD (LOT B) ---
with p5:
    st.subheader("Lot B: Handmade, Premium Glass & Customized Bangles Analytics")
    # Filter everything that IS a bangle
    df_sales_bangles = df_sales[df_sales["Item Type"].astype(str).str.lower().str.contains("bangle")]
    
    if df_sales_bangles.empty:
        st.info("No bangles lot conversions registered in this tracking frame.")
    else:
        bangle_rev = pd.to_numeric(df_sales_bangles["Final Revenue (₹)"], errors='coerce').sum()
        bangle_units = len(df_sales_bangles)
        
        sb1, sb2 = st.columns(2)
        sb1.metric("Bangle Lots Sold", f"{bangle_units} Pcs")
        sb2.metric("Gross Bangles Revenue", f"₹{bangle_rev:,.2f}")
        
        st.markdown("#### Lot B Sales Ingestion Feed")
        st.dataframe(
            df_sales_bangles.sort_values(by="Order ID", ascending=False), use_container_width=True, hide_index=True,
            column_config={
                "Order ID": st.column_config.TextColumn("ID", width=60),
                "Item Code": st.column_config.TextColumn("SKU Code", width=100),
                "Item Type": st.column_config.TextColumn("Bangle Specification", width=220),
                "Final Revenue (₹)": st.column_config.NumberColumn("Collected Revenue", width=130),
                "Timestamp": st.column_config.TextColumn("Timestamp", width=160)
            }
        )

# --- PAGE 6: PROFIT & BREAK-EVEN COMMAND ---
with p6:
    st.subheader("Comprehensive Reconciled Financial Engine")
    
    # Cast all calculations securely
    total_revenue_gross = pd.to_numeric(df_sales["Final Revenue (₹)"], errors='coerce').sum()
    total_expenses_gross = pd.to_numeric(df_expenses["Amount (₹)"], errors='coerce').sum()
    net_profit_loss = total_revenue_gross - total_expenses_gross
    
    # Performance summary cards
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Total Realized Cash Receipts", f"₹{total_revenue_gross:,.2f}")
    mc2.metric("Total Logged Outflows / COGS", f"₹{total_expenses_gross:,.2f}")
    
    if net_profit_loss >= 0:
        mc3.metric("Net Operational Profit (In Pocket)", f"₹{net_profit_loss:,.2f}", delta="PROFITABLE MARGIN")
    else:
        mc3.metric("Net Operational Deficit (Hurdle Overhang)", f"₹{net_profit_loss:,.2f}", delta="- LOSS SNAPSHOT", delta_color="inverse")
        
    st.write("---")
    st.subheader("Break-Even Optimization Calculator")
    
    # Segregate fixed operating overhead vs variable COGS costs to calculate financial break-even volume
    fixed_categories = ["Stall Setup / Rent", "Travel Expenses", "Miscellaneous"]
    variable_categories = ["Material Procurement", "Shipping Costs", "Marketing / Cards"]
    
    fixed_costs = pd.to_numeric(df_expenses[df_expenses["Category"].isin(fixed_categories)]["Amount (₹)"], errors='coerce').sum()
    variable_costs = pd.to_numeric(df_expenses[df_expenses["Category"].isin(variable_categories)]["Amount (₹)"], errors='coerce').sum()
    
    total_units_sold = len(df_sales)
    
    col_bep1, col_bep2 = st.columns(2)
    
    with col_bep1:
        st.markdown("#### Cost Structures Allocation")
        st.markdown(f"🔹 **Fixed Baseline Overhead:** `₹{fixed_costs:,.2f}` *(Stalls, Travel, Setup)*")
        st.markdown(f"🔹 **Variable COGS Sunk Value:** `₹{variable_costs:,.2f}` *(Procurement, Deliveries)*")
        
        if total_units_sold > 0:
            avg_variable_cost_per_unit = variable_costs / total_units_sold
            avg_revenue_per_unit = total_revenue_gross / total_units_sold
            contribution_margin_per_unit = avg_revenue_per_unit - avg_variable_cost_per_unit
            
            st.markdown(f"🔹 **Average Sale Price per Pc:** `₹{avg_revenue_per_unit:,.2f}`")
            st.markdown(f"🔹 **Estimated Sunk Cost per Pc:** `₹{avg_variable_cost_per_unit:,.2f}`")
            st.markdown(f"🔹 **Unit Contribution Margin:** `₹{contribution_margin_per_unit:,.2f}`")
        else:
            contribution_margin_per_unit = 0
            st.warning("⚠️ Awaiting checkout item logs to compute average operational unit margins.")
            
    with col_bep2:
        st.markdown("#### Hurdle Runways to Parity")
        if contribution_margin_per_unit > 0:
            units_to_break_even = math.ceil(fixed_costs / contribution_margin_per_unit) if 'math' in globals() else int(-(-fixed_costs // contribution_margin_per_unit))
            st.info(f"📈 **Calculated Break-Even Target Volumetric Point:** `{units_to_break_even} total units` must be cleared at your current configuration to offset all fixed structural investments.")
            
            progress_ratio = min(1.0, total_units_sold / max(1, units_to_break_even))
            st.progress(progress_ratio)
            st.markdown(f"🎯 *Current Run Clearance Progress:* **{progress_ratio * 100:.1f}% completed** ({total_units_sold} / {units_to_break_even} units cleared).")
        else:
            if total_units_sold > 0:
                st.error("🚨 Margin Deficit: Your variable costs per item currently exceed your average unit sale receipts. Re-evaluate your base retail price lots.")
            else:
                st.info("Log your active product conversion units to calculate your exact breakeven volume progress bars.")

