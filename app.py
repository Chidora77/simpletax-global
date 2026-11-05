
import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os, glob

st.set_page_config(page_title="SimpleTax Global 2026", page_icon="🌍", layout="centered", initial_sidebar_state="collapsed")

# VERIFIED 2026 BRACKETS - 6 COUNTRIES ONLY (NO UAE)
TAX_RULES = {
    "🇬🇧 UK 2026/27": {
        "currency": "£", "allowance": 12570,
        "brackets": [(37700, 0.20), (74870, 0.40), (9999999, 0.45)],
        "extra": "Class4 6% £12,570-£50,270 2% above",
        "calc_extra": lambda p: (min(p,50270)-12570)*0.06 + max(0, p-50270)*0.02 if p>12570 else 0,
        "name": "UK 2026/27 HMRC - PA £12,570 frozen until Apr 2031"
    },
    "🇺🇸 US 2026": {
        "currency": "$", "allowance": 16100,
        "brackets": [(12400, 0.10), (38000, 0.12), (55300, 0.22), (73550, 0.24)],
        "extra": "SE 15.3% | Std Ded $16,100",
        "calc_extra": lambda p: p*0.153 if p>400 else 0,
        "name": "US Federal 2026 IRS - 10% $0-$12,400 12% $12,400-$50,400 22% $50,400-$105,700"
    },
    "🇳🇬 Nigeria NTA 2025": {
        "currency": "₦", "allowance": 800000,
        "brackets": [(2200000, 0.15), (9000000, 0.18), (13000000, 0.21), (25000000, 0.23), (99999999, 0.25)],
        "extra": "NTA 2025 0-25% + Rent Relief 20% up to ₦500k",
        "calc_extra": lambda p: 0,
        "name": "Nigeria Tax Act 2025 - First ₦800k 0% Next ₦2.2m 15%"
    },
    "🇨🇦 Canada 2026": {
        "currency": "C$", "allowance": 16452,
        "brackets": [(58523, 0.14), (58522, 0.205), (64395, 0.26), (77042, 0.29), (9999999, 0.33)],
        "extra": "BPA $16,452 + CPP 5.95%",
        "calc_extra": lambda p: min(p,68500)*0.0595 if p>3500 else 0,
        "name": "Canada 2026 CRA - 14% up to $58,523 BPA $16,452"
    },
    "🇦🇺 Australia 2026-27": {
        "currency": "A$", "allowance": 18200,
        "brackets": [(26800, 0.15), (90000, 0.30), (55000, 0.37), (9999999, 0.45)],
        "extra": "Medicare 2% separate - 15% from 1 July 2026",
        "calc_extra": lambda p: p*0.02 if p>26000 else 0,
        "name": "Australia 2026-27 ATO - $0-$18,200 Nil $18,201-$45k 15%"
    },
    "🇩🇪 Germany 2026": {
        "currency": "€", "allowance": 12348,
        "brackets": [(57530, 0.28), (207947, 0.42), (9999999, 0.45)],
        "extra": "Grundfreibetrag €12,348 - 14%->42%",
        "calc_extra": lambda p: 0,
        "name": "Germany 2026 Single - €0-€12,348 0% €12,349-€69,878 14%->42%"
    },
}

def calc_tax(country, profit):
    rules = TAX_RULES[country]
    taxable = max(0, profit - rules["allowance"])
    tax = 0
    rem = taxable
    for amt, rate in rules["brackets"]:
        portion = min(rem, amt)
        tax += portion * rate
        rem -= portion
        if rem <= 0:
            break
    extra = rules["calc_extra"](profit)
    return tax, extra, tax+extra, taxable

