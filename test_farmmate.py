"""
FarmMate Testing Script
Test the calculation engine with a comprehensive sample farm
"""

from datetime import datetime
from farmmate_engine import (
    FarmModel, CropMargin, LivestockProgram, LivestockClass,
    OverheadCategory, Paddock, FixedAsset, PlannedCapex, PlannedDisposal
)

def create_sample_farm():
    """Create a comprehensive sample farm for testing"""
    
    model = FarmModel()
    
    # ========================================================================
    # GENERAL SETUP
    # ========================================================================
    print("Setting up general assumptions...")
    model.general.farm_name = "Test Farm - Mixed Cropping & Livestock"
    model.general.start_date = datetime(2026, 7, 1)
    model.general.num_months = 12
    model.general.income_tax_rate = 0.275
    model.general.gst_rate = 0.10
    
    # ========================================================================
    # OPENING BALANCES
    # ========================================================================
    print("Setting opening balances...")
    model.opening_balances.cash = 100000
    model.opening_balances.trade_debtors = 50000
    model.opening_balances.inventory_grain = 30000
    model.opening_balances.inventory_livestock = 200000
    model.opening_balances.fixed_assets = 800000
    model.opening_balances.land_water = 3000000
    
    model.opening_balances.trade_creditors = 40000
    model.opening_balances.debt_facilities = 500000
    model.opening_balances.share_capital = 2500000
    model.opening_balances.retained_earnings = 1140000
    
    # ========================================================================
    # PADDOCKS
    # ========================================================================
    print("Adding paddocks...")
    paddocks = [
        Paddock("North 1", "Main Property", 150),
        Paddock("North 2", "Main Property", 150),
        Paddock("South 1", "Main Property", 200),
        Paddock("South 2", "Main Property", 200),
        Paddock("East", "Main Property", 100),
    ]
    model.paddocks.extend(paddocks)
    
    # ========================================================================
    # FIXED ASSETS
    # ========================================================================
    print("Adding fixed assets...")
    assets = [
        FixedAsset("Tractor - John Deere 8R", "Plant & Equipment", "Tractor",
                  datetime(2020, 1, 1), 250000, 15, 50000),
        FixedAsset("Header - Case IH 9240", "Plant & Equipment", "Harvester",
                  datetime(2021, 6, 1), 400000, 10, 80000),
        FixedAsset("Seeder - Simplicity", "Plant & Equipment", "Seeder",
                  datetime(2019, 3, 1), 150000, 12, 30000),
        FixedAsset("Homestead", "Buildings", "Dwelling",
                  datetime(2010, 1, 1), 300000, 50, 100000),
        FixedAsset("Machinery Shed", "Buildings", "Shed",
                  datetime(2015, 1, 1), 120000, 40, 20000),
        FixedAsset("Pasture Improvement", "Pasture", "Establishment",
                  datetime(2023, 1, 1), 80000, 7, 0),
    ]
    model.fixed_assets.extend(assets)
    
    # ========================================================================
    # PLANNED CAPEX
    # ========================================================================
    print("Adding planned CAPEX...")
    capex_items = [
        PlannedCapex("Spray Rig - New", "Plant & Equipment", "Sprayer",
                    purchase_month=3, purchase_amount=85000,
                    useful_life_years=10, residual_value=15000),
        PlannedCapex("Utility Vehicle", "Motor Vehicles", "Utility",
                    purchase_month=5, purchase_amount=45000,
                    useful_life_years=8, residual_value=10000),
    ]
    model.planned_capex.extend(capex_items)
    
    # ========================================================================
    # CROPPING
    # ========================================================================
    print("Adding crops...")
    crops = [
        CropMargin(
            crop_name="Wheat",
            area_ha=200,
            yield_per_ha=3.5,  # tonnes/ha
            price_per_unit=350,  # $/tonne
            revenue_deductions_pct=0.05,  # 5% for storage, levies
            harvest_month=11,
            sale_month=12,
            direct_cost_per_ha=450  # seed, fert, chem, fuel, etc.
        ),
        CropMargin(
            crop_name="Barley",
            area_ha=150,
            yield_per_ha=4.0,
            price_per_unit=280,
            revenue_deductions_pct=0.05,
            harvest_month=11,
            sale_month=1,  # Next year
            direct_cost_per_ha=380
        ),
        CropMargin(
            crop_name="Canola",
            area_ha=100,
            yield_per_ha=2.2,
            price_per_unit=650,
            revenue_deductions_pct=0.06,
            harvest_month=12,
            sale_month=1,
            direct_cost_per_ha=520
        ),
    ]
    model.crop_margins.extend(crops)
    
    # ========================================================================
    # LIVESTOCK CLASSES
    # ========================================================================
    print("Adding livestock classes...")
    livestock_classes = [
        LivestockClass("Cows 2yo+", 550, 3.20, 12, 0.02),  # weight, $/kg, DSE, death%
        LivestockClass("Heifers 1yo", 350, 3.50, 9, 0.02),
        LivestockClass("Steers 1yo+", 400, 4.00, 9, 0.02),
        LivestockClass("Calves", 150, 3.80, 7, 0.03),
    ]
    model.livestock_classes.extend(livestock_classes)
    
    # ========================================================================
    # LIVESTOCK PROGRAMS
    # ========================================================================
    print("Adding livestock programs...")
    
    # Breeding cows program
    cows_program = LivestockProgram(
        program_name="Breeding Cows",
        enterprise_type="beef",
        livestock_class="Cows 2yo+",
        opening_head=150,
        opening_value_per_head=1760  # 550kg @ $3.20/kg
    )
    # Calving in December (month 6)
    cows_program.births_by_month[6] = 135  # 90% calving rate
    # Sell cull cows in May (month 11)
    cows_program.sales_by_month[11] = (20, 2.80, 500)  # head, $/kg, weight
    # Direct costs
    for month in range(1, 13):
        cows_program.direct_costs_by_month[month] = {
            'animal_health': 150 / 12,  # $150/hd/year
            'fodder': 200 / 12
        }
    model.livestock_programs.append(cows_program)
    
    # Trading steers program
    steers_program = LivestockProgram(
        program_name="Trading Steers",
        enterprise_type="beef",
        livestock_class="Steers 1yo+",
        opening_head=80,
        opening_value_per_head=1400
    )
    # Purchase additional steers in August (month 2)
    steers_program.purchases_by_month[2] = (50, 1300)  # head, $/head
    # Sell finished steers in April (month 10)
    steers_program.sales_by_month[10] = (100, 4.20, 550)
    # Direct costs
    for month in range(1, 13):
        steers_program.direct_costs_by_month[month] = {
            'animal_health': 100 / 12,
            'fodder': 250 / 12
        }
    model.livestock_programs.append(steers_program)
    
    # ========================================================================
    # OVERHEADS
    # ========================================================================
    print("Adding overheads...")
    overheads = [
        OverheadCategory("Wages & Salaries", "straight_line", monthly_amount=12000),
        OverheadCategory("Superannuation", "straight_line", monthly_amount=1320),
        OverheadCategory("Rates & Land Tax", "one_off", one_off_month=9, one_off_amount=15000),
        OverheadCategory("Insurance", "one_off", one_off_month=7, one_off_amount=25000),
        OverheadCategory("Power & Water", "straight_line", monthly_amount=800),
        OverheadCategory("Fuel (Non-Direct)", "straight_line", monthly_amount=1500),
        OverheadCategory("Repairs & Maintenance", "straight_line", monthly_amount=2000),
        OverheadCategory("Professional Fees", "straight_line", monthly_amount=800),
        OverheadCategory("Bank Fees", "straight_line", monthly_amount=150),
    ]
    model.overheads.extend(overheads)
    
    return model


