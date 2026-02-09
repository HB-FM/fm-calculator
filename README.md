# FarmMate - Farm Budgeting Platform (MVP)

**Converted from Excel to Python + Streamlit Web App**

## 🎯 What This Is

This is the MVP (Minimum Viable Product) conversion of your comprehensive Excel farm budgeting model into a cloud-based web application. It provides:

- ✅ Clean web interface (no more Excel spreadsheets to manage)
- ✅ Locked calculation engine (users can't break the formulas)
- ✅ Multi-scenario support
- ✅ Real-time calculations
- ✅ Professional charts and dashboards
- ✅ Export capabilities

## 📁 Files Included

1. **farmmate_input_schema.md** - Complete documentation of all inputs from your Excel model
2. **farmmate_engine.py** - Python calculation engine (converts Excel formulas to Python)
3. **farmmate_app.py** - Streamlit web application (the user interface)
4. **requirements.txt** - Python package dependencies
5. **README.md** - This file

## 🚀 Quick Start (Local Testing)

### Prerequisites
- Python 3.9 or higher installed
- Basic command line knowledge

### Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the app:**
```bash
streamlit run farmmate_app.py
```

3. **Open your browser:**
The app will automatically open at `http://localhost:8501`

## 🌐 Deployment Options

### Option 1: Streamlit Cloud (Easiest - Free)

1. **Create a GitHub repository**
   - Upload all files to a new GitHub repo
   - Make it private if needed

2. **Deploy to Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Sign in with GitHub
   - Click "New app"
   - Select your repository
   - Click "Deploy"

**Done! Your app will be live at: `yourapp.streamlit.app`**

**Pros:**
- Completely free
- Automatic updates when you push to GitHub
- HTTPS enabled
- Easy sharing

**Cons:**
- Public URL (anyone with link can access)
- Limited to community tier resources
- Streamlit branding

### Option 2: Heroku (More Control)

1. **Install Heroku CLI**
2. **Create these additional files:**

`Procfile`:
```
web: sh setup.sh && streamlit run farmmate_app.py
```

`setup.sh`:
```bash
mkdir -p ~/.streamlit/
echo "[server]
headless = true
port = $PORT
enableCORS = false
" > ~/.streamlit/config.toml
```

3. **Deploy:**
```bash
heroku create your-farmmate-app
git push heroku main
```

**Pros:**
- More control over configuration
- Can use custom domain
- Better for scaling

**Cons:**
- Costs $7/month after free tier
- More setup complexity

### Option 3: AWS/Azure/Google Cloud (Enterprise)

For production use with Growth Farms or FarmMate business:
- EC2 (AWS) or App Service (Azure) or Cloud Run (GCP)
- Set up with proper authentication
- Database backend for multi-user support
- Professional domain

## 💡 Current Functionality (MVP)

### ✅ Working Features

**Setup:**
- Farm details and general assumptions
- Inflation rates by category
- Opening balance sheet
- Tax and interest rates

**Cropping:**
- Add/manage crop budgets
- Revenue calculations
- Gross margin analysis
- Yield and price inputs

**Financials:**
- Overhead cost categories
- Monthly or one-off allocations
- Overhead summaries

**Reporting:**
- Dashboard with KPIs
- Annual P&L, Balance Sheet, Cash Flow
- Monthly detail
- Charts and graphs

**Calculation Engine:**
- 3-way integrated financial statements
- Monthly and annual summaries
- Balance sheet balancing
- Tax calculations

### 🚧 Not Yet Implemented (Next Phase)

The following tabs from your Excel model need additional work:

**Land & Infrastructure:**
- Paddock management (1.20)
- Rotation planning (1.21)
- Fixed Asset Register (1.30)
- CAPEX planning (1.31)
- Asset disposals (1.32)

**Cropping Detail:**
- Crop programs/input schedules (2.2)
- Crop input library (2.1)

**Livestock:**
- Beef programs and margins (3.10-3.13)
- Sheep programs and margins (3.20-3.23)
- Wool production (3.52)
- Stock flow reconciliation

**Pasture:**
- Maintenance programs (3.60)
- Establishment programs (3.61)
- Fodder crops (3.62)

**Advanced:**
- Debt facilities and scheduling (6.2)
- Land and water assets (6.1)
- Other income/expenses (5)

## 🔧 How to Add Missing Functionality

The calculation engine (`farmmate_engine.py`) is designed to be extended. To add new features:

1. **Add data structures** - Create new dataclasses for the input type
2. **Add calculation methods** - Write methods to calculate results
3. **Update UI** - Add forms in `farmmate_app.py` to capture inputs
4. **Test** - Compare outputs against your Excel model

Example: Adding paddock management
```python
# In farmmate_engine.py
@dataclass
class Paddock:
    name: str
    size_ha: float
    property_name: str

# In farmmate_app.py
# Add form to capture paddock details
# Store in st.session_state.model.paddocks
```

## 🐛 Known Limitations & Debugging

### Current Limitations:

1. **Simplified livestock** - Stock flow reconciliation not yet implemented
2. **No payment timing** - Timing delays for receipts/payments not applied yet
3. **Basic depreciation** - Uses opening balance, doesn't calculate monthly depreciation
4. **No scenarios** - Can only work with one budget at a time (save/load not implemented)
5. **No commodity price feeds** - All prices are manual inputs

### Debugging Calculation Differences:

If you find differences between Excel and Python outputs:

1. **Check inputs** - Verify all inputs match exactly
2. **Compare step-by-step** - Look at intermediate calculations:
   ```python
   # In Python
   print(model.monthly_pl[['month', 'total_income', 'ebitda', 'net_profit']])
   ```
3. **Report the issue** - Let me know which specific calculation is wrong
4. **I can fix it** - I'll trace through the formulas and correct the Python code

## 📊 Input Mapping Reference

See **farmmate_input_schema.md** for complete documentation of:
- Every input field from your Excel model
- What tab it's in
- What it's used for
- Priority for implementation

## 🔐 Access Control (For Growth Farms)

To prevent portfolio managers from modifying the model:

1. **Authentication** - Add password protection
2. **User roles** - Admin (you) vs User (portfolio managers)
3. **Read-only mode** - Users can only input data, not see/modify calculations

Simple example:
```python
# Add to farmmate_app.py
import streamlit as st

def check_password():
    def password_entered():
        if st.session_state["password"] == "your_secure_password":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()
```

## 🎯 Next Steps

### For Growth Farms (Immediate):
1. Deploy to Streamlit Cloud
2. Test with a real farm scenario
3. Compare outputs against Excel
4. Iterate on any calculation errors
5. Add missing functionality based on priority

### For FarmMate (Product):
1. Add remaining functionality (paddocks, livestock, etc.)
2. Build proper database backend
3. Multi-user support with authentication
4. Scenario management
5. Real-time commodity price feeds
6. Weather data integration
7. PDF report generation
8. API for integrations (Xero, etc.)
9. Mobile app for field data entry

## 💰 Cost Estimate

**MVP (Current Solution):**
- Streamlit Cloud: Free
- Development time: ~15 hours (partially complete)
- Total: $0

**Full FarmMate Product:**
- Development: 3-6 months
- Hosting (AWS/Azure): $50-200/month
- Database: Included in hosting
- Domain: $15/year
- Total Year 1: ~$1,000-3,000

## 📞 Support

If you encounter issues or need modifications:

1. **Calculation errors** - Provide specific example and I can debug
2. **New features** - Let me know priority and I can implement
3. **Deployment help** - Can guide through setup process

## 📝 Licence

This is your proprietary model. The code conversion is yours to use for Growth Farms and eventually FarmMate.

---

**Built with:**
- Python 3.9+
- Streamlit (web framework)
- Pandas (data handling)
- Plotly (charts)
- OpenPyXL (Excel reading)

**Version:** 0.1 MVP (February 2026)