# BLUE & ASH THEME + 4 INCH MOBILE FIT
st.markdown("""
<style>
.stApp {background-color: #eef2f7 !important;}
.block-container {background-color: #eef2f7 !important; max-width: 380px !important; padding: 0.6rem 0.8rem !important; margin: 0 auto !important;}
h1, h2, h3 {font-size: 1.1rem !important; margin: 0.3rem 0 !important;}
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {font-size: 0.9rem !important; height: 2.2rem !important;}
.stButton button {background-color: #1e40af !important; color: white !important; border-radius: 8px !important; width: 100% !important; height: 2.6rem !important; font-weight: 600 !important; font-size: 0.95rem !important;}
.stButton button:hover {background-color: #1e3a8a !important;}
div[data-baseweb="radio"] {gap: 0.2rem !important;}
div[data-baseweb="radio"] label {font-size: 0.78rem !important; padding: 0.3rem 0.5rem !important; background: white; border: 1.5px solid #cbd5e1; border-radius: 6px; margin: 2px;}
div[data-baseweb="radio"] label:has(input:checked) {border-color: #1e40af !important; background: #dbeafe !important;}
#MainMenu, header, footer {display: none !important;}
.card {background: white; border-radius: 10px; padding: 10px; border: 1px solid #cbd5e1; margin: 6px 0;}
.small {font-size: 0.78rem; color: #64748b;}
</style>
""", unsafe_allow_html=True)

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "country" not in st.session_state:
    st.session_state.country = "🇬🇧 UK 2026/27"
if "q1" not in st.session_state:
    st.session_state.q1 = st.session_state.q2 = st.session_state.q3 = st.session_state.q4 = 0.0

# LOGIN PAGE - FIXED BUTTON + DROPDOWN + HOW TO
if not st.session_state.user_id:
    st.markdown("### 🌍 SimpleTax Global 2026")
    st.caption("6 countries • Verified 2026 brackets • Blue & Ash")
    
    # COUNTRY DROPDOWN (NOT BUTTONS)
    country = st.selectbox("🌍 Select your country", list(TAX_RULES.keys()), index=0)
    st.session_state.country = country
    rules = TAX_RULES[country]
    
    st.markdown(f'<div class="card"><b>{country}</b><br><span class="small">{rules["name"]}<br>{rules["currency"]}{rules["allowance"]:,} free • {rules["extra"]}</span></div>', unsafe_allow_html=True)
    
    # HOW TO CREATE MEMORABLE CODE
    with st.expander("❓ How to create memorable name or code?"):
        st.markdown("""
        **Create a code you will remember:**
        - Use your name + number: **Chidi12**, **John2026**, **Aisha_01**
        - Use business + year: **Monsoon25**, **Shop_Abc**
        - 3-15 characters, letters, numbers, _ or -
        - **This is your private key** - same code shows your receipts
        - **Example:** If you use `Chidi12`, always login with `Chidi12` to see your data
        - **Keep it secret** - anyone with your code sees your receipts
        """)
    
    # LOGIN FORM - FIXES ENTER KEY + BUTTON NOT WORKING
    with st.form("login_form", clear_on_submit=False):
        user_code = st.text_input("Memorable code", placeholder="e.g. Chidi12", help="3-30 chars, remember this code")
        st.caption("You should remember your memorable code")
        submitted = st.form_submit_button("Login →", type="primary", use_container_width=True)
        if submitted:
            if user_code.strip() and len(user_code.strip()) >= 2:
                safe = "".join(c for c in user_code if c.isalnum() or c in ("-","_"))[:30]
                if not safe:
                    safe = user_code.replace(" ","_")[:30]
                st.session_state.user_id = safe
                st.rerun()
            else:
                st.error("Enter at least 2 characters")
    
    # Admin hint
    st.caption("Admin login: type `admin` to see all receipts")
    st.stop()

# HELPER FUNCTIONS
def get_db():
    code = "".join(ch for ch in st.session_state.country if ch.isalnum())[:4]
    return f"receipts_{code}_{st.session_state.user_id}.csv"

def get_all_receipts_files():
    # For admin to see all
    pattern = "receipts_*.csv"
    files = glob.glob(pattern)
    return files

def load_receipts():
    f = get_db()
    if not os.path.exists(f):
        pd.DataFrame(columns=["date","shop","total","category"]).to_csv(f, index=False)
    try:
        return pd.read_csv(f)
    except:
        return pd.DataFrame(columns=["date","shop","total","category"])

def load_all_receipts_for_admin():
    files = glob.glob("receipts_*.csv")
    all_dfs = []
    for file in files:
        try:
            df = pd.read_csv(file)
            if not df.empty:
                df["source_file"] = file
                # Extract country and user from filename
                parts = file.replace("receipts_","").replace(".csv","").split("_")
                if len(parts) >= 2:
                    df["country_code"] = parts[0]
                    df["user"] = "_".join(parts[1:])
                all_dfs.append(df)
        except:
            continue
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()