def run_tests():
    """Run comprehensive tests on the model"""
    
    print("="*80)
    print("FARMMATE CALCULATION ENGINE - COMPREHENSIVE TEST")
    print("="*80)
    
    # Create sample farm
    model = create_sample_farm()
    
    # Run calculation
    print("\nRunning calculations...")
    monthly_pl, monthly_bs, monthly_cf = model.calculate()
    
    # ========================================================================
    # DISPLAY RESULTS
    # ========================================================================
    
    print("\n" + "="*80)
    print("MONTHLY P&L SUMMARY")
    print("="*80)
    print(monthly_pl[['month', 'total_income', 'total_direct_costs', 'gross_profit', 
                      'overheads', 'depreciation', 'ebitda', 'ebit', 'net_profit']].to_string())
    
    print("\n" + "="*80)
    print("ANNUAL SUMMARY")
    print("="*80)
    if model.annual_pl is not None:
        print(model.annual_pl.to_string())
    
    print("\n" + "="*80)
    print("ENTERPRISE BREAKDOWN (Annual)")
    print("="*80)
    
    # Crop summary
    print("\nCROPPING:")
    for crop in model.crop_margins:
        revenue = crop.calculate_revenue()
        margin = crop.calculate_margin()
        print(f"  {crop.crop_name:20} {crop.area_ha:6.0f} ha  "
              f"Revenue: ${revenue:10,.0f}  Margin: ${margin:10,.0f}  "
              f"$/ha: ${margin/crop.area_ha:6.0f}")
    
    total_crop_revenue = sum(c.calculate_revenue() for c in model.crop_margins)
    total_crop_margin = sum(c.calculate_margin() for c in model.crop_margins)
    print(f"  {'TOTAL CROPPING':20} {sum(c.area_ha for c in model.crop_margins):6.0f} ha  "
          f"Revenue: ${total_crop_revenue:10,.0f}  Margin: ${total_crop_margin:10,.0f}")
    
    # Livestock summary
    print("\nLIVESTOCK:")
    for program in model.livestock_programs:
        print(f"  {program.program_name:30} Opening: {program.opening_head:4} hd")
        if program.program_name in model.stock_reconciliation:
            recon = model.stock_reconciliation[program.program_name]
            closing = recon.iloc[-1]['closing']
            total_sales = recon['sales'].sum()
            total_purchases = recon['purchases'].sum()
            print(f"    Purchases: {total_purchases:4.0f}  Sales: {total_sales:4.0f}  Closing: {closing:4.0f}")
    
    print("\n" + "="*80)
    print("BALANCE SHEET (Year End)")
    print("="*80)
    if model.annual_bs is not None and len(model.annual_bs) > 0:
        final_bs = model.annual_bs.iloc[-1]
        print(f"\nASSETS:")
        print(f"  Cash:                ${final_bs['cash']:12,.0f}")
        print(f"  Trade Debtors:       ${final_bs['trade_debtors']:12,.0f}")
        print(f"  Inventory:           ${final_bs['inventory']:12,.0f}")
        print(f"  Fixed Assets:        ${final_bs['fixed_assets']:12,.0f}")
        print(f"  Land & Water:        ${final_bs['land_water']:12,.0f}")
        print(f"  TOTAL ASSETS:        ${final_bs['total_assets']:12,.0f}")
        
        print(f"\nLIABILITIES:")
        print(f"  Trade Creditors:     ${final_bs['trade_creditors']:12,.0f}")
        print(f"  Debt:                ${final_bs['debt']:12,.0f}")
        print(f"  TOTAL LIABILITIES:   ${final_bs['total_liabilities']:12,.0f}")
        
        print(f"\nEQUITY:")
        print(f"  Share Capital:       ${final_bs['share_capital']:12,.0f}")
        print(f"  Retained Earnings:   ${final_bs['retained_earnings']:12,.0f}")
        print(f"  TOTAL EQUITY:        ${final_bs['total_equity']:12,.0f}")
        
        print(f"\nBALANCE CHECK:         ${final_bs['balance_check']:12,.2f}")
    
    print("\n" + "="*80)
    print("KEY PERFORMANCE INDICATORS")
    print("="*80)
    kpis = model.get_kpis()
    print(f"EBITDA:                ${kpis['ebitda']:12,.0f}")
    print(f"EBIT:                  ${kpis['ebitda'] - monthly_pl['depreciation'].sum():12,.0f}")
    print(f"Net Profit:            ${kpis['net_profit']:12,.0f}")
    print(f"Closing Cash:          ${kpis['closing_cash']:12,.0f}")
    print(f"Total Debt:            ${kpis['total_debt']:12,.0f}")
    print(f"Net Assets:            ${kpis['net_assets']:12,.0f}")
    print(f"Return on Assets:      {kpis['roa']:12.2f}%")
    
    # Asset summary
    print("\n" + "="*80)
    print("FIXED ASSETS & DEPRECIATION")
    print("="*80)
    total_asset_cost = 0
    total_annual_dep = 0
    for asset in model.fixed_assets:
        annual_dep = asset.calculate_annual_depreciation()
        total_asset_cost += asset.purchase_amount
        total_annual_dep += annual_dep
        print(f"  {asset.asset_name:30} ${asset.purchase_amount:10,.0f}  "
              f"Dep: ${annual_dep:8,.0f}/yr")
    
    print(f"  {'TOTAL':30} ${total_asset_cost:10,.0f}  Dep: ${total_annual_dep:8,.0f}/yr")
    print(f"  Monthly depreciation: ${total_annual_dep/12:,.0f}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    
    return model


if __name__ == "__main__":
    model = run_tests()
