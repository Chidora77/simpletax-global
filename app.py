
import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os, glob, re, base64, io

st.set_page_config(page_title="SimpleTax UK", page_icon="🧾", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
.stApp {background-color: #eef2f7 !important;}
[data-testid="stAppViewContainer"] {background-color: #eef2f7 !important;}
.block-container {background-color: #eef2f7 !important; max-width: 380px !important; padding-top: 0.6rem !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; margin: 0 auto !important;}
h1 {color: #1e40af !important; font-size: 1.5rem !important; font-weight: 800 !important;}
h3 {color: #1e3a8a !important; font-size: 1.0rem !important; font-weight: 700 !important;}
h2 {color: #1e3a8a !important; font-size: 1.1rem !important;}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {border: 1.5px solid #cbd5e1 !important; border-radius: 10px !important; height: 2.4rem !important; font-size: 0.88rem !important; background: #f8fafc !important;}
[data-baseweb="select"] div {border-radius: 10px !important; background: #f8fafc !important; font-size: 0.88rem !important;}
.stButton button {background-color: #1e40af !important; color: white !important; border-radius: 10px !important; height: 2.7rem !important; font-weight: 600 !important; border: none !important;}
.stButton button:hover {background-color: #1e3a8a !important;}
.stCaption {color: #64748b !important; font-size: 0.78rem !important;}
div[data-baseweb="radio"] svg {fill: #1e40af !important; color: #1e40af !important;}
div[data-baseweb="radio"] div[aria-checked="true"] {background-color: #1e40af !important; border-color: #1e40af !important;}
div[data-baseweb="radio"] label {font-size: 0.82rem !important; color: #334155 !important;}
div[role="radiogroup"] {gap: 12px !important;}
[data-testid="stFileUploader"] {background-color: #eef2f7 !important; border-radius: 10px !important; padding: 0.5rem !important; border: 1px solid #e2e8f0 !important;}
[data-testid="stFileUploader"] button {background: white !important; color: #334155 !important; border: 1px solid #cbd5e1 !important; border-radius: 8px !important;}
[data-testid="stMetricValue"] {color: #1e293b !important; font-size: 1.4rem !important; font-weight: 800 !important;}
[data-testid="stMetricLabel"] {font-size: 0.7rem !important; color: #64748b !important;}
[data-testid="stMetric"] {background: white !important; border-radius: 10px !important; padding: 8px !important; border: 1px solid #e2e8f0 !important;}
.stAlert {border-radius: 10px !important; font-size: 0.82rem !important;}
#MainMenu, header, footer, [data-testid="stToolbar"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "q1" not in st.session_state:
    st.session_state.q1 = 0.0
if "q2" not in st.session_state:
    st.session_state.q2 = 0.0
if "q3" not in st.session_state:
    st.session_state.q3 = 0.0
if "q4" not in st.session_state:
    st.session_state.q4 = 0.0
if "upload_counter" not in st.session_state:
    st.session_state.upload_counter = 0
if "current_image_path" not in st.session_state:
    st.session_state.current_image_path = None
if "detected" not in st.session_state:
    st.session_state.detected = {"shop": "", "total": 0.0, "date": datetime.now().strftime("%Y-%m-%d")}

if "logout" in st.query_params:
    st.session_state.user_id = None
    st.query_params.clear()
    st.rerun()

def extract_receipt_data(image_path):
    result = {"shop": "", "total": 0.0, "date": datetime.now().strftime("%Y-%m-%d")}
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        try:
            if hasattr(st, 'secrets') and "OPENAI_API_KEY" in st.secrets:
                api_key = st.secrets["OPENAI_API_KEY"]
        except:
            pass
        if api_key:
            import openai
            client = openai.OpenAI(api_key=api_key)
            img = Image.open(image_path)
            img.thumbnail((1024, 1024))
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            b64 = base64.b64encode(buffered.getvalue()).decode()
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": "Extract from this UK receipt: Shop name, Total amount number, Date YYYY-MM-DD. Return JSON {\"shop\":\"Monsoon Foods\",\"total\":49.84,\"date\":\"2026-11-05\"}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]}],
                max_tokens=150
            )
            import json
            txt = resp.choices[0].message.content.strip()
            m = re.search(r"\{.*\}", txt, re.DOTALL)
            if m:
                data = json.loads(m.group(0))
                if data.get("shop"):
                    result["shop"] = str(data["shop"])[:40]
                if data.get("total"):
                    try:
                        result["total"] = float(data["total"])
                    except:
                        pass
                if data.get("date"):
                    try:
                        d = datetime.strptime(str(data["date"])[:10], "%Y-%m-%d")
                        result["date"] = d.strftime("%Y-%m-%d")
                    except:
                        pass
            return result
    except:
        pass
    try:
        import pytesseract
        img = Image.open(image_path).convert("L")
        text = pytesseract.image_to_string(img)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            result["shop"] = lines[0][:40]
        for pat in [r"TOTAL\s*[:\s]*£?\s*(\d+\.\d{2})", r"Total\s*[:\s]*£?\s*(\d+\.\d{2})", r"£\s*(\d+\.\d{2})"]:
            m = re.findall(pat, text, re.IGNORECASE)
            if m:
                try:
                    v = m[-1]
                    if isinstance(v, tuple):
                        v = v[0]
                    result["total"] = float(v)
                    break
                except:
                    pass
        for pat in [r"(\d{2}/\d{2}/\d{4})", r"(\d{4}-\d{2}-\d{2})"]:
            m = re.search(pat, text)
            if m:
                try:
                    ds = m.group(1)
                    if "/" in ds:
                        d = datetime.strptime(ds, "%d/%m/%Y")
                    else:
                        d = datetime.strptime(ds, "%Y-%m-%d")
                    result["date"] = d.strftime("%Y-%m-%d")
                    break
                except:
                    pass
    except:
        pass
    return result

def get_db_file():
    uid = st.session_state.user_id or "default"
    return f"receipts_{uid}.csv"

def get_upload_dir():
    uid = st.session_state.user_id or "default"
    d = f"receipt_images_{uid}"
    os.makedirs(d, exist_ok=True)
    return d

def load_receipts():
    f = get_db_file()
    if not os.path.exists(f):
        pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at"]).to_csv(f, index=False)
    try:
        return pd.read_csv(f)
    except:
        return pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at"])

def save_receipt(shop, date, total, category, filename, image_path=""):
    f = get_db_file()
    df = load_receipts()
    new_row = pd.DataFrame([{
        "date": date, "shop": shop, "total": float(total), "category": category,
        "filename": filename, "image_path": image_path,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(f, index=False)

def calc_tax_from_annual(annual_profit):
    taxable = max(0, annual_profit - 12570)
    basic = min(taxable, 37700) * 0.20
    higher = max(0, taxable - 37700) * 0.40
    ni = 0
    if annual_profit > 12570:
        ni += (min(annual_profit, 50270) - 12570) * 0.06
        if annual_profit > 50270:
            ni += (annual_profit - 50270) * 0.02
    class2 = 179.40 if annual_profit > 12570 else 0
    total_annual = basic + higher + ni + class2
    return annual_profit, taxable, basic, higher, ni, class2, total_annual

if not st.session_state.user_id:
    st.markdown("### 🧾 SimpleTax UK")
    st.markdown("**👋 Welcome - Easy Receipts Submission**")
    with st.form("login_form"):
        user_code = st.text_input("code", placeholder="type a memorable name or code", label_visibility="collapsed")
        st.caption("You should remember your memorable code")
        submitted = st.form_submit_button("🔒 Login / Create Private Space", type="primary", use_container_width=True)
        if submitted:
            if user_code.strip() and len(user_code.strip())>=2:
                safe = "".join(c for c in user_code if c.isalnum() or c in ("-","_")).strip()[:30]
                if not safe:
                    safe = user_code.strip().replace(" ","_")[:30]
                st.session_state.user_id = safe
                st.rerun()
            else:
                st.error("Enter at least 2 characters")
    with st.expander("How to create memorable name or code?"):
        st.markdown("**Create code you remember:** - Name + number: ABC, Monsoon1 - 2-30 chars - Same code shows your private receipts")
    st.stop()

# Header matching screenshots
col_h1, col_h2 = st.columns([4,1])
with col_h1:
    st.markdown("**📃 SimpleTax UK**")
with col_h2:
    st.link_button("Logout", "?logout=1", type="primary", use_container_width=True)
    st.caption(f"Private: {st.session_state.user_id}")

st.markdown("---")

# Nav - blue dot
main_nav = st.radio("nav", ["Add", "List", "Dashboard", "Accountant"], horizontal=True, label_visibility="collapsed", key="main_nav")

if main_nav == "Add":
    st.markdown("**Add Receipt**")
    upload_method = st.radio("method", ["Browse files", "Take photo"], horizontal=True, label_visibility="collapsed", key="upload_method")
    uploaded = None
    uploader_key = f"uploader_{st.session_state.user_id}_{st.session_state.upload_counter}"
    if upload_method == "Browse files":
        uf = st.file_uploader("Pick receipt", type=["jpg","jpeg","png","heic"], key=uploader_key, label_visibility="collapsed")
        if uf:
            uploaded = uf
    else:
        cam = st.camera_input("Take photo", key=f"cam_{st.session_state.user_id}_{st.session_state.upload_counter}", label_visibility="collapsed")
        if cam:
            uploaded = cam

    if uploaded:
        try:
            orig_name = getattr(uploaded, 'name', f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        except:
            orig_name = f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        safe_name = "".join(c for c in orig_name if c.isalnum() or c in (".","_","-"))[:50]
        if not safe_name.lower().endswith(('.jpg','.jpeg','.png')):
            safe_name += ".jpg"
        upload_dir = get_upload_dir()
        image_path_saved = os.path.join(upload_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{safe_name}")
        try:
            data = uploaded.getvalue()
            with open(image_path_saved, "wb") as out:
                out.write(data)
            st.session_state.current_image_path = image_path_saved
        except:
            pass

        if st.session_state.current_image_path and os.path.exists(st.session_state.current_image_path):
            try:
                img = Image.open(st.session_state.current_image_path)
                st.image(img, width=200, caption=f"Ready to submit - only this receipt for {st.session_state.user_id}")
            except:
                st.write("Image ready")

        if st.session_state.current_image_path and os.path.exists(st.session_state.current_image_path):
            with st.spinner("Reading receipt..."):
                detected = extract_receipt_data(st.session_state.current_image_path)
                st.session_state.detected = detected
                msgs = []
                if detected["total"] > 0:
                    msgs.append(f"£{detected['total']:.2f}")
                if detected["shop"]:
                    msgs.append(detected["shop"])
                if detected["date"] != datetime.now().strftime("%Y-%m-%d"):
                    msgs.append(detected["date"])
                if msgs:
                    st.success(f"Auto-detected: {', '.join(msgs)} (you can edit below)")
                else:
                    st.info("Could not auto-read - please enter manually")

        with st.form("add_form"):
            def_shop = st.session_state.detected.get("shop","")
            def_total = float(st.session_state.detected.get("total",0.0))
            def_date = st.session_state.detected.get("date", datetime.now().strftime("%Y-%m-%d"))
            shop = st.text_input("Description", value=def_shop, placeholder="e.g. Monsoon Foods")
            total = st.number_input("Total £", value=def_total, step=0.01)
            date = st.text_input("Date", value=def_date, help="Auto-detected from receipt, or enter manually")
            cat = st.selectbox("Category", ["Cost of goods sold","Tools","Travel","Materials","Office costs","Fuel","Other"])
            if st.form_submit_button("SUBMIT RECEIPT", type="primary", use_container_width=True):
                if not shop.strip():
                    st.error("Please enter description")
                else:
                    save_receipt(shop, date, total, cat, safe_name, image_path_saved)
                    st.session_state.upload_counter += 1
                    st.session_state.current_image_path = None
                    st.session_state.detected = {"shop":"", "total":0.0, "date": datetime.now().strftime("%Y-%m-%d")}
                    st.success(f"Saved {shop} £{total:.2f}")
                    st.rerun()

if main_nav == "List":
    st.markdown("**Receipts**")
    df_personal = load_receipts()
    if st.session_state.user_id.lower() == "admin":
        st.info("ADMIN MODE - All users receipts")
        files = glob.glob("receipts_*.csv")
        all_users = []
        for f in files:
            try:
                d = pd.read_csv(f)
                if d.empty:
                    continue
                user = f.replace("receipts_","").replace(".csv","")
                if user.lower()=="admin":
                    continue
                all_users.append({"user": user, "count": len(d), "total": d["total"].sum(), "df": d})
            except:
                pass
        for u in all_users:
            with st.expander(f"{u['user']} - {u['count']} - £{u['total']:.2f}"):
                d = u['df'].rename(columns={"shop":"Description","date":"Date","total":"Total £","category":"Category"})
                st.dataframe(d[["Date","Description","Total £","Category"]], width="stretch")
    if df_personal.empty:
        if st.session_state.user_id.lower()!="admin":
            st.info("No receipts yet")
    else:
        st.caption(f"{len(df_personal)} receipts, £{df_personal['total'].sum():.2f} - only your private receipts for {st.session_state.user_id}")
        for idx in reversed(df_personal.index.tolist()):
            row = df_personal.loc[idx]
            c1, c2, c3, c4 = st.columns([1,3,2,2])
            with c1:
                if row.get("image_path") and os.path.exists(str(row["image_path"])):
                    try:
                        im = Image.open(row["image_path"])
                        im.thumbnail((40,40))
                        st.image(im, width=40)
                    except:
                        pass
            with c2:
                st.write(str(row['shop'])[:16])
            with c3:
                st.write(f"£{float(row['total']):.2f}")
            with c4:
                with st.popover("View"):
                    st.write(f"{row['shop']} £{row['total']}")
                    if row.get("image_path") and os.path.exists(str(row["image_path"])):
                        st.image(Image.open(row["image_path"]), width=200)
                    st.write(f"Date: {row.get('date','')}")
                    if st.button("DELETE", key=f"del_{st.session_state.user_id}_{idx}", type="primary", use_container_width=True):
                        try:
                            if os.path.exists(str(row["image_path"])):
                                os.remove(str(row["image_path"]))
                        except:
                            pass
                        df_personal.drop(idx).to_csv(get_db_file(), index=False)
                        st.rerun()

if main_nav == "Dashboard":
    st.markdown("**Dashboard**")
    st.caption("Quarterly Income - enter each quarter separately (dynamic)")
    df = load_receipts()
    total_exp = df["total"].sum() if not df.empty else 0
    col1, col2 = st.columns(2)
    with col1:
        q1 = st.number_input("Q1 Income £ (Apr-Jul)", value=st.session_state.q1, min_value=0.0, step=0.01, key="q1_input")
        q2 = st.number_input("Q2 Income £ (Jul-Oct)", value=st.session_state.q2, min_value=0.0, step=0.01, key="q2_input")
    with col2:
        q3 = st.number_input("Q3 Income £ (Oct-Jan)", value=st.session_state.q3, min_value=0.0, step=0.01, key="q3_input")
        q4 = st.number_input("Q4 Income £ (Jan-Apr)", value=st.session_state.q4, min_value=0.0, step=0.01, key="q4_input")
    if q1 != st.session_state.q1:
        st.session_state.q1 = q1
    if q2 != st.session_state.q2:
        st.session_state.q2 = q2
    if q3 != st.session_state.q3:
        st.session_state.q3 = q3
    if q4 != st.session_state.q4:
        st.session_state.q4 = q4
    annual_income = st.session_state.q1 + st.session_state.q2 + st.session_state.q3 + st.session_state.q4
    annual_profit = annual_income - total_exp
    c1, c2, c3 = st.columns(3)
    c1.metric("Expenses", f"£{total_exp:.2f}")
    c2.metric("Profit Annual", f"£{annual_profit:.2f}")
    if annual_income > 0:
        annual, taxable, basic, higher, ni, class2, total_annual = calc_tax_from_annual(annual_profit)
        c3.metric("Tax Annual", f"£{total_annual:.2f}")
        st.success(f"Annual Income £{annual_income:.0f} | Profit £{annual_profit:.0f} | Tax £{total_annual:.0f}/yr")
        with st.expander("Full HMRC breakdown - dynamic per quarter"):
            st.markdown(f"Annual Profit £{annual_profit:.2f} | Taxable £{taxable:.2f} | Income Tax £{basic+higher:.2f} | NI £{ni+class2:.2f} | Total £{total_annual:.2f}/yr")
            st.caption(f"Q1 £{st.session_state.q1:.0f} + Q2 £{st.session_state.q2:.0f} + Q3 £{st.session_state.q3:.0f} + Q4 £{st.session_state.q4:.0f} = £{annual_income:.0f}")
    else:
        c3.metric("Tax Annual", "£0.00")
        st.info("Enter income for each quarter above - no more x4 same quarter")
    if not df.empty:
        st.bar_chart(df.groupby("category")["total"].sum(), height=150)
        d = df.rename(columns={"shop": "Description", "date": "Date", "total": "Total", "category": "Category"})
        st.dataframe(d[["Date","Description","Total","Category"]], width="stretch")
        st.download_button("Download CSV", d.to_csv(index=False).encode(), "MTD.csv", "text/csv", use_container_width=True)

if main_nav == "Accountant":
    st.markdown("**Send to Accountant**")
    df = load_receipts()
    if df.empty:
        st.info("Add receipts first")
    else:
        st.caption("Ready")
        st.markdown(f"### {len(df)} receipts")
        st.markdown(f"↑ £{df['total'].sum():.2f}")
        your_name = st.text_input("Your name", value=st.session_state.user_id)
        your_business = st.text_input("Business", value=f"{st.session_state.user_id} Foods")
        accountant_email = st.text_input("Accountant email", value="accountant@example.com")
        qi = st.session_state.q1 + st.session_state.q2 + st.session_state.q3 + st.session_state.q4
        st.info(f"Total Annual Income (dynamic): £{qi:.2f} = Q1 £{st.session_state.q1:.0f}+Q2 £{st.session_state.q2:.0f}+Q3 £{st.session_state.q3:.0f}+Q4 £{st.session_state.q4:.0f}")
        profit = qi - df["total"].sum()
        txt = f"Business: {your_business}\nAnnual Income: £{qi:.2f}\nExpenses: £{df['total'].sum():.2f}\nAnnual Profit: £{profit:.2f}\n\nThank you {your_name} for using SimpleTax!\n\nThanks, {your_name}"
        st.markdown("Preview")
        st.text_area("Preview", txt, height=100, label_visibility="collapsed")
        st.download_button("Download CSV", df.to_csv(index=False).encode(), "MTD.csv", "text/csv", use_container_width=True)
        import urllib.parse
        subject = urllib.parse.quote(f"MTD - {your_business}")
        body = urllib.parse.quote(txt)
        st.link_button("Open Email App", f"mailto:{accountant_email}?subject={subject}&body={body}", use_container_width=True, type="primary")
