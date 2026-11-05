
import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os, re, base64, io, glob

st.set_page_config(page_title="SimpleTax Global", page_icon="🌍", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"] {background-color: #eef2f7 !important;}
.block-container {background-color: #eef2f7 !important; max-width: 430px !important;}
#MainMenu, header, footer, [data-testid="stToolbar"] {display: none !important;}

/* BUTTONS BLUE */
button, div[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button,
a[data-testid="stLinkButton"] {background-color: #1e40af !important; background: #1e40af !important; color: white !important; border-radius: 10px !important;}

/* RADIO BLUE - DEFINITIVE - OVERRIDES RED */
div[data-baseweb="radio"] > div:first-child {
    border-color: #1e40af !important;
    border-width: 2px !important;
    border-style: solid !important;
}
/* The inner dot - force blue */
div[data-baseweb="radio"] > div:first-child > div,
div[data-baseweb="radio"] div[data-checked="true"],
div[data-baseweb="radio"] div[aria-checked="true"] {
    background: #1e40af !important;
    background-color: #1e40af !important;
    border-color: #1e40af !important;
    width: 10px !important;
    height: 10px !important;
    border-radius: 50% !important;
}
/* SVG circle */
div[data-baseweb="radio"] svg, div[data-baseweb="radio"] svg circle,
span[data-baseweb="radioMarkInner"] {
    fill: #1e40af !important;
    background: #1e40af !important;
    background-color: #1e40af !important;
    stroke: #1e40af !important;
    color: #1e40af !important;
}
/* If still red, hue-rotate red to blue */
div[data-baseweb="radio"] div[style*="rgb(255, 75, 75)"],
div[data-baseweb="radio"] div[style*="#ff4b4b"],
div[data-baseweb="radio"] svg[style*="rgb(255, 75, 75)"] {
    background: #1e40af !important;
    background-color: #1e40af !important;
    fill: #1e40af !important;
    filter: hue-rotate(220deg) saturate(2) !important;
}

/* FIELDS BLACK */
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
    border: 1.5px solid #000 !important; background: white !important; border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

st.components.v1.html("""
<script>
(function(){
  function forceBlueRadio(){
    try{
      const doc = window.parent.document;
      // Add blue style once
      if(!doc.getElementById('blue-radio-v24')){
        const s=doc.createElement('style');
        s.id='blue-radio-v24';
        s.textContent=`
          div[data-baseweb="radio"] > div:first-child{border-color:#1e40af !important; border-width:2px !important;}
          div[data-baseweb="radio"] > div:first-child > div,
          div[data-baseweb="radio"] div[data-checked="true"]{background:#1e40af !important; background-color:#1e40af !important; width:10px !important; height:10px !important; border-radius:50% !important;}
          div[data-baseweb="radio"] svg circle, span[data-baseweb="radioMarkInner"]{fill:#1e40af !important; background:#1e40af !important;}
          button{background:#1e40af !important; color:white !important;}
        `;
        doc.head.appendChild(s);
      }
      // Force every radio dot blue
      doc.querySelectorAll('div[data-baseweb="radio"] > div:first-child > div, div[data-baseweb="radio"] svg circle, span[data-baseweb="radioMarkInner"]').forEach(el=>{
        el.style.setProperty('background','#1e40af','important');
        el.style.setProperty('background-color','#1e40af','important');
        el.style.setProperty('fill','#1e40af','important');
        el.style.setProperty('border-color','#1e40af','important');
      });
    }catch(e){}
  }
  forceBlueRadio();
  setTimeout(forceBlueRadio, 500);
  setTimeout(forceBlueRadio, 1500);
})();
</script>
""", height=0)

if "user_id" not in st.session_state: st.session_state.user_id = None
if "country" not in st.session_state: st.session_state.country = "UK"
if "q1" not in st.session_state: st.session_state.q1 = 0.0
if "q2" not in st.session_state: st.session_state.q2 = 0.0
if "q3" not in st.session_state: st.session_state.q3 = 0.0
if "q4" not in st.session_state: st.session_state.q4 = 0.0
if "upload_counter" not in st.session_state: st.session_state.upload_counter = 0
if "current_image_path" not in st.session_state: st.session_state.current_image_path = None
if "detected" not in st.session_state: st.session_state.detected = {"shop": "", "total": 0.0, "date": datetime.now().strftime("%Y-%m-%d"), "debug": ""}
if "receipts_data" not in st.session_state: st.session_state.receipts_data = []

try:
    qp = st.query_params
    if "user" in qp and st.session_state.user_id is None:
        saved_user = qp.get("user","")
        if saved_user and len(saved_user)>=2:
            st.session_state.user_id = saved_user
            if "country" in qp: st.session_state.country = qp.get("country","UK")
except: pass

if "logout" in st.query_params:
    st.session_state.user_id = None; st.session_state.receipts_data = []
    try: st.query_params.clear()
    except: pass
    st.rerun()

CURRENCY_MAP = {"UK": "£", "US": "$", "Nigeria": "₦", "Canada": "C$", "Australia": "A$", "Germany": "€"}
def get_currency(): return CURRENCY_MAP.get(st.session_state.country, "£")

# FISCAL YEAR DYNAMIC PER COUNTRY
FISCAL_YEAR_MAP = {
    "UK": {"Q1": "Apr-Jun", "Q2": "Jul-Sep", "Q3": "Oct-Dec", "Q4": "Jan-Mar", "label": "UK FY Apr-Mar"},
    "Canada": {"Q1": "Apr-Jun", "Q2": "Jul-Sep", "Q3": "Oct-Dec", "Q4": "Jan-Mar", "label": "Canada FY Apr-Mar"},
    "US": {"Q1": "Jan-Mar", "Q2": "Apr-Jun", "Q3": "Jul-Sep", "Q4": "Oct-Dec", "label": "US Calendar Jan-Dec"},
    "Germany": {"Q1": "Jan-Mar", "Q2": "Apr-Jun", "Q3": "Jul-Sep", "Q4": "Oct-Dec", "label": "Germany Calendar Jan-Dec"},
    "Nigeria": {"Q1": "Jan-Mar", "Q2": "Apr-Jun", "Q3": "Jul-Sep", "Q4": "Oct-Dec", "label": "Nigeria Calendar Jan-Dec"},
    "Australia": {"Q1": "Jul-Sep", "Q2": "Oct-Dec", "Q3": "Jan-Mar", "Q4": "Apr-Jun", "label": "Australia FY Jul-Jun"},
}
def get_fiscal(country):
    return FISCAL_YEAR_MAP.get(country, FISCAL_YEAR_MAP["US"])


def calc_tax_uk(profit):
    pa=12570; taxable=max(0,profit-pa); rem=taxable; tax=0
    # UK 2026/27 bands: PA £12,570, 20% £12,571-£50,270 (37,700), 40% £50,271-£125,140 (74,870), 45% over
    b1=min(rem,37700); tax+=b1*0.20; rem-=b1
    if rem>0:
        b2=min(rem,74870); tax+=b2*0.40; rem-=b2
        if rem>0: tax+=rem*0.45
    ni=0
    if profit>12570:
        ni+=(min(profit,50270)-12570)*0.06
        if profit>50270: ni+=(profit-50270)*0.02
    total=tax+ni
    info=f"UK 26/27: PA £{pa} 0%, £12,571-£50,270 20%, £50,271-£125,140 40%, >£125,140 45% | NI 6% £12,570-£50,270 +2% above"
    return taxable, total, tax, ni, info

def calc_tax_nigeria(profit):
    # Nigeria NTA 2025 effective Jan 2026: First 800k 0%, Next 2.2m 15%, Next 9m 18%, Next 13m 21%, Next 25m 23%, Above 50m 25%
    # Bands cumulative: 0-800k, 800k-3M, 3M-12M, 12M-25M, 25M-50M, 50M+
    taxable = max(0, profit)
    rem = taxable
    tax = 0
    # 0% first 800k
    free = min(rem, 800000)
    rem -= free
    if rem>0:
        amt = min(rem, 2200000); tax+=amt*0.15; rem-=amt
    if rem>0:
        amt = min(rem, 9000000); tax+=amt*0.18; rem-=amt
    if rem>0:
        amt = min(rem, 13000000); tax+=amt*0.21; rem-=amt
    if rem>0:
        amt = min(rem, 25000000); tax+=amt*0.23; rem-=amt
    if rem>0:
        tax+=rem*0.25
    # No NI in Nigeria
    info="Nigeria NTA 2025: First ₦800k 0%, Next ₦2.2m 15%, Next ₦9m 18%, Next ₦13m 21%, Next ₦25m 23%, Above ₦50m 25% | No NI"
    return taxable, tax, tax, 0, info

def calc_tax_us(profit):
    std_ded=16100; taxable=max(0,profit-std_ded); rem=taxable; tax=0
    brackets=[(12400,0.10),(50400,0.12),(105700,0.22),(208500,0.24),(353800,0.32),(579200,0.35),(float('inf'),0.37)]
    prev=0
    for limit, rate in brackets:
        if rem<=0: break
        span = (limit - prev) if limit!=float('inf') else rem
        amt=min(rem, span); tax+=amt*rate; rem-=amt; prev=limit if limit!=float('inf') else prev
    info=f"US 2026: Std Ded ${std_ded} | 10% $0-$12,400, 12% $12,400-$50,400, 22% $50,400-$105,700, 24% $105,700-$208,500, 32% $208,500-$353,800, 35% $353,800-$579,200, 37% >$579,200"
    return taxable, tax, tax, 0, info

def calc_tax_canada(profit):
    bpa=16452; taxable=max(0,profit-bpa); rem=taxable; tax=0
    # Canada 2026 federal: 14% up to $58,523, 20.5% $58,523-$117,045, 26% $117,045-$173,205, 29% $173,205-$258,482, 33% over
    brackets=[(58523,0.14),(117045,0.205),(173205,0.26),(258482,0.29),(float('inf'),0.33)]
    prev=0
    for limit, rate in brackets:
        if rem<=0: break
        span = (limit - prev) if limit!=float('inf') else rem
        amt=min(rem, span); tax+=amt*rate; rem-=amt; prev=limit if limit!=float('inf') else prev
    info=f"Canada 2026: BPA ${bpa} | 14% up to $58,523, 20.5% $58,523-$117,045, 26% $117,045-$173,205, 29% $173,205-$258,482, 33% >$258,482"
    return taxable, tax, tax, 0, info

def calc_tax_australia(profit):
    taxable=max(0,profit); rem=taxable; tax=0
    # Australia 2026-27: $0-$18,200 0%, $18,201-$45k 15%, $45k-$135k 30%, $135k-$190k 37%, 45% over +2% Medicare
    if rem>18200:
        amt=min(rem-18200, 45000-18200); tax+=amt*0.15
    if rem>45000:
        amt=min(rem-45000, 135000-45000); tax+=amt*0.30
    if rem>135000:
        amt=min(rem-135000, 190000-135000); tax+=amt*0.37
    if rem>190000:
        tax+=(rem-190000)*0.45
    medicare = taxable*0.02 if taxable>0 else 0
    total=tax+medicare
    info="Australia 26-27: $0-$18,200 0%, $18,201-$45k 15%, $45k-$135k 30%, $135k-$190k 37%, >$190k 45% + 2% Medicare"
    return taxable, total, tax, medicare, info

def calc_tax_germany(profit):
    grund=12348; taxable=max(0,profit-grund); rem=profit; tax=0
    # Germany 2026 simplified: Grundfreibetrag €12,348 0%, €12,349-€69,878 14%-42% progressive, €69,879-€277,825 42%, €277,826+ 45%
    # For simplicity use average progressive: use 14% at start increasing to 42%
    # Accurate formula is complex, use bracket approximation
    if profit<=grund:
        info="Germany 2026: Grundfreibetrag €12,348 0%, €12,349-€69,878 14%->42%, €69,879-€277,825 42%, €277,826+ 45%"
        return 0, 0, 0, 0, info
    # Simplified progressive: calculate as per German Einkommensteuer
    # Use formula: y = (profit-grund)/10000, then tax based on y
    y = (profit - grund) / 10000.0
    if profit <= 69878:
        # z = y, tax = (1000*y + 1400)*y ??? simplified linear approx 14% to 42%
        # Use progressive: approximate effective rate
        # For demo: tax = taxable * (0.14 + (profit-grund)/(69878-grund)*0.28) * 0.5 ??? Let's do accurate piecewise using BMF formula approximation
        # Use simplified BMF 2026 formula approximation: 
        if y <= 1:
            tax = (989.72*y + 1400)*y
        else:
            tax = (239.33*y + 2397)*y + 938.24
            # Adjust
            tax = tax * 1.0
    elif profit <= 277825:
        tax = 0.42*profit - 10150  # Simplified 42%
    else:
        tax = 0.45*profit - 18450
    # Ensure not negative
    tax = max(0, tax)
    taxable = max(0, profit-grund)
    info="Germany 2026: Grundfreibetrag €12,348 0%, €12,349-€69,878 14%->42% progressive, €69,879-€277,825 42%, €277,826+ 45%"
    return taxable, tax, tax, 0, info

def calc_tax_for_country(country, profit):
    if country=="UK": return calc_tax_uk(profit)
    if country=="Nigeria": return calc_tax_nigeria(profit)
    if country=="US": return calc_tax_us(profit)
    if country=="Canada": return calc_tax_canada(profit)
    if country=="Australia": return calc_tax_australia(profit)
    if country=="Germany": return calc_tax_germany(profit)
    return calc_tax_uk(profit)

def extract_receipt_data(image_path):
    result={"shop":"", "total":0.0, "date":datetime.now().strftime("%Y-%m-%d"), "debug":""}
    api_key = os.getenv("OPENAI_API_KEY")
    try:
        if hasattr(st,'secrets') and "OPENAI_API_KEY" in st.secrets: api_key = st.secrets["OPENAI_API_KEY"]
    except: pass
    cur = CURRENCY_MAP.get(st.session_state.country, "£")
    if not api_key:
        result["debug"]=f"❌ OPENAI_API_KEY NOT FOUND"
        return result
    try:
        import openai
        client=openai.OpenAI(api_key=api_key)
        img=Image.open(image_path)
        if img.mode!="RGB": img=img.convert("RGB")
        img.thumbnail((1024,1024))
        buf=io.BytesIO(); img.save(buf, format="JPEG", quality=90)
        b64=base64.b64encode(buf.getvalue()).decode()
        resp=client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":[{"type":"text","text":"Extract shop, total, date YYYY-MM-DD JSON"},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+b64}}]}], max_tokens=250)
        txt=resp.choices[0].message.content
        m=re.search(r"\{.*\}", txt, re.DOTALL)
        if m:
            import json
            data=json.loads(m.group(0))
            if data.get("shop"): result["shop"]=str(data["shop"])[:40]
            if data.get("total"):
                try:
                    val=str(data["total"]).replace(",","")
                    result["total"]=float(re.findall(r"[0-9]+\.?[0-9]*", val)[0])
                except: pass
            if data.get("date"):
                try:
                    d=datetime.strptime(str(data["date"])[:10], "%Y-%m-%d")
                    result["date"]=d.strftime("%Y-%m-%d")
                except: pass
            result["debug"]=f"✅ {cur}{result['total']} - {result['shop']}"
            return result
    except Exception as e: result["debug"]=f"❌ {e}"
    return result

def get_db_file():
    uid=st.session_state.user_id or "default"; c=st.session_state.country
    return f"receipts_{uid}_{c}.csv"

def get_upload_dir():
    uid=st.session_state.user_id or "default"; c=st.session_state.country
    d=f"receipt_images_{uid}_{c}"; os.makedirs(d, exist_ok=True); return d

def load_receipts():
    # ALWAYS load from file for current user+country - fixes Nigeria ₦ showing as UK £
    f=get_db_file()
    if os.path.exists(f):
        try:
            df=pd.read_csv(f)
            if not df.empty:
                st.session_state.receipts_data = df.to_dict('records')
                return df
        except: pass
    # If no file but session has data, check if session country matches current file
    if st.session_state.receipts_data:
        # Only use session if it matches current country file
        df = pd.DataFrame(st.session_state.receipts_data)
        if not df.empty:
            return df
    return pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at"])

def save_receipt(shop, date, total, category, filename, image_path=""):
    record={"date":date,"shop":shop,"total":float(total),"category":category,"filename":filename,"image_path":image_path,"created_at":datetime.now().strftime("%Y-%m-%d %H:%M")}
    st.session_state.receipts_data.append(record)
    try: pd.DataFrame(st.session_state.receipts_data).to_csv(get_db_file(), index=False)
    except: pass

if not st.session_state.user_id:
    st.markdown("### 🌍 SimpleTax Global")
    st.markdown("**👋 Welcome - Easy Receipts Submission**")
    with st.form("login_form"):
        user_code=st.text_input("MemorableCode", placeholder="type a memorable name or code", label_visibility="collapsed", key="login_code_input")
        st.caption("You should remember your memorable code")
        country_sel=st.selectbox("Select Country / Tax Region", ["UK","US","Nigeria","Canada","Australia","Germany"], index=0)
        submitted=st.form_submit_button("🔒 Login / Create Private Space", type="secondary", use_container_width=True)
        if submitted and user_code.strip() and len(user_code.strip())>=2:
            safe="".join(c for c in user_code if c.isalnum() or c in ("-","_")).strip()[:30]
            if not safe: safe=user_code.strip().replace(" ","_")[:30]
            st.session_state.user_id=safe; st.session_state.country=country_sel; st.session_state.receipts_data=[]
            try: st.query_params["user"]=safe; st.query_params["country"]=country_sel
            except: pass
            st.rerun()
    st.stop()

col_h1, col_h2=st.columns([2,1])
with col_h1: st.markdown("**🌍 SimpleTax Global**")
with col_h2:
    if st.button("Logout", type="secondary", use_container_width=True, key="logout_btn"):
        st.session_state.user_id=None; st.session_state.receipts_data=[]
        try: st.query_params.clear()
        except: pass
        st.rerun()
    st.caption(f"Private: {st.session_state.user_id}")
st.markdown("---")
country_sel=st.selectbox("Country / Tax Region", ["UK","US","Nigeria","Canada","Australia","Germany"], index=["UK","US","Nigeria","Canada","Australia","Germany"].index(st.session_state.country) if st.session_state.country in ["UK","US","Nigeria","Canada","Australia","Germany"] else 0)
if country_sel!=st.session_state.country:
    st.session_state.country=country_sel; st.session_state.receipts_data=[]
    try: st.query_params["country"]=country_sel
    except: pass
    st.rerun()

cur=get_currency()
main_nav=st.radio("nav", ["Add","List","Dashboard","Accountant"], horizontal=True, label_visibility="collapsed", key="main_nav")

if main_nav=="Add":
    st.markdown(f"**Add Receipt - {st.session_state.country} ({cur})**")
    upload_method=st.radio("method", ["Browse files","Take photo"], horizontal=True, label_visibility="collapsed", key="upload_method")
    uploaded=None
    uploader_key=f"uploader_{st.session_state.user_id}_{st.session_state.upload_counter}_{st.session_state.country}"
    if upload_method=="Browse files":
        uf=st.file_uploader(f"Pick receipt - {cur} will be auto-detected", type=["jpg","jpeg","png","heic"], key=uploader_key, label_visibility="collapsed")
        if uf: uploaded=uf
    else:
        cam=st.camera_input("Take photo", key=f"cam_{st.session_state.user_id}_{st.session_state.upload_counter}_{st.session_state.country}", label_visibility="collapsed")
        if cam: uploaded=cam
    if uploaded:
        orig_name=getattr(uploaded,'name', f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        safe_name="".join(c for c in orig_name if c.isalnum() or c in (".","_","-"))[:50]
        if not safe_name.lower().endswith(('.jpg','.jpeg','.png')): safe_name+=".jpg"
        upload_dir=get_upload_dir()
        image_path_saved=os.path.join(upload_dir, f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{safe_name}")
        try:
            data=uploaded.getvalue()
            with open(image_path_saved, "wb") as out: out.write(data)
            st.session_state.current_image_path=image_path_saved
        except: pass
        if st.session_state.current_image_path and os.path.exists(st.session_state.current_image_path):
            try:
                img=Image.open(st.session_state.current_image_path)
                st.image(img, width=200, caption=f"Ready for {st.session_state.user_id}")
            except: st.write("Image ready")
            with st.spinner(f"Reading receipt as {cur}..."):
                detected=extract_receipt_data(st.session_state.current_image_path)
                st.session_state.detected=detected
                if detected["total"]>0: st.success(f"✅ {cur}{detected['total']} - {detected['shop']}")
                else: st.error(f"❌ Could not auto-read"); st.code(detected.get("debug","")[:500])
        with st.form("add_form"):
            def_shop=st.session_state.detected.get("shop","")
            def_total=float(st.session_state.detected.get("total",0.0))
            def_date=st.session_state.detected.get("date", datetime.now().strftime("%Y-%m-%d"))
            shop=st.text_input("Description", value=def_shop)
            total=st.number_input(f"Total {cur}", value=def_total, step=0.01)
            date=st.text_input("Date", value=def_date)
            cat=st.selectbox("Category", ["Cost of goods sold","Tools","Travel","Materials","Office costs","Fuel","Other"])
            if st.form_submit_button("SUBMIT RECEIPT", type="secondary", use_container_width=True):
                if not shop.strip(): st.error("Please enter description")
                else:
                    save_receipt(shop, date, total, cat, safe_name, image_path_saved)
                    st.session_state.upload_counter+=1
                    st.session_state.current_image_path=None
                    st.session_state.detected={"shop":"","total":0.0,"date":datetime.now().strftime("%Y-%m-%d"),"debug":""}
                    st.success(f"Saved {shop} {cur}{total:.2f}")
                    st.rerun()

if main_nav=="List":
    st.markdown(f"**Receipts - List - {st.session_state.country} {cur}**")
    df=load_receipts()
    if df.empty: st.info("No receipts yet")
    else:
        st.success(f"{len(df)} receipts")
        for idx in range(len(df)-1, -1, -1):
            row=df.iloc[idx]
            c1,c2,c3,c4=st.columns([1,3,2,2])
            with c1:
                if row.get("image_path") and os.path.exists(str(row["image_path"])):
                    try:
                        im=Image.open(row["image_path"]); im.thumbnail((40,40)); st.image(im, width=40)
                    except: pass
            with c2: st.write(str(row['shop'])[:20])
            with c3: st.write(f"{cur}{float(row['total']):.2f}")
            with c4:
                with st.popover("View"):
                    st.write(f"{row['shop']} {row['total']}")
                    if st.button("DELETE", key=f"del_{idx}", type="secondary", use_container_width=True):
                        try: st.session_state.receipts_data.pop(idx)
                        except: pass
                        try: pd.DataFrame(st.session_state.receipts_data).to_csv(get_db_file(), index=False)
                        except: pass
                        st.rerun()

if main_nav=="Dashboard":
    st.markdown(f"**Dashboard - {st.session_state.country} Tax 2026**")
    df=load_receipts()
    total_exp=df["total"].sum() if not df.empty else 0
    st.caption(f"Total {cur}{total_exp:.2f} | {len(df)} receipts")

    c_clear1, c_clear2 = st.columns([1,2])
    with c_clear1:
        if st.button("Clear All", type="secondary", key="clear_incomes", use_container_width=True):
            st.session_state.q1=0.0; st.session_state.q2=0.0; st.session_state.q3=0.0; st.session_state.q4=0.0
            for k in ["q1_text","q2_text","q3_text","q4_text"]:
                if k in st.session_state: st.session_state[k]="0"
            st.rerun()
    with c_clear2: st.caption("Delete = set to 0")

    fiscal = get_fiscal(st.session_state.country)
    st.caption(f"{fiscal['label']} | Q1:{fiscal['Q1']} Q2:{fiscal['Q2']} Q3:{fiscal['Q3']} Q4:{fiscal['Q4']}")
    col1,col2=st.columns(2)
    with col1:
        q1_str=st.text_input(f"Q1 Income ({fiscal['Q1']}) {cur}", value=str(int(st.session_state.q1) if st.session_state.q1==int(st.session_state.q1) else st.session_state.q1), key="q1_text", placeholder="0")
        q2_str=st.text_input(f"Q2 Income ({fiscal['Q2']}) {cur}", value=str(int(st.session_state.q2) if st.session_state.q2==int(st.session_state.q2) else st.session_state.q2), key="q2_text", placeholder="0")
    with col2:
        q3_str=st.text_input(f"Q3 Income ({fiscal['Q3']}) {cur}", value=str(int(st.session_state.q3) if st.session_state.q3==int(st.session_state.q3) else st.session_state.q3), key="q3_text", placeholder="0")
        q4_str=st.text_input(f"Q4 Income ({fiscal['Q4']}) {cur}", value=str(int(st.session_state.q4) if st.session_state.q4==int(st.session_state.q4) else st.session_state.q4), key="q4_text", placeholder="0")
    
    def parse_income(s):
        try:
            s=str(s).strip().replace(",","")
            if s=="" or s.lower()=="none": return 0.0
            return float(s)
        except: return 0.0
    
    q1=parse_income(q1_str); q2=parse_income(q2_str); q3=parse_income(q3_str); q4=parse_income(q4_str)
    annual_income = float(q1) + float(q2) + float(q3) + float(q4)
    st.session_state.q1=float(q1); st.session_state.q2=float(q2); st.session_state.q3=float(q3); st.session_state.q4=float(q4)
    annual_profit=annual_income-total_exp
    taxable, total_annual, income_tax, ni_val, bracket_info = calc_tax_for_country(st.session_state.country, annual_profit)

    st.markdown(f"""
    <div style="display:flex; gap:10px; margin:10px 0;">
        <div style="flex:1; background:white; border:1px solid #000; border-radius:8px; padding:10px; text-align:center;">
            <div style="font-size:0.8rem;">Expenses</div>
            <div style="font-size:1.1rem; font-weight:600;">{cur}{total_exp:.2f}</div>
        </div>
        <div style="flex:1; background:white; border:1px solid #000; border-radius:8px; padding:10px; text-align:center;">
            <div style="font-size:0.8rem;">Profit</div>
            <div style="font-size:1.1rem; font-weight:600;">{cur}{annual_profit:.2f}</div>
        </div>
        <div style="flex:1; background:white; border:1px solid #000; border-radius:8px; padding:10px; text-align:center;">
            <div style="font-size:0.8rem;">Tax</div>
            <div style="font-size:1.1rem; font-weight:600;">{cur}{total_annual:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if annual_income>0:
        st.success(f"{cur} Income {cur}{annual_income:.2f} | Profit {cur}{annual_profit:.2f} | Taxable {cur}{taxable:.2f} | Tax {cur}{total_annual:.2f}")
        st.caption(f"{bracket_info}")

if main_nav=="Accountant":
    st.session_state.receipts_data = []
    df=load_receipts()
    fiscal = get_fiscal(st.session_state.country)
    st.markdown(f"**Send to Accountant - {st.session_state.country} ({cur}) - {fiscal['label']}**")
    if df.empty:
        st.info(f"No receipts yet for {st.session_state.country} - {cur}")
    else:
        st.success(f"{len(df)} receipts for {st.session_state.country} - Total {cur}{df['total'].sum():.2f}")
        your_name=st.text_input("Your name", value=st.session_state.user_id, key="acct_name")
        accountant_email=st.text_input("Accountant email", value="accountant@example.com", key="acct_email")
        qi=st.session_state.q1+st.session_state.q2+st.session_state.q3+st.session_state.q4
        profit=qi-df["total"].sum()
        taxable, total_annual, income_tax, ni_val, bracket_info = calc_tax_for_country(st.session_state.country, profit)
        st.markdown("### Preview")
        lines = []
        lines.append("Hello,")
        lines.append("")
        lines.append(f"Please find my records ({st.session_state.country} - {cur}) - {fiscal['label']}:")
        lines.append("")
        lines.append(f"- Name: {your_name}")
        lines.append(f"- Country: {st.session_state.country}")
        lines.append(f"- Currency: {cur}")
        lines.append(f"- Fiscal Year: {fiscal['label']}")
        lines.append(f"- Annual Income: {cur}{qi:.2f} (Q1 {fiscal['Q1']} {cur}{st.session_state.q1:.2f} + Q2 {fiscal['Q2']} {cur}{st.session_state.q2:.2f} + Q3 {fiscal['Q3']} {cur}{st.session_state.q3:.2f} + Q4 {fiscal['Q4']} {cur}{st.session_state.q4:.2f})")
        lines.append(f"- Total Expenses: {cur}{df['total'].sum():.2f} ({len(df)} receipts)")
        lines.append(f"- Annual Profit: {cur}{profit:.2f}")
        lines.append(f"- Taxable Profit: {cur}{taxable:.2f}")
        lines.append(f"- Estimated Tax: {cur}{total_annual:.2f} ({bracket_info})")
        lines.append("")
        lines.append("Receipts breakdown:")
        for i, r in df.iterrows():
            lines.append(f"  {i+1}. {r['date']} - {r['shop']} - {cur}{float(r['total']):.2f}")
        lines.append("")
        lines.append(f"Thanks,")
        lines.append(f"{your_name}")
        preview_text = chr(10).join(lines)
        st.text_area("Preview", preview_text, height=300, key="preview_simple", label_visibility="collapsed")

