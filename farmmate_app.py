"""
Farm Budgeting Web Application
Streamlit interface for farm financial planning
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from farmmate_engine import (
    FarmModel, GeneralAssumptions, InflationRates, CropMargin,
    LivestockProgram, LivestockClass, OverheadCategory, OpeningBalances,
    Paddock, FixedAsset, PlannedCapex, PlannedDisposal
)

# Page config
st.set_page_config(
    page_title="Farm Budget Builder",
    page_icon="🚜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #2E7D32;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'model' not in st.session_state:
    st.session_state.model = FarmModel()
    st.session_state.calculated = False

# Sidebar navigation
st.sidebar.title("🚜 Farm Budget Builder")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "⚙️ Setup", "🚜 Land & Assets", "🌱 Cropping", "🐄🐑 Livestock", "💰 Financials", "📈 Reports"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Actions")
if st.sidebar.button("🔄 Recalculate", use_container_width=True):
    with st.spinner("Calculating..."):
        st.session_state.model.calculate()
        st.session_state.calculated = True
        st.success("Calculation complete!")

if st.sidebar.button("💾 Save Scenario", use_container_width=True):
    st.info("Save functionality coming soon")

if st.sidebar.button("📥 Export Report", use_container_width=True):
    st.info("Export functionality coming soon")

# Main content area
if page == "📊 Dashboard":
    st.markdown('<div class="main-header">Farm Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Overview of your farm\'s financial performance</div>', unsafe_allow_html=True)
    
    if st.session_state.calculated:
        # Get KPIs
        kpis = st.session_state.model.get_kpis()
        
        # Display KPIs
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("EBITDA", f"${kpis.get('ebitda', 0):,.0f}")
            st.metric("Net Profit", f"${kpis.get('net_profit', 0):,.0f}")
        with col2:
            st.metric("Closing Cash", f"${kpis.get('closing_cash', 0):,.0f}")
            st.metric("Total Debt", f"${kpis.get('total_debt', 0):,.0f}")
        with col3:
            st.metric("Net Assets", f"${kpis.get('net_assets', 0):,.0f}")
            st.metric("ROA", f"{kpis.get('roa', 0):.2f}%")
        
        st.markdown("---")
        
        # Charts
        if st.session_state.model.monthly_pl is not None:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Monthly Revenue")
                fig = px.line(
                    st.session_state.model.monthly_pl,
                    x='month',
                    y='total_income',
                    title="Total Income by Month"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Monthly Cash Flow")
                if st.session_state.model.monthly_cf is not None:
                    fig = px.line(
                        st.session_state.model.monthly_cf,
                        x='month',
                        y='closing_cash',
                        title="Cash Balance by Month"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            # P&L waterfall
            st.subheader("Annual P&L Breakdown")
            if st.session_state.model.annual_pl is not None:
                annual = st.session_state.model.annual_pl.iloc[-1]
                
                fig = go.Figure(go.Waterfall(
                    x=["Total Income", "Direct Costs", "Overheads", "Depreciation", 
                       "Interest", "Tax", "Net Profit"],
                    y=[annual['total_income'], -annual['total_direct_costs'], 
                       -annual['overheads'], -annual['depreciation'],
                       -annual['interest_expense'] + annual['interest_income'],
                       -annual['tax'], 0],
                    measure=["relative", "relative", "relative", "relative", 
                            "relative", "relative", "total"]
                ))
                fig.update_layout(title="Profit & Loss Waterfall")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("👈 Complete the setup and click 'Recalculate' to see your dashboard")

elif page == "⚙️ Setup":
    st.markdown('<div class="main-header">Farm Setup</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Configure your farm\'s basic details and assumptions</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["General", "Inflation", "Opening Balances"])
    
    with tab1:
        st.subheader("Farm Details")
        
        col1, col2 = st.columns(2)
        with col1:
            farm_name = st.text_input("Farm Name", value=st.session_state.model.general.farm_name)
            start_date = st.date_input("Budget Start Date", value=st.session_state.model.general.start_date)
            num_months = st.number_input("Number of Months", value=st.session_state.model.general.num_months, 
                                        min_value=1, max_value=120)
        
        with col2:
            income_tax = st.number_input("Income Tax Rate (%)", value=st.session_state.model.general.income_tax_rate * 100,
                                        min_value=0.0, max_value=100.0) / 100
            gst_rate = st.number_input("GST Rate (%)", value=st.session_state.model.general.gst_rate * 100,
                                      min_value=0.0, max_value=100.0) / 100
            overdraft_rate = st.number_input("Overdraft Interest Rate (%)", 
                                            value=st.session_state.model.general.overdraft_rate * 100,
                                            min_value=0.0, max_value=50.0) / 100
        
        # Update model
        st.session_state.model.general.farm_name = farm_name
        st.session_state.model.general.start_date = datetime.combine(start_date, datetime.min.time())
        st.session_state.model.general.num_months = num_months
        st.session_state.model.general.income_tax_rate = income_tax
        st.session_state.model.general.gst_rate = gst_rate
        st.session_state.model.general.overdraft_rate = overdraft_rate
    
    with tab2:
        st.subheader("Inflation Assumptions")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Income Inflation**")
            all_income = st.number_input("All Income (%)", value=st.session_state.model.inflation.all_income * 100,
                                        min_value=0.0, max_value=50.0) / 100
            crops_inf = st.number_input("Crops (%)", value=st.session_state.model.inflation.crops * 100,
                                       min_value=0.0, max_value=50.0) / 100
            beef_inf = st.number_input("Beef (%)", value=st.session_state.model.inflation.beef * 100,
                                       min_value=0.0, max_value=50.0) / 100
            sheep_inf = st.number_input("Sheep (%)", value=st.session_state.model.inflation.sheep * 100,
                                        min_value=0.0, max_value=50.0) / 100
        
        with col2:
            st.markdown("**Expense Inflation**")
            all_expenses = st.number_input("All Expenses (%)", value=st.session_state.model.inflation.all_expenses * 100,
                                          min_value=0.0, max_value=50.0) / 100
            fertiliser = st.number_input("Fertiliser (%)", value=st.session_state.model.inflation.fertiliser * 100,
                                         min_value=0.0, max_value=50.0) / 100
            chemicals = st.number_input("Chemicals (%)", value=st.session_state.model.inflation.chemicals * 100,
                                        min_value=0.0, max_value=50.0) / 100
            fuel = st.number_input("Fuel & Oil (%)", value=st.session_state.model.inflation.fuel_oil * 100,
                                   min_value=0.0, max_value=50.0) / 100
        
        # Update model
        st.session_state.model.inflation.all_income = all_income
        st.session_state.model.inflation.crops = crops_inf
        st.session_state.model.inflation.beef = beef_inf
        st.session_state.model.inflation.sheep = sheep_inf
        st.session_state.model.inflation.all_expenses = all_expenses
        st.session_state.model.inflation.fertiliser = fertiliser
        st.session_state.model.inflation.chemicals = chemicals
        st.session_state.model.inflation.fuel_oil = fuel
    
    with tab3:
        st.subheader("Opening Balance Sheet")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Assets**")
            cash = st.number_input("Cash at Bank ($)", value=float(st.session_state.model.opening_balances.cash),
                                  min_value=0.0, format="%.2f")
            debtors = st.number_input("Trade Debtors ($)", value=float(st.session_state.model.opening_balances.trade_debtors),
                                     min_value=0.0, format="%.2f")
            inventory = st.number_input("Inventory ($)", 
                                       value=float(st.session_state.model.opening_balances.inventory_grain +
                                                  st.session_state.model.opening_balances.inventory_wool +
                                                  st.session_state.model.opening_balances.inventory_livestock),
                                       min_value=0.0, format="%.2f")
            fixed_assets = st.number_input("Fixed Assets ($)", value=float(st.session_state.model.opening_balances.fixed_assets),
                                          min_value=0.0, format="%.2f")
            land = st.number_input("Land & Water ($)", value=float(st.session_state.model.opening_balances.land_water),
                                  min_value=0.0, format="%.2f")
        
        with col2:
            st.markdown("**Liabilities & Equity**")
            creditors = st.number_input("Trade Creditors ($)", value=float(st.session_state.model.opening_balances.trade_creditors),
                                       min_value=0.0, format="%.2f")
            debt = st.number_input("Debt ($)", value=float(st.session_state.model.opening_balances.debt_facilities),
                                  min_value=0.0, format="%.2f")
            share_cap = st.number_input("Share Capital ($)", value=float(st.session_state.model.opening_balances.share_capital),
                                       min_value=0.0, format="%.2f")
            retained = st.number_input("Retained Earnings ($)", value=float(st.session_state.model.opening_balances.retained_earnings),
                                      format="%.2f")
        
        # Update model
        st.session_state.model.opening_balances.cash = cash
        st.session_state.model.opening_balances.trade_debtors = debtors
        st.session_state.model.opening_balances.inventory_grain = inventory  # Simplified
        st.session_state.model.opening_balances.fixed_assets = fixed_assets
        st.session_state.model.opening_balances.land_water = land
        st.session_state.model.opening_balances.trade_creditors = creditors
        st.session_state.model.opening_balances.debt_facilities = debt
        st.session_state.model.opening_balances.share_capital = share_cap
        st.session_state.model.opening_balances.retained_earnings = retained
        
        # Balance check
        total_assets = cash + debtors + inventory + fixed_assets + land
        total_liab_equity = creditors + debt + share_cap + retained
        
        st.markdown("---")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Total Assets", f"${total_assets:,.2f}")
        with col_b:
            st.metric("Total Liabilities + Equity", f"${total_liab_equity:,.2f}")
        with col_c:
            difference = total_assets - total_liab_equity
            if abs(difference) < 0.01:
                st.success(f"✅ Balanced")
            else:
                st.error(f"⚠️ Out of balance by ${difference:,.2f}")

elif page == "🌾 Land & Assets":
    st.markdown('<div class="main-header">Land & Assets</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage paddocks, rotations, and fixed assets</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Paddocks & Rotation", "Fixed Assets", "CAPEX Planning"])
    
    with tab1:
        st.subheader("Paddock Management")
        
        # Add paddock
        with st.expander("➕ Add Paddock"):
            col1, col2, col3 = st.columns(3)
            with col1:
                pad_name = st.text_input("Paddock Name", key="pad_name")
            with col2:
                pad_property = st.text_input("Property", key="pad_property")
            with col3:
                pad_size = st.number_input("Size (ha)", min_value=0.0, key="pad_size")
            
            if st.button("Add Paddock"):
                new_pad = Paddock(
                    name=pad_name,
                    property_name=pad_property,
                    size_ha=pad_size
                )
                st.session_state.model.paddocks.append(new_pad)
                st.success(f"Added {pad_name}")
                st.rerun()
        
        # Display paddocks
        if st.session_state.model.paddocks:
            st.markdown("### Paddock List")
            pads_data = []
            for pad in st.session_state.model.paddocks:
                pads_data.append({
                    'Paddock': pad.name,
                    'Property': pad.property_name,
                    'Size (ha)': pad.size_ha
                })
            
            df_pads = pd.DataFrame(pads_data)
            st.dataframe(df_pads, use_container_width=True)
            
            total_area = df_pads['Size (ha)'].sum()
            st.metric("Total Farm Area", f"{total_area:,.1f} ha")
        else:
            st.info("Add paddocks to start planning your farm layout")
    
    with tab2:
        st.subheader("Fixed Asset Register")
        
        # Add asset
        with st.expander("➕ Add Fixed Asset"):
            col1, col2 = st.columns(2)
            with col1:
                asset_name = st.text_input("Asset Name", key="asset_name")
                asset_class = st.selectbox("Asset Class", 
                    ["Buildings", "Irrigation", "Plant & Equipment", "Motor Vehicles", "Pasture"],
                    key="asset_class")
                asset_subclass = st.text_input("Subclass", key="asset_subclass")
                purchase_date = st.date_input("Purchase Date", key="asset_purchase_date")
            with col2:
                purchase_amt = st.number_input("Purchase Amount ($)", min_value=0.0, key="asset_purchase_amt")
                useful_life = st.number_input("Useful Life (years)", min_value=1.0, max_value=100.0,
                                             value=10.0, key="asset_life")
                residual = st.number_input("Residual Value ($)", min_value=0.0, key="asset_residual")
            
            if st.button("Add Asset"):
                new_asset = FixedAsset(
                    asset_name=asset_name,
                    asset_class=asset_class,
                    asset_subclass=asset_subclass,
                    purchase_date=datetime.combine(purchase_date, datetime.min.time()),
                    purchase_amount=purchase_amt,
                    useful_life_years=useful_life,
                    residual_value=residual
                )
                st.session_state.model.fixed_assets.append(new_asset)
                st.success(f"Added {asset_name}")
                st.rerun()
        
        # Display assets
        if st.session_state.model.fixed_assets:
            st.markdown("### Asset Register")
            assets_data = []
            total_cost = 0
            total_annual_dep = 0
            
            for asset in st.session_state.model.fixed_assets:
                annual_dep = asset.calculate_annual_depreciation()
                total_cost += asset.purchase_amount
                total_annual_dep += annual_dep
                
                assets_data.append({
                    'Asset': asset.asset_name,
                    'Class': asset.asset_class,
                    'Subclass': asset.asset_subclass,
                    'Purchase Cost': f"${asset.purchase_amount:,.0f}",
                    'Useful Life (yrs)': asset.useful_life_years,
                    'Annual Depreciation': f"${annual_dep:,.0f}"
                })
            
            df_assets = pd.DataFrame(assets_data)
            st.dataframe(df_assets, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Asset Cost", f"${total_cost:,.0f}")
            with col2:
                st.metric("Total Annual Depreciation", f"${total_annual_dep:,.0f}")
        else:
            st.info("Add fixed assets to track depreciation")
    
    with tab3:
        st.subheader("CAPEX Planning")
        
        # Add planned CAPEX
        with st.expander("➕ Add Planned CAPEX"):
            col1, col2 = st.columns(2)
            with col1:
                capex_name = st.text_input("Asset Name", key="capex_name")
                capex_class = st.selectbox("Asset Class",
                    ["Buildings", "Irrigation", "Plant & Equipment", "Motor Vehicles", "Pasture"],
                    key="capex_class")
                capex_subclass = st.text_input("Subclass", key="capex_subclass")
                capex_month = st.number_input("Purchase Month", min_value=1, max_value=12, key="capex_month")
            with col2:
                capex_amt = st.number_input("Purchase Amount ($)", min_value=0.0, key="capex_amt")
                capex_life = st.number_input("Useful Life (years)", min_value=1.0, max_value=100.0,
                                            value=10.0, key="capex_life")
                capex_residual = st.number_input("Residual Value ($)", min_value=0.0, key="capex_residual")
            
            if st.button("Add CAPEX"):
                new_capex = PlannedCapex(
                    asset_name=capex_name,
                    asset_class=capex_class,
                    asset_subclass=capex_subclass,
                    purchase_month=capex_month,
                    purchase_amount=capex_amt,
                    useful_life_years=capex_life,
                    residual_value=capex_residual
                )
                st.session_state.model.planned_capex.append(new_capex)
                st.success(f"Added CAPEX: {capex_name}")
                st.rerun()
        
        # Display planned CAPEX
        if st.session_state.model.planned_capex:
            st.markdown("### Planned Capital Expenditure")
            capex_data = []
            total_capex = 0
            
            for capex in st.session_state.model.planned_capex:
                total_capex += capex.purchase_amount
                capex_data.append({
                    'Asset': capex.asset_name,
                    'Class': capex.asset_class,
                    'Purchase Month': capex.purchase_month,
                    'Amount': f"${capex.purchase_amount:,.0f}",
                    'Useful Life': f"{capex.useful_life_years:.0f} yrs"
                })
            
            df_capex = pd.DataFrame(capex_data)
            st.dataframe(df_capex, use_container_width=True)
            
            st.metric("Total Planned CAPEX", f"${total_capex:,.0f}")
        else:
            st.info("Add planned capital expenditure to model future purchases")

elif page == "🌱 Cropping":
    st.markdown('<div class="main-header">Cropping Enterprise</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Define your cropping program and margins</div>', unsafe_allow_html=True)
    
    st.subheader("Crop Budgets")
    
    # Add new crop
    with st.expander("➕ Add New Crop", expanded=len(st.session_state.model.crop_margins) == 0):
        col1, col2, col3 = st.columns(3)
        with col1:
            crop_name = st.text_input("Crop Name", key="new_crop_name")
            area = st.number_input("Area (ha)", min_value=0.0, key="new_crop_area")
            yield_val = st.number_input("Yield (t/ha)", min_value=0.0, key="new_crop_yield")
        with col2:
            price = st.number_input("Price ($/t)", min_value=0.0, key="new_crop_price")
            deductions = st.number_input("Revenue Deductions (%)", min_value=0.0, max_value=100.0, key="new_crop_ded") / 100
            harvest_month = st.number_input("Harvest Month", min_value=1, max_value=12, key="new_crop_harvest")
        with col3:
            sale_month = st.number_input("Sale Month", min_value=1, max_value=12, key="new_crop_sale")
            direct_cost = st.number_input("Direct Cost ($/ha)", min_value=0.0, key="new_crop_cost")
        
        if st.button("Add Crop"):
            new_crop = CropMargin(
                crop_name=crop_name,
                area_ha=area,
                yield_per_ha=yield_val,
                price_per_unit=price,
                revenue_deductions_pct=deductions,
                harvest_month=harvest_month,
                sale_month=sale_month,
                direct_cost_per_ha=direct_cost
            )
            st.session_state.model.crop_margins.append(new_crop)
            st.success(f"Added {crop_name}")
            st.rerun()
    
    # Display existing crops
    if st.session_state.model.crop_margins:
        st.markdown("### Existing Crops")
        crops_data = []
        for i, crop in enumerate(st.session_state.model.crop_margins):
            revenue = crop.calculate_revenue()
            margin = crop.calculate_margin()
            crops_data.append({
                'Crop': crop.crop_name,
                'Area (ha)': crop.area_ha,
                'Yield (t/ha)': crop.yield_per_ha,
                'Price ($/t)': crop.price_per_unit,
                'Revenue ($)': revenue,
                'Direct Cost ($)': crop.area_ha * crop.direct_cost_per_ha,
                'Gross Margin ($)': margin,
                'GM/ha ($/ha)': margin / crop.area_ha if crop.area_ha > 0 else 0
            })
        
        df_crops = pd.DataFrame(crops_data)
        st.dataframe(df_crops, use_container_width=True)
        
        # Summary
        total_area = df_crops['Area (ha)'].sum()
        total_revenue = df_crops['Revenue ($)'].sum()
        total_margin = df_crops['Gross Margin ($)'].sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Cropped Area", f"{total_area:,.1f} ha")
        with col2:
            st.metric("Total Crop Revenue", f"${total_revenue:,.0f}")
        with col3:
            st.metric("Total Crop Margin", f"${total_margin:,.0f}")

elif page == "🐄 Livestock":
    st.markdown('<div class="main-header">Livestock Enterprise</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage your beef and sheep operations</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Livestock Classes", "Programs", "Stock Reconciliation"])
    
    with tab1:
        st.subheader("Livestock Classes")
        
        # Add livestock class
        with st.expander("➕ Add Livestock Class"):
            col1, col2, col3 = st.columns(3)
            with col1:
                ls_name = st.text_input("Class Name", key="ls_class_name", 
                                       placeholder="e.g., Cows 2yo+")
                ls_type = st.selectbox("Type", ["beef", "sheep"], key="ls_type")
            with col2:
                ls_weight = st.number_input("Average Weight (kg)", min_value=0.0, key="ls_weight")
                ls_price = st.number_input("Price ($/kg)", min_value=0.0, step=0.01, key="ls_price")
            with col3:
                ls_dse = st.number_input("DSE", min_value=0.0, key="ls_dse", 
                                        help="Dry Sheep Equivalent for feed planning")
                ls_death = st.number_input("Death Rate (%/year)", min_value=0.0, max_value=100.0,
                                          value=2.0, key="ls_death") / 100
            
            if st.button("Add Class"):
                new_class = LivestockClass(
                    class_name=ls_name,
                    avg_weight_kg=ls_weight,
                    price_per_kg=ls_price,
                    dse=ls_dse,
                    death_rate_annual=ls_death
                )
                st.session_state.model.livestock_classes.append(new_class)
                st.success(f"Added {ls_name}")
                st.rerun()
        
        # Display classes
        if st.session_state.model.livestock_classes:
            st.markdown("### Defined Classes")
            classes_data = []
            for lc in st.session_state.model.livestock_classes:
                classes_data.append({
                    'Class': lc.class_name,
                    'Type': lc.class_name.lower() if 'cow' in lc.class_name.lower() or 'steer' in lc.class_name.lower() or 'heifer' in lc.class_name.lower() else 'sheep',
                    'Weight (kg)': lc.avg_weight_kg,
                    'Price ($/kg)': lc.price_per_kg,
                    'Value/Head ($)': lc.value_per_head,
                    'DSE': lc.dse,
                    'Death Rate': f"{lc.death_rate_annual*100:.1f}%"
                })
            df_classes = pd.DataFrame(classes_data)
            st.dataframe(df_classes, use_container_width=True)
    
    with tab2:
        st.subheader("Livestock Programs")
        
        # Add program
        with st.expander("➕ Add Livestock Program", expanded=len(st.session_state.model.livestock_programs) == 0):
            col1, col2 = st.columns(2)
            with col1:
                prog_name = st.text_input("Program Name", key="prog_name")
                prog_type = st.selectbox("Enterprise", ["beef", "sheep"], key="prog_type")
                prog_class = st.text_input("Livestock Class", key="prog_class",
                                          help="Must match a class name from Classes tab")
            with col2:
                opening_head = st.number_input("Opening Head Count", min_value=0, key="prog_opening")
                opening_value = st.number_input("Opening Value/Head ($)", min_value=0.0, key="prog_value")
            
            st.markdown("**Sales (optional)**")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                sale_month = st.number_input("Sale Month", min_value=1, max_value=12, key="sale_month")
            with col2:
                sale_head = st.number_input("Head to Sell", min_value=0, key="sale_head")
            with col3:
                sale_price = st.number_input("Price ($/kg)", min_value=0.0, key="sale_price")
            with col4:
                sale_weight = st.number_input("Avg Weight (kg)", min_value=0.0, key="sale_weight")
            
            if st.button("Add Program"):
                new_prog = LivestockProgram(
                    program_name=prog_name,
                    enterprise_type=prog_type,
                    livestock_class=prog_class,
                    opening_head=opening_head,
                    opening_value_per_head=opening_value
                )
                
                # Add sale if specified
                if sale_head > 0:
                    new_prog.sales_by_month[sale_month] = (sale_head, sale_price, sale_weight)
                
                st.session_state.model.livestock_programs.append(new_prog)
                st.success(f"Added {prog_name}")
                st.rerun()
        
        # Display programs
        if st.session_state.model.livestock_programs:
            st.markdown("### Existing Programs")
            progs_data = []
            for prog in st.session_state.model.livestock_programs:
                total_sales_head = sum(h for h, p, w in prog.sales_by_month.values())
                total_purchases_head = sum(h for h, p in prog.purchases_by_month.values())
                
                progs_data.append({
                    'Program': prog.program_name,
                    'Type': prog.enterprise_type,
                    'Class': prog.livestock_class,
                    'Opening Head': prog.opening_head,
                    'Sales (head)': total_sales_head,
                    'Purchases (head)': total_purchases_head,
                    'Opening Value': f"${prog.opening_value_per_head:.2f}/hd"
                })
            
            df_progs = pd.DataFrame(progs_data)
            st.dataframe(df_progs, use_container_width=True)
    
    with tab3:
        st.subheader("Stock Reconciliation")
        
        if st.session_state.calculated and st.session_state.model.stock_reconciliation:
            for prog_name, recon_df in st.session_state.model.stock_reconciliation.items():
                with st.expander(f"📊 {prog_name}", expanded=True):
                    st.dataframe(recon_df, use_container_width=True)
                    
                    # Chart
                    fig = px.line(recon_df, x='month', y='closing', 
                                 title=f"{prog_name} - Monthly Head Count")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Run calculation to see stock reconciliation")

elif page == "💰 Financials":
    st.markdown('<div class="main-header">Financials</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Overheads and other financial items</div>', unsafe_allow_html=True)
    
    st.subheader("Overhead Costs")
    
    # Add overhead
    with st.expander("➕ Add Overhead Category", expanded=len(st.session_state.model.overheads) == 0):
        col1, col2 = st.columns(2)
        with col1:
            oh_name = st.text_input("Category Name", key="oh_name")
            oh_method = st.selectbox("Allocation Method", ["straight_line", "one_off"], key="oh_method")
        with col2:
            if oh_method == "straight_line":
                oh_amount = st.number_input("Monthly Amount ($)", min_value=0.0, key="oh_amount")
            else:
                oh_amount = st.number_input("Amount ($)", min_value=0.0, key="oh_oneoff_amt")
                oh_month = st.number_input("Month", min_value=1, max_value=12, key="oh_oneoff_month")
        
        if st.button("Add Overhead"):
            if oh_method == "straight_line":
                overhead = OverheadCategory(
                    category_name=oh_name,
                    allocation_method=oh_method,
                    monthly_amount=oh_amount
                )
            else:
                overhead = OverheadCategory(
                    category_name=oh_name,
                    allocation_method=oh_method,
                    one_off_month=oh_month,
                    one_off_amount=oh_amount
                )
            st.session_state.model.overheads.append(overhead)
            st.success(f"Added {oh_name}")
            st.rerun()
    
    # Display overheads
    if st.session_state.model.overheads:
        st.markdown("### Overhead Categories")
        oh_data = []
        for oh in st.session_state.model.overheads:
            if oh.allocation_method == "straight_line":
                annual_cost = oh.monthly_amount * 12
                oh_data.append({
                    'Category': oh.category_name,
                    'Method': 'Monthly',
                    'Monthly Amount': f"${oh.monthly_amount:,.2f}",
                    'Annual Cost': f"${annual_cost:,.2f}"
                })
            else:
                oh_data.append({
                    'Category': oh.category_name,
                    'Method': 'One-off',
                    'Monthly Amount': f"Month {oh.one_off_month}",
                    'Annual Cost': f"${oh.one_off_amount:,.2f}"
                })
        
        df_oh = pd.DataFrame(oh_data)
        st.dataframe(df_oh, use_container_width=True)

elif page == "📈 Reports":
    st.markdown('<div class="main-header">Reports</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">View detailed financial statements and reports</div>', unsafe_allow_html=True)
    
    if st.session_state.calculated:
        tab1, tab2, tab3, tab4 = st.tabs(["P&L", "Balance Sheet", "Cash Flow", "Monthly Detail"])
        
        with tab1:
            st.subheader("Profit & Loss Statement")
            if st.session_state.model.annual_pl is not None:
                st.dataframe(st.session_state.model.annual_pl, use_container_width=True)
        
        with tab2:
            st.subheader("Balance Sheet")
            if st.session_state.model.annual_bs is not None:
                st.dataframe(st.session_state.model.annual_bs, use_container_width=True)
        
        with tab3:
            st.subheader("Cash Flow Statement")
            if st.session_state.model.annual_cf is not None:
                st.dataframe(st.session_state.model.annual_cf, use_container_width=True)
        
        with tab4:
            st.subheader("Monthly P&L")
            if st.session_state.model.monthly_pl is not None:
                st.dataframe(st.session_state.model.monthly_pl, use_container_width=True)
    else:
        st.info("Calculate the model first to view reports")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**FarmMate v0.1 MVP**")
st.sidebar.markdown("Converted from Excel model")