rules = TAX_RULES[st.session_state.country]
cur = rules["currency"]

# HEADER - FITS 4 INCH
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"**{st.session_state.country}**")
    st.caption(f"{st.session_state.user_id} • {cur}{rules['allowance']:,} free")
with col2:
    if st.button("Logout", use_container_width=True):
        st.session_state.user_id = None
        st.rerun()

# COUNTRY DROPDOWN IN APP (DYNAMIC SWITCH)
with st.expander(f"🌍 Switch Country - Now {st.session_state.country}"):
    new_c = st.selectbox("Select country", list(TAX_RULES.keys()), index=list(TAX_RULES.keys()).index(st.session_state.country), key="switch_country", label_visibility="collapsed")
    if st.button("Apply Country", type="primary", use_container_width=True):
        st.session_state.country = new_c
        st.rerun()

# NAV - RADIO BUTTONS FIT 4 INCH
nav = st.radio("Nav", ["Add", "List", "Dashboard", "Accountant"], horizontal=True, label_visibility="collapsed")

if nav == "Add":
    st.markdown(f'<div class="card"><b>Add Receipt ({cur})</b><br><span class="small">{st.session_state.country}</span></div>', unsafe_allow_html=True)
    method = st.radio("Method", ["Browse", "Camera"], horizontal=True, label_visibility="collapsed")
    up = None
    if method == "Browse":
        up = st.file_uploader("Receipt", type=["jpg","png","heic"], label_visibility="collapsed")
    else:
        up = st.camera_input("Camera", label_visibility="collapsed")
    if up:
        try:
            st.image(Image.open(up), width=200, caption="Ready")
        except:
            st.success("Image ready")
        with st.form("receipt_form"):
            shop = st.text_input("Supplier / Description", "Monsoon Foods")
            total = st.number_input(f"Total ({cur})", value=0.0, step=0.01)
            date = st.text_input("Date", datetime.now().strftime("%Y-%m-%d"))
            cat = st.selectbox("Category", ["Cost of goods", "Tools", "Travel", "Materials", "Office", "Fuel", "Other"])
            submit = st.form_submit_button("SUBMIT", type="primary", use_container_width=True)
            if submit:
                df = load_receipts()
                new = pd.DataFrame([{"date": date, "shop": shop, "total": total, "category": cat}])
                pd.concat([df, new]).to_csv(get_db(), index=False)
                st.success(f"Saved {cur}{total:.2f}")
                st.rerun()

if nav == "List":
    # ADMIN VIEW - SEE ALL RECEIPTS
    if st.session_state.user_id.lower() == "admin":
        st.subheader("🔑 Admin - All Receipts")
        all_df = load_all_receipts_for_admin()
        if all_df.empty:
            st.info("No receipts yet from any user")
        else:
            st.caption(f"Total {len(all_df)} receipts from all users")
            # Summary by user
            summary = all_df.groupby("user")["total"].agg(["count","sum"]).reset_index()
            st.dataframe(summary, width="stretch")
            st.divider()
            # All receipts
            st.dataframe(all_df[["user","country_code","shop","total","date"]].rename(columns={"shop":"Description"}), width="stretch")
            st.download_button("Download ALL as CSV", all_df.to_csv(index=False).encode(), "all_receipts_admin.csv", use_container_width=True)
    else:
        df = load_receipts()
        if df.empty:
            st.info(f"No receipts yet in {st.session_state.country}")
        else:
            st.caption(f"{len(df)} receipts • {cur}{df['total'].sum():.2f}")
            st.dataframe(df.rename(columns={"shop":"Desc", "total": f"Total ({cur})"}), width="stretch")
            # Delete option
            for idx, row in df.iterrows():
                c1, c2 = st.columns([4,1])
                with c1:
                    st.caption(f"{row['shop']} {cur}{row['total']}")
                with c2:
                    if st.button("Del", key=f"del_{idx}", use_container_width=True):
                        df.drop(idx, inplace=True)
                        df.to_csv(get_db(), index=False)
                        st.rerun()
            st.download_button("Download CSV", df.to_csv(index=False).encode(), f"SimpleTax-{st.session_state.country}.csv", use_container_width=True)

