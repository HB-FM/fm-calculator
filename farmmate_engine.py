"""
FarmMate Calculation Engine
Core financial model conversion from Excel to Python
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
from decimal import Decimal


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class GeneralAssumptions:
    """Core farm setup and financial assumptions (from 1.10 GENERAL)"""
    farm_name: str = "Farm"
    start_date: datetime = datetime(2026, 7, 1)
    num_months: int = 12
    financial_year_end_month: int = 6  # June = 6
    
    # Tax rates
    income_tax_rate: float = 0.275
    gst_rate: float = 0.10
    capital_gains_tax_rate: float = 0.23
    investor_tax_rate: float = 0.30
    tax_payment_month: int = 9  # September
    
    # GST settings
    gst_reporting_period: str = "quarterly"  # "monthly", "quarterly", "annual"
    gst_payment_delay: int = 1  # Months after period end to pay
    
    # Interest rates
    overdraft_rate: float = 0.09
    cash_interest_rate: float = 0.03
    
    # Management fees
    base_management_fee: float = 0.0
    performance_fee_hurdle: float = 0.03  # 3% ROA
    performance_fee_ebit_share: float = 0.20  # 20% of EBIT above hurdle
    
    # Payout ratios
    payout_ratio_npat: float = 0.0
    payout_ratio_fcf: float = 0.0
    
    def get_month_dates(self) -> List[datetime]:
        """Generate list of month-end dates for the model period"""
        dates = []
        current = self.start_date
        for i in range(self.num_months):
            # Get last day of month
            if current.month == 12:
                next_month = current.replace(year=current.year + 1, month=1, day=1)
            else:
                next_month = current.replace(month=current.month + 1, day=1)
            month_end = next_month - timedelta(days=1)
            dates.append(month_end)
            current = next_month
        return dates
    
    def get_financial_year(self, date: datetime) -> int:
        """Get financial year for a given date"""
        if date.month <= self.financial_year_end_month:
            return date.year
        else:
            return date.year + 1
    
    def get_gst_payment_months(self) -> List[int]:
        """Get months when GST is paid based on reporting period"""
        payment_months = []
        
        if self.gst_reporting_period == "monthly":
            # Pay every month with delay
            for month in range(1, self.num_months + 1):
                payment_month = month + self.gst_payment_delay
                if payment_month <= self.num_months:
                    payment_months.append(payment_month)
        
        elif self.gst_reporting_period == "quarterly":
            # Pay in months 4, 7, 10, 13 (with delay)
            for quarter_end in [3, 6, 9, 12]:
                payment_month = quarter_end + self.gst_payment_delay
                if payment_month <= self.num_months:
                    payment_months.append(payment_month)
        
        elif self.gst_reporting_period == "annual":
            # Pay once at year end
            payment_month = 12 + self.gst_payment_delay
            if payment_month <= self.num_months:
                payment_months.append(payment_month)
        
        return payment_months


@dataclass
class InflationRates:
    """Inflation assumptions (from 1.11 INFLATION)"""
    # Income inflation
    all_income: float = 0.028
    wool: float = 0.028
    beef: float = 0.028
    sheep: float = 0.028
    crops: float = 0.028
    
    # Expense inflation
    all_expenses: float = 0.028
    freight: float = 0.028
    storage_handling: float = 0.028
    levies_royalties: float = 0.028
    electricity: float = 0.028
    labour_contracts: float = 0.028
    agronomy: float = 0.028
    animal_health: float = 0.028
    fertiliser: float = 0.028
    chemicals: float = 0.028
    fuel_oil: float = 0.028
    agistment: float = 0.028
    repairs_maintenance: float = 0.028
    other_expenses: float = 0.028
    
    # Capital inflation
    buildings: float = 0.028
    irrigation: float = 0.028
    plant_equipment: float = 0.028
    motor_vehicles: float = 0.028
    water_entitlements: float = 0.028
    pasture_establishment: float = 0.028
    
    def apply_inflation(self, base_value: float, category: str, years: float) -> float:
        """Apply inflation to a value"""
        rate = getattr(self, category, self.all_expenses)
        return base_value * ((1 + rate) ** years)


@dataclass
class PaymentTiming:
    """Payment timing assumptions in months (from 1.10 GENERAL)"""
    # Beef
    beef_sales: int = 1
    beef_animal_health: int = 0
    beef_contract_services: int = 0
    beef_fodder_agistment: int = 0
    beef_freight: int = 0
    beef_selling_costs: int = 0
    
    # Sheep
    sheep_sales: int = 1
    sheep_animal_health: int = 0
    sheep_contract_services: int = 0
    sheep_fodder_agistment: int = 0
    sheep_freight: int = 1
    sheep_selling_costs: int = 0
    
    # Wool
    wool_sales: int = 1
    wool_freight: int = 1
    wool_selling_costs: int = 0
    shearing_costs: int = 0
    shearing_supplies: int = 0
    
    # Crops
    crop_sales: int = 1
    crop_agronomy: int = 1
    crop_chemicals: int = 0
    crop_contract_services: int = 1
    crop_fertiliser: int = 0
    crop_freight: int = 0
    crop_fuel: int = 0
    crop_seed: int = 0
    crop_levies: int = 0
    
    # Overheads
    overhead_default: int = 0


@dataclass
class Paddock:
    """Individual paddock definition (from 1.20 PADDOCKS)"""
    name: str
    property_name: str
    size_ha: float
    rotation: Dict[int, str] = field(default_factory=dict)  # {month: enterprise_code}
    
    def get_enterprise_allocation(self, month: int) -> str:
        """Get which enterprise is allocated to this paddock in a given month"""
        return self.rotation.get(month, 'Fallow')
    
    def set_rotation(self, rotations: Dict[int, str]):
        """Set rotation schedule for the paddock"""
        self.rotation = rotations


@dataclass  
class FixedAsset:
    """Fixed asset definition (from 1.30 FAR)"""
    asset_name: str
    asset_class: str  # Buildings, Irrigation, Plant & Equipment, Motor Vehicles, Pasture
    asset_subclass: str
    purchase_date: datetime
    purchase_amount: float
    useful_life_years: float
    residual_value: float = 0.0
    depreciation_method: str = 'straight_line'
    
    def calculate_annual_depreciation(self) -> float:
        """Calculate annual depreciation"""
        if self.depreciation_method == 'straight_line':
            depreciable_amount = self.purchase_amount - self.residual_value
            return depreciable_amount / self.useful_life_years
        return 0.0
    
    def calculate_monthly_depreciation(self) -> float:
        """Calculate monthly depreciation"""
        return self.calculate_annual_depreciation() / 12
    
    def calculate_written_down_value(self, months_elapsed: int) -> float:
        """Calculate current written down value"""
        monthly_dep = self.calculate_monthly_depreciation()
        total_depreciation = monthly_dep * months_elapsed
        return max(self.purchase_amount - total_depreciation, self.residual_value)


@dataclass
class PlannedCapex:
    """Planned capital expenditure (from 1.31 CAPEX)"""
    asset_name: str
    asset_class: str
    asset_subclass: str
    purchase_month: int
    purchase_amount: float
    useful_life_years: float
    residual_value: float = 0.0
    funding_source: str = "Cash"  # Cash, Debt, Equity
    
    def to_fixed_asset(self, start_date: datetime) -> FixedAsset:
        """Convert planned CAPEX to fixed asset after purchase"""
        # Calculate purchase date
        purchase_date = start_date + relativedelta(months=self.purchase_month - 1)
        
        return FixedAsset(
            asset_name=self.asset_name,
            asset_class=self.asset_class,
            asset_subclass=self.asset_subclass,
            purchase_date=purchase_date,
            purchase_amount=self.purchase_amount,
            useful_life_years=self.useful_life_years,
            residual_value=self.residual_value
        )


@dataclass
class PlannedDisposal:
    """Planned asset disposal (from 1.32 DISPOSALS)"""
    asset_name: str
    disposal_month: int
    sale_price: float
    disposal_costs: float = 0.0
    
    def calculate_profit_on_sale(self, written_down_value: float) -> float:
        """Calculate profit/loss on disposal"""
        net_proceeds = self.sale_price - self.disposal_costs
        return net_proceeds - written_down_value


@dataclass
class PastureProgram:
    """Pasture maintenance, establishment, or fodder crop program"""
    program_name: str
    program_type: str  # 'maintenance', 'establishment', 'fodder'
    paddock_name: str
    area_ha: float
    start_month: int
    
    # Activities and costs
    activities: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # {activity: (rate_per_ha, cost_per_unit)}
    total_cost_per_ha: float = 0.0
    
    # For fodder crops
    fodder_yield_per_ha: float = 0.0  # tonnes/ha
    fodder_value_per_tonne: float = 0.0  # $/tonne (for valuation if consumed on farm)
    
    def calculate_total_cost(self) -> float:
        """Calculate total program cost"""
        cost_per_ha = sum(rate * cost for rate, cost in self.activities.values())
        self.total_cost_per_ha = cost_per_ha
        return cost_per_ha * self.area_ha
    
    def get_monthly_costs(self, month: int) -> float:
        """Get costs for a specific month (simplified - spread evenly)"""
        if month < self.start_month or month > self.start_month + 6:
            return 0.0
        
        total_cost = self.calculate_total_cost()
        # Spread over 6 months from start
        return total_cost / 6
    

@dataclass
class CropProgram:
    """Crop growing program (from 2.2 CROP PROGRAMS)"""
    crop_name: str
    inputs: Dict[str, Tuple[float, float]]  # {input_name: (units_per_ha, price_per_unit)}
    total_cost_per_ha: float = 0.0
    
    def calculate_cost_per_ha(self) -> float:
        """Calculate total cost per hectare"""
        self.total_cost_per_ha = sum(units * price for units, price in self.inputs.values())
        return self.total_cost_per_ha


@dataclass
class CropMargin:
    """Crop revenue and margin calculation (from 2.3 CROP MARGINS)"""
    crop_name: str
    area_ha: float
    yield_per_ha: float  # tonnes or kg
    price_per_unit: float  # $ per tonne or kg
    revenue_deductions_pct: float = 0.0  # Storage, levies, etc.
    harvest_month: int = 1
    sale_month: int = 1
    direct_cost_per_ha: float = 0.0
    
    def calculate_revenue(self) -> float:
        """Calculate gross revenue"""
        gross_revenue = self.area_ha * self.yield_per_ha * self.price_per_unit
        return gross_revenue * (1 - self.revenue_deductions_pct)
    
    def calculate_margin(self) -> float:
        """Calculate gross margin"""
        revenue = self.calculate_revenue()
        total_costs = self.area_ha * self.direct_cost_per_ha
        return revenue - total_costs


@dataclass
class LivestockClass:
    """Livestock class definition (beef or sheep)"""
    class_name: str
    avg_weight_kg: float
    price_per_kg: float = 0.0
    dse: float = 0.0  # Dry Sheep Equivalent
    death_rate_annual: float = 0.02  # 2% default
    
    # Breeding parameters (for breeding females only)
    is_breeding_female: bool = False
    breeding_rate: float = 0.0  # % that produce offspring (e.g., 0.90 for 90%)
    offspring_class: str = ""  # Class name that offspring become
    offspring_sex_split_male: float = 0.5  # % male
    weaning_month: int = 0  # Month when offspring are weaned/counted
    
    # Wool production parameters (for wool-producing sheep)
    produces_wool: bool = False
    fleece_weight_kg: float = 0.0  # Greasy fleece weight per head
    wool_micron: float = 0.0  # Fibre diameter
    wool_yield_pct: float = 0.0  # Clean wool percentage (e.g., 0.65 for 65%)
    shearing_frequency: int = 1  # Times per year (1 or 2)
    shearing_months: List[int] = field(default_factory=list)  # Months when shorn
    
    @property
    def value_per_head(self) -> float:
        """Calculate value per head from weight and price"""
        return self.avg_weight_kg * self.price_per_kg
    
    def annual_wool_production_kg(self) -> float:
        """Calculate annual clean wool production per head"""
        if not self.produces_wool:
            return 0.0
        greasy_wool = self.fleece_weight_kg * self.shearing_frequency
        clean_wool = greasy_wool * self.wool_yield_pct
        return clean_wool


@dataclass
class WoolProduction:
    """Wool production and sales for a sheep program"""
    program_name: str
    livestock_class: str
    
    # Shearing details
    shearing_cost_per_head: float = 0.0
    crutching_cost_per_head: float = 0.0
    shearing_supplies_per_head: float = 0.0
    
    # Wool marketing
    wool_price_per_kg_clean: float = 0.0  # $/kg clean wool
    wool_freight_per_bale: float = 0.0
    wool_selling_costs_pct: float = 0.0  # % of gross proceeds
    bale_weight_kg: float = 150.0  # Average bale weight
    
    # Monthly production (calculated from shearing schedule)
    production_by_month: Dict[int, float] = field(default_factory=dict)  # {month: kg clean wool}
    sales_by_month: Dict[int, float] = field(default_factory=dict)  # {month: kg clean wool sold}
    
    def calculate_monthly_production(self, sheep_count: int, livestock_class: LivestockClass, month: int) -> float:
        """Calculate wool production for a month based on shearing schedule"""
        if not livestock_class.produces_wool:
            return 0.0
        
        if month not in livestock_class.shearing_months:
            return 0.0
        
        # Wool per head for this shearing
        greasy_per_head = livestock_class.fleece_weight_kg
        clean_per_head = greasy_per_head * livestock_class.wool_yield_pct
        
        total_production = sheep_count * clean_per_head
        self.production_by_month[month] = total_production
        
        return total_production
    
    def calculate_wool_revenue(self, month: int) -> float:
        """Calculate wool revenue for the month"""
        if month not in self.sales_by_month:
            return 0.0
        
        kg_sold = self.sales_by_month[month]
        gross_revenue = kg_sold * self.wool_price_per_kg_clean
        
        # Deduct selling costs
        selling_costs = gross_revenue * self.wool_selling_costs_pct
        
        # Deduct freight (per bale)
        num_bales = kg_sold / self.bale_weight_kg
        freight_costs = num_bales * self.wool_freight_per_bale
        
        net_revenue = gross_revenue - selling_costs - freight_costs
        
        return net_revenue
    
    def calculate_shearing_costs(self, sheep_count: int, month: int, livestock_class: LivestockClass) -> float:
        """Calculate shearing costs for the month"""
        if month not in livestock_class.shearing_months:
            return 0.0
        
        total_cost = (
            sheep_count * self.shearing_cost_per_head +
            sheep_count * self.shearing_supplies_per_head
        )
        
        return total_cost
    

@dataclass
class LivestockProgram:
    """Livestock production program with full stock reconciliation"""
    program_name: str
    enterprise_type: str  # 'beef' or 'sheep'
    livestock_class: str  # Class name (e.g., 'Cows 2yo+', 'Ewes')
    
    # Opening position
    opening_head: int = 0
    opening_value_per_head: float = 0.0
    
    # Monthly movements
    purchases_by_month: Dict[int, Tuple[int, float]] = field(default_factory=dict)  # {month: (head, price)}
    sales_by_month: Dict[int, Tuple[int, float, float]] = field(default_factory=dict)  # {month: (head, price_per_kg, avg_weight_kg)}
    deaths_by_month: Dict[int, int] = field(default_factory=dict)
    births_by_month: Dict[int, int] = field(default_factory=dict)
    transfers_in_by_month: Dict[int, int] = field(default_factory=dict)  # Moving between classes
    transfers_out_by_month: Dict[int, int] = field(default_factory=dict)
    
    # Direct costs
    direct_costs_by_month: Dict[int, Dict[str, float]] = field(default_factory=dict)  # {month: {category: amount}}
    
    # Mortality and reproduction
    death_rate_annual: float = 0.02  # 2% annual
    birth_rate_annual: float = 0.0  # Only for breeding females
    birth_month: int = 0  # Month when births occur
    
    def get_monthly_deaths(self, month: int, opening_head: int) -> int:
        """Calculate deaths for the month based on annual death rate"""
        if month in self.deaths_by_month:
            return self.deaths_by_month[month]
        # Otherwise use death rate (spread monthly)
        monthly_death_rate = self.death_rate_annual / 12
        return int(opening_head * monthly_death_rate)
    
    def calculate_natural_increase(self, month: int, livestock_class: LivestockClass) -> int:
        """Calculate natural increase (births) based on livestock class breeding parameters"""
        if not livestock_class.is_breeding_female:
            return 0
        
        if month != livestock_class.weaning_month:
            return 0
        
        # Calculate breeding females (opening + purchases - sales - deaths)
        breeding_females = self.opening_head
        
        # Add purchases up to this month
        for m, (head, price) in self.purchases_by_month.items():
            if m < month:
                breeding_females += head
        
        # Subtract sales up to this month
        for m, (head, price, weight) in self.sales_by_month.items():
            if m < month:
                breeding_females -= head
        
        # Subtract deaths up to this month
        for m in range(1, month):
            breeding_females -= self.get_monthly_deaths(m, breeding_females)
        
        # Calculate offspring
        offspring = int(breeding_females * livestock_class.breeding_rate)
        
        return offspring
    
    def apply_class_transfer(self, from_month: int, to_month: int, transfer_head: int):
        """Apply transfer of stock between classes (e.g., calves → yearlings)"""
        self.transfers_out_by_month[from_month] = transfer_head
        # Note: The receiving class should have a corresponding transfer_in
    
    def calculate_stock_reconciliation(self, num_months: int) -> pd.DataFrame:
        """Calculate month-by-month stock reconciliation"""
        recon_data = []
        
        current_head = self.opening_head
        
        for month in range(1, num_months + 1):
            # Opening
            opening = current_head
            
            # Movements
            purchases = self.purchases_by_month.get(month, (0, 0))[0]
            sales = self.sales_by_month.get(month, (0, 0, 0))[0]
            deaths = self.get_monthly_deaths(month, opening)
            births = self.births_by_month.get(month, 0)
            transfers_in = self.transfers_in_by_month.get(month, 0)
            transfers_out = self.transfers_out_by_month.get(month, 0)
            
            # Closing
            closing = opening + purchases + births + transfers_in - sales - deaths - transfers_out
            
            recon_data.append({
                'month': month,
                'opening': opening,
                'purchases': purchases,
                'births': births,
                'transfers_in': transfers_in,
                'deaths': deaths,
                'sales': sales,
                'transfers_out': transfers_out,
                'closing': closing
            })
            
            current_head = closing
        
        return pd.DataFrame(recon_data)
    
    def calculate_trading_profit(self, month: int, opening_value: float, closing_value: float) -> Dict:
        """Calculate trading profit for the month"""
        # Sales revenue
        sales_revenue = 0.0
        if month in self.sales_by_month:
            head, price_per_kg, avg_weight = self.sales_by_month[month]
            sales_revenue = head * price_per_kg * avg_weight
        
        # Purchase cost
        purchase_cost = 0.0
        if month in self.purchases_by_month:
            head, price = self.purchases_by_month[month]
            purchase_cost = head * price
        
        # Natural increase/decrease value
        births_value = 0.0
        if month in self.births_by_month:
            # Value births at opening value (simplified)
            births_value = self.births_by_month[month] * self.opening_value_per_head
        
        deaths_value = 0.0
        if month in self.deaths_by_month:
            deaths_value = self.deaths_by_month[month] * self.opening_value_per_head
        
        # Stock value change
        stock_value_change = closing_value - opening_value
        
        # Trading P&L = Sales - Purchases + Stock change
        trading_pl = sales_revenue - purchase_cost + stock_value_change + births_value - deaths_value
        
        return {
            'sales_revenue': sales_revenue,
            'purchase_cost': purchase_cost,
            'births_value': births_value,
            'deaths_value': deaths_value,
            'stock_value_change': stock_value_change,
            'trading_profit': trading_pl
        }
    
    def calculate_closing_head(self, month: int) -> int:
        """Calculate closing head count for a month"""
        opening = self.opening_head
        purchases = sum(h for m, (h, p) in self.purchases_by_month.items() if m <= month)
        sales = sum(h for m, (h, p, w) in self.sales_by_month.items() if m <= month)
        deaths = sum(self.deaths_by_month.get(m, 0) for m in range(1, month + 1))
        births = sum(self.births_by_month.get(m, 0) for m in range(1, month + 1))
        transfers_in = sum(self.transfers_in_by_month.get(m, 0) for m in range(1, month + 1))
        transfers_out = sum(self.transfers_out_by_month.get(m, 0) for m in range(1, month + 1))
        return opening + purchases + births + transfers_in - sales - deaths - transfers_out


@dataclass
class OverheadCategory:
    """Overhead cost category (from 4 OVERHEADS)"""
    category_name: str
    allocation_method: str  # 'straight_line' or 'one_off'
    monthly_amount: float = 0.0
    one_off_month: Optional[int] = None
    one_off_amount: Optional[float] = None
    
    def get_monthly_cost(self, month: int) -> float:
        """Get cost for a specific month"""
        if self.allocation_method == 'straight_line':
            return self.monthly_amount
        elif self.allocation_method == 'one_off' and month == self.one_off_month:
            return self.one_off_amount or 0.0
        return 0.0


@dataclass
class DebtFacility:
    """Debt facility (from 6.2 DEBT)"""
    description: str
    facility_type: str  # 'term_loan', 'overdraft', 'related_party'
    principal: float
    interest_rate: float
    establishment_date: datetime
    repayment_schedule: Dict[int, float] = field(default_factory=dict)  # {month: repayment}
    drawdown_schedule: Dict[int, float] = field(default_factory=dict)  # {month: drawdown}
    
    def calculate_balance(self, month: int) -> float:
        """Calculate outstanding balance at month end"""
        balance = self.principal
        for m in range(1, month + 1):
            balance += self.drawdown_schedule.get(m, 0)
            balance -= self.repayment_schedule.get(m, 0)
        return max(balance, 0)
    
    def calculate_interest(self, month: int) -> float:
        """Calculate interest for the month"""
        balance = self.calculate_balance(month - 1) if month > 1 else self.principal
        monthly_rate = self.interest_rate / 12
        return balance * monthly_rate


@dataclass
class OpeningBalances:
    """Opening balance sheet (from 7 BS OPENBAL)"""
    cash: float = 0.0
    trade_debtors: float = 0.0
    inventory_grain: float = 0.0
    inventory_wool: float = 0.0
    inventory_livestock: float = 0.0
    prepayments: float = 0.0
    fixed_assets: float = 0.0
    land_water: float = 0.0
    
    trade_creditors: float = 0.0
    accruals: float = 0.0
    gst_liability: float = 0.0  # Negative if receivable, positive if payable
    tax_payable: float = 0.0
    debt_facilities: float = 0.0
    
    share_capital: float = 0.0
    retained_earnings: float = 0.0
    
    def total_assets(self) -> float:
        return (self.cash + self.trade_debtors + self.inventory_grain +
                self.inventory_wool + self.inventory_livestock + self.prepayments +
                self.fixed_assets + self.land_water)
    
    def total_liabilities(self) -> float:
        return (self.trade_creditors + self.accruals + 
                max(self.gst_liability, 0) +  # Only include if payable
                self.tax_payable + self.debt_facilities)
    
    def total_equity(self) -> float:
        return self.share_capital + self.retained_earnings
    
    def check_balance(self) -> bool:
        """Check if balance sheet balances"""
        assets = self.total_assets()
        # If GST is receivable (negative), it's an asset
        if self.gst_liability < 0:
            assets += abs(self.gst_liability)
        
        liabs_equity = self.total_liabilities() + self.total_equity()
        return abs(assets - liabs_equity) < 0.01


@dataclass
class GSTCalculation:
    """GST calculation for a period"""
    gst_on_sales: float = 0.0  # GST collected
    gst_on_purchases: float = 0.0  # GST paid
    net_gst: float = 0.0  # Payable (positive) or receivable (negative)
    
    def calculate_net_gst(self):
        """Calculate net GST position"""
        self.net_gst = self.gst_on_sales - self.gst_on_purchases
        return self.net_gst


# ============================================================================
# CALCULATION ENGINE
# ============================================================================

class FarmModel:
    """Main farm financial model calculation engine"""
    
    def __init__(self):
        self.general = GeneralAssumptions()
        self.inflation = InflationRates()
        self.payment_timing = PaymentTiming()
        self.opening_balances = OpeningBalances()
        
        self.paddocks: List[Paddock] = []
        self.fixed_assets: List[FixedAsset] = []
        self.planned_capex: List[PlannedCapex] = []
        self.planned_disposals: List[PlannedDisposal] = []
        self.crop_programs: List[CropProgram] = []
        self.crop_margins: List[CropMargin] = []
        self.pasture_programs: List[PastureProgram] = []  # Pasture maintenance/establishment/fodder
        self.livestock_classes: List[LivestockClass] = []
        self.livestock_programs: List[LivestockProgram] = []
        self.wool_production: List[WoolProduction] = []  # Wool production for sheep programs
        self.overheads: List[OverheadCategory] = []
        self.debt_facilities: List[DebtFacility] = []
        
        # Results storage
        self.monthly_pl: pd.DataFrame = None
        self.monthly_bs: pd.DataFrame = None
        self.monthly_cf: pd.DataFrame = None
        self.annual_pl: pd.DataFrame = None
        self.annual_bs: pd.DataFrame = None
        self.annual_cf: pd.DataFrame = None
        self.stock_reconciliation: Dict[str, pd.DataFrame] = {}  # {program_name: reconciliation_df}
        self.monthly_gst: pd.DataFrame = None  # GST tracking by month
        
    def calculate(self):
        """Run the complete model calculation"""
        print("Starting farm model calculation...")
        
        # Get month dates
        month_dates = self.general.get_month_dates()
        num_months = len(month_dates)
        
        # Initialize result dataframes
        months = list(range(1, num_months + 1))
        
        # P&L components
        pl_data = {
            'month': months,
            'date': month_dates,
            # Income
            'crop_revenue': [0.0] * num_months,
            'beef_revenue': [0.0] * num_months,
            'sheep_revenue': [0.0] * num_months,
            'wool_revenue': [0.0] * num_months,
            'other_income': [0.0] * num_months,
            # Direct costs
            'crop_direct_costs': [0.0] * num_months,
            'beef_direct_costs': [0.0] * num_months,
            'sheep_direct_costs': [0.0] * num_months,
            'wool_direct_costs': [0.0] * num_months,
            'pasture_costs': [0.0] * num_months,
            # Overheads
            'overheads': [0.0] * num_months,
            # Other
            'depreciation': [0.0] * num_months,
            'interest_expense': [0.0] * num_months,
            'interest_income': [0.0] * num_months,
        }
        
        # Calculate enterprise revenues and costs
        self._calculate_crop_enterprise(pl_data)
        self._calculate_livestock_enterprises(pl_data)
        self._calculate_pasture_programs(pl_data)
        self._calculate_overheads(pl_data)
        self._calculate_depreciation(pl_data)
        self._calculate_debt_costs(pl_data)
        
        # Build P&L
        df_pl = pd.DataFrame(pl_data)
        
        # Total income
        df_pl['total_income'] = (df_pl['crop_revenue'] + df_pl['beef_revenue'] + 
                                  df_pl['sheep_revenue'] + df_pl['wool_revenue'] + 
                                  df_pl['other_income'])
        
        # Total direct costs
        df_pl['total_direct_costs'] = (df_pl['crop_direct_costs'] + df_pl['beef_direct_costs'] + 
                                        df_pl['sheep_direct_costs'] + df_pl['wool_direct_costs'] + 
                                        df_pl['pasture_costs'])
        
        # Gross profit
        df_pl['gross_profit'] = df_pl['total_income'] - df_pl['total_direct_costs']
        
        # EBITDA
        df_pl['ebitda'] = df_pl['gross_profit'] - df_pl['overheads']
        
        # EBIT
        df_pl['ebit'] = df_pl['ebitda'] - df_pl['depreciation']
        
        # EBT
        df_pl['ebt'] = df_pl['ebit'] - df_pl['interest_expense'] + df_pl['interest_income']
        
        # Tax accrual - calculate on cumulative taxable income each month
        df_pl['cumulative_taxable_income'] = df_pl['ebt'].cumsum()
        df_pl['tax_accrued'] = df_pl['cumulative_taxable_income'].apply(
            lambda x: max(0, x * self.general.income_tax_rate)
        )
        
        # Tax payment only in tax payment month (reduces cash)
        df_pl['tax_paid'] = 0.0
        tax_month = self.general.tax_payment_month
        if tax_month <= num_months:
            # Pay tax accrued to date
            tax_to_pay = df_pl.iloc[tax_month - 1]['tax_accrued']
            if tax_to_pay > 0:
                df_pl.loc[tax_month - 1, 'tax_paid'] = tax_to_pay
        
        # Tax expense for P&L is based on full year position
        # For monthly P&L, accrue progressively
        df_pl['tax_expense'] = df_pl['tax_accrued'] - df_pl['tax_accrued'].shift(1).fillna(0)
        
        # Net profit (after tax expense)
        df_pl['net_profit'] = df_pl['ebt'] - df_pl['tax_expense']
        
        self.monthly_pl = df_pl
        
        # Build cash flow
        self._calculate_cash_flow(df_pl)
        
        # Calculate interest income on positive cash (now that we know cash balances)
        self._calculate_interest_income(df_pl)
        
        # Calculate GST
        self._calculate_gst(df_pl)
        
        # Build balance sheet
        self._calculate_balance_sheet(df_pl)
        
        # Summarize to annual
        self._summarize_annual()
        
        print("Calculation complete.")
        return self.monthly_pl, self.monthly_bs, self.monthly_cf
    
    def _calculate_crop_enterprise(self, pl_data: Dict):
        """Calculate cropping revenues and costs"""
        num_months = len(pl_data['month'])
        
        for crop in self.crop_margins:
            # Revenue in sale month
            revenue = crop.calculate_revenue()
            if 1 <= crop.sale_month <= num_months:
                pl_data['crop_revenue'][crop.sale_month - 1] += revenue
            
            # Costs spread or in specific months (simplified - would need program details)
            total_cost = crop.area_ha * crop.direct_cost_per_ha
            # For now, spread evenly across year (would be more sophisticated with timing)
            monthly_cost = total_cost / 12
            for m in range(num_months):
                pl_data['crop_direct_costs'][m] += monthly_cost
    
    def _calculate_livestock_enterprises(self, pl_data: Dict):
        """Calculate livestock revenues and costs with stock reconciliation and wool"""
        num_months = len(pl_data['month'])
        
        for program in self.livestock_programs:
            # Calculate stock reconciliation
            stock_recon = program.calculate_stock_reconciliation(num_months)
            self.stock_reconciliation[program.program_name] = stock_recon
            
            # Find associated livestock class
            livestock_class = None
            for lc in self.livestock_classes:
                if lc.class_name == program.livestock_class:
                    livestock_class = lc
                    break
            
            for month in range(1, num_months + 1):
                # Sales revenue (meat)
                if month in program.sales_by_month:
                    head, price_per_kg, avg_weight = program.sales_by_month[month]
                    revenue = head * price_per_kg * avg_weight
                    if program.enterprise_type == 'beef':
                        pl_data['beef_revenue'][month - 1] += revenue
                    elif program.enterprise_type == 'sheep':
                        pl_data['sheep_revenue'][month - 1] += revenue
                
                # Purchase costs (goes to P&L as direct cost)
                if month in program.purchases_by_month:
                    head, price = program.purchases_by_month[month]
                    cost = head * price
                    if program.enterprise_type == 'beef':
                        pl_data['beef_direct_costs'][month - 1] += cost
                    elif program.enterprise_type == 'sheep':
                        pl_data['sheep_direct_costs'][month - 1] += cost
                
                # Direct costs (animal health, fodder, etc.)
                if month in program.direct_costs_by_month:
                    for category, amount in program.direct_costs_by_month[month].items():
                        if program.enterprise_type == 'beef':
                            pl_data['beef_direct_costs'][month - 1] += amount
                        elif program.enterprise_type == 'sheep':
                            pl_data['sheep_direct_costs'][month - 1] += amount
                
                # Wool production and sales (for sheep only)
                if program.enterprise_type == 'sheep' and livestock_class and livestock_class.produces_wool:
                    # Find wool production record for this program
                    wool_prod = None
                    for wp in self.wool_production:
                        if wp.program_name == program.program_name:
                            wool_prod = wp
                            break
                    
                    if wool_prod:
                        # Get sheep count for this month
                        month_recon = stock_recon[stock_recon['month'] == month]
                        if len(month_recon) > 0:
                            sheep_count = int(month_recon.iloc[0]['closing'])
                            
                            # Calculate wool production if shearing month
                            wool_prod.calculate_monthly_production(sheep_count, livestock_class, month)
                            
                            # Calculate wool revenue if sale month
                            wool_revenue = wool_prod.calculate_wool_revenue(month)
                            pl_data['wool_revenue'][month - 1] += wool_revenue
                            
                            # Calculate shearing costs
                            shearing_cost = wool_prod.calculate_shearing_costs(sheep_count, month, livestock_class)
                            pl_data['wool_direct_costs'][month - 1] += shearing_cost
    
    def _calculate_overheads(self, pl_data: Dict):
        """Calculate overhead costs"""
        num_months = len(pl_data['month'])
        
        for overhead in self.overheads:
            for month in range(1, num_months + 1):
                cost = overhead.get_monthly_cost(month)
                pl_data['overheads'][month - 1] += cost
    
    def _calculate_pasture_programs(self, pl_data: Dict):
        """Calculate pasture program costs"""
        num_months = len(pl_data['month'])
        
        for program in self.pasture_programs:
            for month in range(1, num_months + 1):
                cost = program.get_monthly_costs(month)
                pl_data['pasture_costs'][month - 1] += cost
    
    def _calculate_depreciation(self, pl_data: Dict):
        """Calculate depreciation from fixed assets"""
        num_months = len(pl_data['month'])
        
        for asset in self.fixed_assets:
            monthly_dep = asset.calculate_monthly_depreciation()
            for month in range(num_months):
                pl_data['depreciation'][month] += monthly_dep
    
    def _calculate_debt_costs(self, pl_data: Dict):
        """Calculate interest on debt and interest income on cash"""
        num_months = len(pl_data['month'])
        
        # Interest expense on debt
        for facility in self.debt_facilities:
            for month in range(1, num_months + 1):
                interest = facility.calculate_interest(month)
                pl_data['interest_expense'][month - 1] += interest
        
        # Interest income on positive cash balances
        # This is calculated after cash flow is built, so we'll add it there
    
    def _calculate_interest_income(self, df_pl: pd.DataFrame):
        """Calculate interest income on positive cash balances"""
        if self.monthly_cf is None:
            return
        
        num_months = len(df_pl)
        monthly_rate = self.general.cash_interest_rate / 12
        
        for month_idx in range(num_months):
            cash_balance = self.monthly_cf.iloc[month_idx]['closing_cash']
            if cash_balance > 0:
                interest_income = cash_balance * monthly_rate
                df_pl.loc[month_idx, 'interest_income'] += interest_income
    
    def _calculate_gst(self, df_pl: pd.DataFrame):
        """Calculate GST on revenues and expenses with payment timing"""
        num_months = len(df_pl)
        gst_rate = self.general.gst_rate
        
        gst_on_sales = []
        gst_on_purchases = []
        net_gst_list = []
        gst_payments = [0.0] * num_months
        
        for month_idx in range(num_months):
            # GST collected on sales
            total_revenue = (df_pl.iloc[month_idx]['crop_revenue'] +
                           df_pl.iloc[month_idx]['beef_revenue'] +
                           df_pl.iloc[month_idx]['sheep_revenue'] +
                           df_pl.iloc[month_idx]['wool_revenue'] +
                           df_pl.iloc[month_idx]['other_income'])
            gst_collected = total_revenue * gst_rate
            
            # GST paid on purchases
            total_expenses = (df_pl.iloc[month_idx]['crop_direct_costs'] +
                            df_pl.iloc[month_idx]['beef_direct_costs'] +
                            df_pl.iloc[month_idx]['sheep_direct_costs'] +
                            df_pl.iloc[month_idx]['wool_direct_costs'] +
                            df_pl.iloc[month_idx]['pasture_costs'] +
                            df_pl.iloc[month_idx]['overheads'])
            gst_paid = total_expenses * gst_rate
            
            # Net GST (positive = payable, negative = receivable)
            net_gst = gst_collected - gst_paid
            
            gst_on_sales.append(gst_collected)
            gst_on_purchases.append(gst_paid)
            net_gst_list.append(net_gst)
        
        gst_data = {
            'month': df_pl['month'].tolist(),
            'date': df_pl['date'].tolist(),
            'gst_on_sales': gst_on_sales,
            'gst_on_purchases': gst_on_purchases,
            'net_gst': net_gst_list,
            'gst_payment': gst_payments
        }
        
        df_gst = pd.DataFrame(gst_data)
        
        # Calculate GST payments based on reporting period
        payment_months = self.general.get_gst_payment_months()
        
        if self.general.gst_reporting_period == "quarterly":
            # Pay quarterly GST in payment months
            for payment_month in payment_months:
                if payment_month <= num_months:
                    # Calculate which quarter we're paying for
                    quarter_end = payment_month - self.general.gst_payment_delay
                    quarter_start = max(1, quarter_end - 2)
                    
                    # Sum GST for the quarter
                    quarter_gst = df_gst.loc[(df_gst['month'] >= quarter_start) & 
                                             (df_gst['month'] <= quarter_end), 'net_gst'].sum()
                    
                    if quarter_gst > 0:  # Only pay if positive (payable)
                        df_gst.loc[df_gst['month'] == payment_month, 'gst_payment'] = quarter_gst
        
        elif self.general.gst_reporting_period == "monthly":
            # Pay monthly GST
            for month in range(1, num_months + 1):
                payment_month = month + self.general.gst_payment_delay
                if payment_month <= num_months:
                    month_gst = df_gst.loc[df_gst['month'] == month, 'net_gst'].values[0]
                    if month_gst > 0:
                        df_gst.loc[df_gst['month'] == payment_month, 'gst_payment'] = month_gst
        
        elif self.general.gst_reporting_period == "annual":
            # Pay annual GST
            if payment_months:
                payment_month = payment_months[0]
                if payment_month <= num_months:
                    annual_gst = df_gst['net_gst'].sum()
                    if annual_gst > 0:
                        df_gst.loc[df_gst['month'] == payment_month, 'gst_payment'] = annual_gst
        
        # Calculate cumulative GST liability (unpaid)
        df_gst['cumulative_gst'] = self.opening_balances.gst_liability
        for idx in range(len(df_gst)):
            if idx > 0:
                df_gst.loc[idx, 'cumulative_gst'] = df_gst.loc[idx-1, 'cumulative_gst']
            df_gst.loc[idx, 'cumulative_gst'] += df_gst.loc[idx, 'net_gst'] - df_gst.loc[idx, 'gst_payment']
        
        self.monthly_gst = df_gst
    
    def _calculate_cash_flow(self, df_pl: pd.DataFrame):
        """Build cash flow statement with payment timing"""
        num_months = len(df_pl)
        
        # Initialize arrays for cash timing
        cash_receipts = [0.0] * num_months
        cash_payments = [0.0] * num_months
        
        # Apply payment timing to revenues (including GST on receipts)
        gst_rate = self.general.gst_rate
        for month in range(num_months):
            # Crop sales - delayed by crop_sales timing
            crop_rev_accrual = df_pl.iloc[month]['crop_revenue']
            crop_rev_incl_gst = crop_rev_accrual * (1 + gst_rate)  # Add GST
            cash_month = month + self.payment_timing.crop_sales
            if cash_month < num_months:
                cash_receipts[cash_month] += crop_rev_incl_gst
            
            # Beef sales - delayed by beef_sales timing  
            beef_rev_accrual = df_pl.iloc[month]['beef_revenue']
            beef_rev_incl_gst = beef_rev_accrual * (1 + gst_rate)
            cash_month = month + self.payment_timing.beef_sales
            if cash_month < num_months:
                cash_receipts[cash_month] += beef_rev_incl_gst
            
            # Sheep sales - delayed by sheep_sales timing
            sheep_rev_accrual = df_pl.iloc[month]['sheep_revenue']
            sheep_rev_incl_gst = sheep_rev_accrual * (1 + gst_rate)
            cash_month = month + self.payment_timing.sheep_sales
            if cash_month < num_months:
                cash_receipts[cash_month] += sheep_rev_incl_gst
            
            # Wool sales - delayed by wool_sales timing
            wool_rev_accrual = df_pl.iloc[month]['wool_revenue']
            wool_rev_incl_gst = wool_rev_accrual * (1 + gst_rate)
            cash_month = month + self.payment_timing.wool_sales
            if cash_month < num_months:
                cash_receipts[cash_month] += wool_rev_incl_gst
        
        # Apply payment timing to costs (including GST on payments)
        for month in range(num_months):
            # Direct costs - various timing
            crop_cost_accrual = df_pl.iloc[month]['crop_direct_costs']
            crop_cost_incl_gst = crop_cost_accrual * (1 + gst_rate)
            cash_month = month + self.payment_timing.crop_fertiliser  # Simplified
            if cash_month < num_months:
                cash_payments[cash_month] += crop_cost_incl_gst
            
            beef_cost_accrual = df_pl.iloc[month]['beef_direct_costs']
            beef_cost_incl_gst = beef_cost_accrual * (1 + gst_rate)
            cash_month = month + self.payment_timing.beef_animal_health  # Simplified
            if cash_month < num_months:
                cash_payments[cash_month] += beef_cost_incl_gst
            
            sheep_cost_accrual = df_pl.iloc[month]['sheep_direct_costs']
            sheep_cost_incl_gst = sheep_cost_accrual * (1 + gst_rate)
            cash_month = month + self.payment_timing.sheep_animal_health  # Simplified
            if cash_month < num_months:
                cash_payments[cash_month] += sheep_cost_incl_gst
            
            # Overheads - typically paid in month
            overhead_cost = df_pl.iloc[month]['overheads']
            overhead_cost_incl_gst = overhead_cost * (1 + gst_rate)
            cash_month = month + self.payment_timing.overhead_default
            if cash_month < num_months:
                cash_payments[cash_month] += overhead_cost_incl_gst
            
            # Pasture costs
            pasture_cost = df_pl.iloc[month]['pasture_costs']
            pasture_cost_incl_gst = pasture_cost * (1 + gst_rate)
            if cash_month < num_months:
                cash_payments[cash_month] += pasture_cost_incl_gst
            
            # Interest - paid in month
            interest_cost = df_pl.iloc[month]['interest_expense']
            if month < num_months:
                cash_payments[month] += interest_cost
        
        # Calculate working capital changes
        working_capital_change = [0.0] * num_months
        for month in range(num_months):
            # Debtors increase when revenue > receipts
            accrual_revenue = (df_pl.iloc[month]['crop_revenue'] + 
                              df_pl.iloc[month]['beef_revenue'] + 
                              df_pl.iloc[month]['sheep_revenue'] + 
                              df_pl.iloc[month]['wool_revenue'])
            debtor_change = accrual_revenue - cash_receipts[month]
            
            # Creditors increase when costs > payments
            accrual_costs = (df_pl.iloc[month]['crop_direct_costs'] + 
                            df_pl.iloc[month]['beef_direct_costs'] + 
                            df_pl.iloc[month]['sheep_direct_costs'] + 
                            df_pl.iloc[month]['overheads'])
            creditor_change = accrual_costs - cash_payments[month]
            
            # Net working capital change (increase in WC = cash outflow)
            working_capital_change[month] = debtor_change - creditor_change
        
        cf_data = {
            'month': df_pl['month'].tolist(),
            'date': df_pl['date'].tolist(),
            'net_profit': df_pl['net_profit'].tolist(),
            'depreciation': df_pl['depreciation'].tolist(),
            'working_capital_change': working_capital_change,
            'cash_receipts': cash_receipts,
            'cash_payments': cash_payments,
            'capex': [0.0] * num_months,
            'asset_sales': [0.0] * num_months,
            'debt_drawdowns': [0.0] * num_months,
            'debt_repayments': [0.0] * num_months,
            'equity_injection': [0.0] * num_months,
            'dividends': [0.0] * num_months,
        }
        
        # Add debt facility movements
        for facility in self.debt_facilities:
            for month in range(1, num_months + 1):
                if month in facility.drawdown_schedule:
                    cf_data['debt_drawdowns'][month - 1] += facility.drawdown_schedule[month]
                if month in facility.repayment_schedule:
                    cf_data['debt_repayments'][month - 1] += facility.repayment_schedule[month]
        
        # Add GST payments (reduce cash when paying to ATO)
        if self.monthly_gst is not None:
            for month_idx in range(num_months):
                gst_payment = self.monthly_gst.iloc[month_idx]['gst_payment']
                if gst_payment > 0:
                    cash_payments[month_idx] += gst_payment
        
        # Add tax payments (only when actually paid, not when accrued)
        for month_idx in range(num_months):
            tax_payment = df_pl.iloc[month_idx]['tax_paid']
            if tax_payment > 0:
                cash_payments[month_idx] += tax_payment
        
        # Process planned CAPEX
        for capex in self.planned_capex:
            if 1 <= capex.purchase_month <= num_months:
                cf_data['capex'][capex.purchase_month - 1] += capex.purchase_amount
                
                # Add to fixed assets after purchase
                new_asset = capex.to_fixed_asset(self.general.start_date)
                self.fixed_assets.append(new_asset)
        
        # Process planned disposals
        for disposal in self.planned_disposals:
            if 1 <= disposal.disposal_month <= num_months:
                # Find the asset
                for asset in self.fixed_assets:
                    if asset.asset_name == disposal.asset_name:
                        # Calculate months from purchase to disposal
                        months_held = (disposal.disposal_month - 1)
                        wdv = asset.calculate_written_down_value(months_held)
                        
                        # Record sale proceeds
                        cf_data['asset_sales'][disposal.disposal_month - 1] += (disposal.sale_price - disposal.disposal_costs)
                        
                        # Profit on sale goes to P&L (would need to add this to pl_data)
                        profit_on_sale = disposal.calculate_profit_on_sale(wdv)
                        # TODO: Add to other_income in P&L
                        break
        
        # Operating cash flow
        df_cf = pd.DataFrame(cf_data)
        
        # Add back non-cash expenses (depreciation and unpaid tax)
        df_cf['tax_unpaid'] = df_pl['tax_expense'] - df_pl['tax_paid']
        df_cf['operating_cf'] = (df_cf['net_profit'] + df_cf['depreciation'] + 
                                  df_cf['tax_unpaid'] - df_cf['working_capital_change'])
        
        # Investing cash flow
        df_cf['investing_cf'] = df_cf['asset_sales'] - df_cf['capex']
        
        # Financing cash flow
        df_cf['financing_cf'] = (df_cf['debt_drawdowns'] - df_cf['debt_repayments'] + 
                                  df_cf['equity_injection'] - df_cf['dividends'])
        
        # Net cash flow
        df_cf['net_cash_flow'] = df_cf['operating_cf'] + df_cf['investing_cf'] + df_cf['financing_cf']
        
        # Cumulative cash
        df_cf['closing_cash'] = self.opening_balances.cash + df_cf['net_cash_flow'].cumsum()
        
        self.monthly_cf = df_cf
    
    def _calculate_balance_sheet(self, df_pl: pd.DataFrame):
        """Build balance sheet with working capital tracking"""
        num_months = len(df_pl)
        
        bs_data = {
            'month': df_pl['month'].tolist(),
            'date': df_pl['date'].tolist(),
            # Assets
            'cash': [self.opening_balances.cash] * num_months,
            'trade_debtors': [self.opening_balances.trade_debtors] * num_months,
            'inventory': [self.opening_balances.inventory_grain + 
                          self.opening_balances.inventory_wool + 
                          self.opening_balances.inventory_livestock] * num_months,
            'fixed_assets': [self.opening_balances.fixed_assets] * num_months,
            'land_water': [self.opening_balances.land_water] * num_months,
            # Liabilities
            'trade_creditors': [self.opening_balances.trade_creditors] * num_months,
            'debt': [self.opening_balances.debt_facilities] * num_months,
            'tax_payable': [self.opening_balances.tax_payable] * num_months,
            # Equity
            'share_capital': [self.opening_balances.share_capital] * num_months,
            'retained_earnings': [self.opening_balances.retained_earnings] * num_months,
        }
        
        df_bs = pd.DataFrame(bs_data)
        
        # Update cash from cash flow
        if self.monthly_cf is not None:
            df_bs['cash'] = self.monthly_cf['closing_cash']
            
            # Update working capital accounts
            cumulative_wc_change = self.monthly_cf['working_capital_change'].cumsum()
            
            # Debtors increase with timing delays on revenue
            df_bs['trade_debtors'] = self.opening_balances.trade_debtors + cumulative_wc_change
            
            # Add GST component to debtors
            # GST collected but not yet received in cash is part of debtors
            if self.monthly_gst is not None:
                # GST on sales that haven't been received yet
                cumulative_gst_on_sales = self.monthly_gst['gst_on_sales'].cumsum()
                cumulative_gst_collected_cash = (self.monthly_gst['gst_on_sales'].shift(1).fillna(0) * 
                                                (1 if self.payment_timing.crop_sales == 0 else 0)).cumsum()
                
                # Simpler approach: cumulative GST owing less cumulative GST paid
                # This is the GST component sitting in our working capital
                cumulative_gst_liability = self.monthly_gst['cumulative_gst']
                
                # Add the GST liability to debtors (it's money customers owe us that we'll pass to ATO)
                df_bs['trade_debtors'] = df_bs['trade_debtors'] + cumulative_gst_liability
            
            # Creditors stay at opening level (simplified)
            df_bs['trade_creditors'] = self.opening_balances.trade_creditors
        
        # Update tax payable (accrued less paid)
        df_bs['tax_payable'] = self.opening_balances.tax_payable + df_pl['tax_accrued'] - df_pl['tax_paid'].cumsum()
        
        # Update fixed assets with accumulated depreciation and CAPEX
        cumulative_depreciation = df_pl['depreciation'].cumsum()
        cumulative_capex = 0
        if self.monthly_cf is not None:
            cumulative_capex = self.monthly_cf['capex'].cumsum()
        
        df_bs['fixed_assets'] = (self.opening_balances.fixed_assets + 
                                  cumulative_capex - 
                                  cumulative_depreciation)
        
        # Update debt from facility movements
        if len(self.debt_facilities) > 0:
            for month_idx in range(num_months):
                month = month_idx + 1
                total_debt = self.opening_balances.debt_facilities
                for facility in self.debt_facilities:
                    total_debt += sum(facility.drawdown_schedule.get(m, 0) for m in range(1, month + 1))
                    total_debt -= sum(facility.repayment_schedule.get(m, 0) for m in range(1, month + 1))
                df_bs.loc[month_idx, 'debt'] = total_debt
        
        # Update GST liability from monthly GST calculations
        if self.monthly_gst is not None:
            df_bs['gst_payable'] = self.monthly_gst['cumulative_gst']
        else:
            df_bs['gst_payable'] = self.opening_balances.gst_liability
        
        # Update retained earnings with cumulative profit
        df_bs['retained_earnings'] = (self.opening_balances.retained_earnings + 
                                       df_pl['net_profit'].cumsum())
        
        # Totals
        df_bs['total_assets'] = (df_bs['cash'] + df_bs['trade_debtors'] + 
                                  df_bs['inventory'] + df_bs['fixed_assets'] + 
                                  df_bs['land_water'])
        
        # Add GST receivable to assets (when negative/receivable)
        df_bs['gst_receivable'] = df_bs['gst_payable'].apply(lambda x: abs(x) if x < 0 else 0)
        df_bs['total_assets'] = df_bs['total_assets'] + df_bs['gst_receivable']
        
        # Only include GST in liabilities when payable (positive)
        df_bs['gst_liability'] = df_bs['gst_payable'].apply(lambda x: x if x > 0 else 0)
        
        df_bs['total_liabilities'] = (df_bs['trade_creditors'] + df_bs['debt'] + 
                                       df_bs['tax_payable'] + df_bs['gst_liability'])
        
        df_bs['total_equity'] = df_bs['share_capital'] + df_bs['retained_earnings']
        
        # Check balance
        df_bs['balance_check'] = df_bs['total_assets'] - (df_bs['total_liabilities'] + df_bs['total_equity'])
        
        self.monthly_bs = df_bs
    
    def _summarize_annual(self):
        """Summarize monthly data to annual"""
        if self.monthly_pl is None:
            return
        
        # Add financial year column
        self.monthly_pl['fy'] = self.monthly_pl['date'].apply(self.general.get_financial_year)
        
        # Group by financial year and sum
        annual_pl = self.monthly_pl.groupby('fy').agg({
            'total_income': 'sum',
            'total_direct_costs': 'sum',
            'gross_profit': 'sum',
            'overheads': 'sum',
            'ebitda': 'sum',
            'depreciation': 'sum',
            'ebit': 'sum',
            'interest_expense': 'sum',
            'interest_income': 'sum',
            'ebt': 'sum',
            'tax_expense': 'sum',
            'net_profit': 'sum',
        }).reset_index()
        
        self.annual_pl = annual_pl
        
        # Annual balance sheet (year-end snapshot)
        annual_bs = self.monthly_bs.groupby(
            self.monthly_bs['date'].apply(self.general.get_financial_year)
        ).last().reset_index(drop=True)
        annual_bs['fy'] = self.annual_pl['fy']
        
        self.annual_bs = annual_bs
        
        # Annual cash flow
        if self.monthly_cf is not None:
            self.monthly_cf['fy'] = self.monthly_cf['date'].apply(self.general.get_financial_year)
            annual_cf = self.monthly_cf.groupby('fy').agg({
                'operating_cf': 'sum',
                'investing_cf': 'sum',
                'financing_cf': 'sum',
                'net_cash_flow': 'sum',
            }).reset_index()
            annual_cf['closing_cash'] = self.monthly_cf.groupby('fy')['closing_cash'].last().values
            self.annual_cf = annual_cf
    
    def get_kpis(self) -> Dict:
        """Calculate and return key KPIs"""
        if self.annual_pl is None or self.annual_bs is None:
            return {}
        
        latest_year = self.annual_pl.iloc[-1]
        latest_bs = self.annual_bs.iloc[-1]
        
        return {
            'ebitda': latest_year['ebitda'],
            'net_profit': latest_year['net_profit'],
            'closing_cash': latest_bs['cash'],
            'total_debt': latest_bs['debt'],
            'net_assets': latest_bs['total_equity'],
            'roa': (latest_year['ebit'] / latest_bs['total_assets'] * 100) if latest_bs['total_assets'] > 0 else 0,
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Create model instance
    model = FarmModel()
    
    # Set up basic assumptions
    model.general.farm_name = "Example Farm"
    model.general.start_date = datetime(2026, 7, 1)
    model.general.num_months = 12
    
    # Set opening balances
    model.opening_balances.cash = 50000
    model.opening_balances.fixed_assets = 500000
    model.opening_balances.land_water = 2000000
    model.opening_balances.share_capital = 2000000
    model.opening_balances.retained_earnings = 550000
    
    # Add a simple crop
    crop = CropMargin(
        crop_name="Wheat",
        area_ha=100,
        yield_per_ha=3.5,  # tonnes
        price_per_unit=350,  # $ per tonne
        revenue_deductions_pct=0.05,
        harvest_month=11,
        sale_month=12,
        direct_cost_per_ha=400
    )
    model.crop_margins.append(crop)
    
    # Add overhead
    overhead = OverheadCategory(
        category_name="Wages",
        allocation_method="straight_line",
        monthly_amount=8000
    )
    model.overheads.append(overhead)
    
    # Calculate
    monthly_pl, monthly_bs, monthly_cf = model.calculate()
    
    # Display results
    print("\n" + "="*80)
    print("MONTHLY P&L SUMMARY")
    print("="*80)
    print(monthly_pl[['month', 'total_income', 'gross_profit', 'ebitda', 'net_profit']])
    
    print("\n" + "="*80)
    print("ANNUAL SUMMARY")
    print("="*80)
    if model.annual_pl is not None:
        print(model.annual_pl)
    
    print("\n" + "="*80)
    print("KEY KPIs")
    print("="*80)
    kpis = model.get_kpis()
    for key, value in kpis.items():
        print(f"{key}: ${value:,.2f}" if 'roa' not in key else f"{key}: {value:.2f}%")