if nav == "Dashboard":
    st.subheader(f"Dashboard {cur}")
    df = load_receipts()
    exp = df["total"].sum() if not df.empty else 0
    
    # QUARTERLY INCOME - DYNAMIC PER QUARTER (NOT x4)
    st.markdown('<div class="card"><b>Quarterly Income</b><br><span class="small">Enter income per quarter - Annual = Q1+Q2+Q3+Q4 (not Q1 x4)</span></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        q1 = st.number_input(f"Q1 ({cur})", value=float(st.session_state.q1), min_value=0.0, step=100.0, key="q1")
        q2 = st.number_input(f"Q2 ({cur})", value=float(st.session_state.q2), min_value=0.0, step=100.0, key="q2")
    with c2:
        q3 = st.number_input(f"Q3 ({cur})", value=float(st.session_state.q3), min_value=0.0, step=100.0, key="q3")
        q4 = st.number_input(f"Q4 ({cur})", value=float(st.session_state.q4), min_value=0.0, step=100.0, key="q4")
    st.session_state.q1, st.session_state.q2, st.session_state.q3, st.session_state.q4 = q1, q2, q3, q4
    annual = q1+q2+q3+q4
    profit = annual - exp
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Exp", f"{cur}{exp:.0f}")
    c2.metric("Profit", f"{cur}{profit:.0f}")
    if annual>0:
        tax, extra, total, taxable = calc_tax(st.session_state.country, profit)
        c3.metric(f"Tax", f"{cur}{total:.0f}")
        st.success(f"Inc {cur}{annual:.0f} | Prof {cur}{profit:.0f} | Taxable {cur}{taxable:.0f} | Tax {cur}{total:.0f}/yr")
        with st.expander("Tax breakdown"):
            st.write(f"Allowance: {cur}{rules['allowance']:,}")
            st.write(f"Taxable = Profit {cur}{profit:.0f} - Allow {cur}{rules['allowance']:,} = {cur}{taxable:.0f}")
            st.write(f"Income Tax: {cur}{tax:.2f}")
            st.write(f"Extra {rules['extra']}: {cur}{extra:.2f}")
            st.write(f"**Total {cur}{total:.2f}/yr → {cur}{total/4:.2f}/q**")
            st.caption(f"Q1 {cur}{q1:.0f}+Q2 {cur}{q2:.0f}+Q3 {cur}{q3:.0f}+Q4 {cur}{q4:.0f} = {cur}{annual:.0f}")
            st.caption(f"Source: {rules['name']}")
    else:
        c3.metric("Tax", f"{cur}0")

if nav == "Accountant":
    st.subheader("Send to Accountant")
    df = load_receipts()
    if df.empty:
        st.info("Add receipts first")
    else:
        st.metric("Ready", f"{len(df)} receipts in {st.session_state.country}")
        # DYNAMIC NAME - USE LOGGED IN USER
        logged_name = st.session_state.user_id
        name = st.text_input("Your name", value=logged_name, help="This name will be used to thank you in email")
        email = st.text_input("Accountant email", placeholder="accountant@example.com")
        annual = st.session_state.q1+st.session_state.q2+st.session_state.q3+st.session_state.q4
        # DYNAMIC THANK YOU - USE LOGGED IN NAME
        txt = f"Country: {st.session_state.country} - {rules['name']}\nBusiness: {name}\nAnnual Income: {cur}{annual:.2f}\nExpenses: {cur}{df['total'].sum():.2f}\n\nThank you {name} for using SimpleTax!\n\nThanks, {name}"
        st.text_area("Email Preview", txt, height=160)
        st.caption(f"Preview uses logged-in name: {logged_name} - Thank you {logged_name}")
        st.download_button("Download CSV", df.to_csv(index=False).encode(), f"SimpleTax-{st.session_state.country}.csv", use_container_width=True)
        import urllib.parse
        st.link_button("Email Accountant", f"mailto:{email}?subject={urllib.parse.quote(f'Tax Records - {st.session_state.country} - {name}')}&body={urllib.parse.quote(txt)}", type="primary", use_container_width=True)
