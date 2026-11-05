
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
a[data-testid="stLinkButton"] {background-color: #1e40af !important; background: #1e40af !important; color: white !important; border-color: #1e40af !important; border-radius: 10px !important;}

/* RADIO BLUE */
input[type="radio"] { accent-color: #1e40af !important; }
div[data-baseweb="radio"] svg, div[data-baseweb="radio"] svg circle, span[data-baseweb="radioMarkInner"] { fill: #1e40af !important; background: #1e40af !important; border-color: #1e40af !important; }
div[data-baseweb="radio"] > div:first-child { border: 2px solid #1e40af !important; }
div[data-baseweb="radio"] > div:first-child > div { background: #1e40af !important; }

/* FIELDS BLACK BORDER - NOT RED */
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
    border: 1.5px solid #000000 !important; background: white !important; border-radius: 8px !important; color: #1e293b !important;
}
div[data-testid="stTextInput"] input:focus, div[data-testid="stTextArea"] textarea:focus {
    border: 2px solid #000000 !important; box-shadow: none !important; outline: none !important;
}
div[data-testid="stTextInput"] > div:focus-within { border-color: #000000 !important; box-shadow: none !important; }

/* ALIGN FIELDS */
div[data-testid="stTextInput"] { margin-bottom: 10px !important; }
label { margin-bottom: 4px !important; color: #1e293b !important; font-size: 0.9rem !important; }

/* METRIC FULL AMOUNT - NO ... */
div[data-testid="stMetricValue"] { overflow: visible !important; white-space: normal !important; text-overflow: unset !important; word-break: break-all !important; }
</style>
""", unsafe_allow_html=True)

# LIGHTWEIGHT JS - NO FREEZE
st.components.v1.html("""
<script>
(function(){
  let ran=false;
  function lightFix(){
    if(ran) return;
    try{
      const doc = window.parent.document;
      if(!doc.getElementById('light-v22-blue')){
        const s=doc.createElement('style');
        s.id='light-v22-blue';
        s.textContent=`input[type="radio"]{accent-color:#1e40af !important;} div[data-baseweb="radio"] svg{fill:#1e40af !important;} button{background:#1e40af !important; color:white !important;} div[data-testid="stTextInput"] input{border:1.5px solid #000 !important;}`;
        doc.head.appendChild(s);
        ran=true;
      }
    }catch(e){}
  }
  lightFix();
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

# Persist login via URL
try:
    qp = st.query_params
    if "user" in qp and st.session_state.user_id is None:
        saved_user = qp.get("user","")
        if saved_user and len(saved_user)>=2:
            st.session_state.user_id = saved_user
            if "country" in qp: st.session_state.country = qp.get("country","UK")
            try:
                f = f"receipts_{st.session_state.user_id}_{st.session_state.country}.csv"
                if os.path.exists(f):
                    df_tmp = pd.read_csv(f)
                    if not df_tmp.empty: st.session_state.receipts_data = df_tmp.to_dict('records')
            except: pass
    if "q1" in qp:
        try:
            st.session_state.q1 = float(qp.get("q1","0")); st.session_state.q2 = float(qp.get("q2","0"))
            st.session_state.q3 = float(qp.get("q3","0")); st.session_state.q4 = float(qp.get("q4","0"))
        except: pass
except: pass

if "logout" in st.query_params:
    st.session_state.user_id = None; st.session_state.receipts_data = []
    try: st.query_params.clear()
    except: pass
    st.rerun()

CURRENCY_MAP = {"UK": "£", "US": "$", "Nigeria": "₦", "Canada": "C$", "Australia": "A$", "Germany": "€"}
def get_currency(): return CURRENCY_MAP.get(st.session_state.country, "£")

def load_all_receipts_admin():
    all_records=[]
    try:
        files=glob.glob("receipts_*.csv")
        for f in files:
            try:
                df_tmp=pd.read_csv(f)
                if not df_tmp.empty:
                    parts=f.replace("receipts_","").replace(".csv","").split("_")
                    if len(parts)>=2:
                        df_tmp["owner"]=parts[0]; df_tmp["country_file"]=parts[-1]
                    all_records.append(df_tmp)
            except: continue
        if all_records: return pd.concat(all_records, ignore_index=True)
    except: pass
    return pd.DataFrame()

def calc_tax_uk(profit):
    pa=12570; taxable=max(0,profit-pa); rem=taxable; tax=0
    b1=min(rem,37700); tax+=b1*0.20; rem-=b1
    if rem>0:
        limit=125140-12570-37700
        b2=min(rem,limit); tax+=b2*0.40; rem-=b2
        if rem>0: tax+=rem*0.45
    ni=0
    if profit>12570:
        ni+=(min(profit,50270)-12570)*0.06
        if profit>50270: ni+=(profit-50270)*0.02
    return taxable, tax+ni, tax, ni, f"PA £{pa} | 20%/40%/45% | NI 6%+2%"

def calc_tax_us(profit):
    std_ded=16100; taxable=max(0,profit-std_ded); rem=taxable; tax=0; prev=0
    for limit, rate in [(12400,0.10),(50400,0.12),(105700,0.22),(208500,0.24),(353800,0.32),(579200,0.35),(float('inf'),0.37)]:
        if rem<=0: break
        span = (limit - prev) if limit!=float('inf') else rem
        amt=min(rem, span); tax+=amt*rate; rem-=amt; prev=limit if limit!=float('inf') else prev
    return taxable, tax, tax, 0, f"Std Ded ${std_ded} | 10%/12%/22%/24%/32%/35%/37%"

def calc_tax_nigeria(profit):
    if profit<=800000: return 0,0,0,0,"First ₦800k 0%"
    taxable=profit-800000; rem=taxable; tax=0
    for limit, rate in [(2200000,0.15),(9000000,0.18),(13000000,0.21),(25000000,0.23),(float('inf'),0.25)]:
        if rem<=0: break
        amt=min(rem,limit); tax+=amt*rate; rem-=amt
    return taxable, tax, tax, 0, "0% ₦0-800k | 15% | 18% | 21% | 23% | 25% >₦50m"

def calc_tax_canada(profit):
    bpa=16452; taxable=max(0,profit-bpa); rem=taxable; tax=0; prev=0
    for limit, rate in [(58523,0.14),(117045,0.205),(181021,0.26),(252752,0.29),(float('inf'),0.33)]:
        if rem<=0: break
        span = (limit - prev) if limit!=float('inf') else rem
        amt=min(rem, span); tax+=amt*rate; rem-=amt; prev=limit if limit!=float('inf') else prev
    return taxable, tax, tax, 0, f"BPA ${bpa} | 14%/20.5%/26%/29%/33%"

def calc_tax_australia(profit):
    if profit<=18200: return 0,0,0,0,"0% $0-$18.2k"
    tax=0; medicare = profit*0.02 if profit>24276 else 0
    if profit>18200:
        amt=min(profit,45000)-18200
        if amt>0: tax+=amt*0.15
    if profit>45000:
        amt=min(profit,135000)-45000
        if amt>0: tax+=amt*0.30
    if profit>135000:
        amt=min(profit,190000)-135000
        if amt>0: tax+=amt*0.37
    if profit>190000: tax+=(profit-190000)*0.45
    return profit, tax+medicare, tax, medicare, "0% $0-18.2k | 15%/30%/37%/45% +2% Medicare"

def calc_tax_germany(profit):
    grund=12348; taxable=max(0,profit-grund)
    if taxable<=0: return 0,0,0,0,f"Grundfreibetrag €{grund}"
    if profit<=69878:
        rate = 0.14 + (0.42-0.14)*(profit-grund)/(69878-grund)
        tax = taxable * (0.14 + rate)/2
    elif profit<=277825: tax = (69878-grund)*0.28 + (profit-69878)*0.42
    else: tax = (69878-grund)*0.28 + (277825-69878)*0.42 + (profit-277825)*0.45
    return taxable, tax, tax, 0, f"Grundfreibetrag €{grund} | 14%→42% €12k-69k | 42% | 45%"

def calc_tax_for_country(country, profit):
    if country=="UK": return calc_tax_uk(profit)
    if country=="US": return calc_tax_us(profit)
    if country=="Nigeria": return calc_tax_nigeria(profit)
    if country=="Canada": return calc_tax_canada(profit)
    if country=="Australia": return calc_tax_australia(profit)
    if country=="Germany": return calc_tax_germany(profit)
    return calc_tax_uk(profit)

def get_tax_explanation(country, annual_income, total_exp, profit, taxable, total_tax, income_tax, ni, bracket_info):
    cur = CURRENCY_MAP.get(country, "£")
    exp = total_exp
    if country=="UK":
        return f"""**UK 2026/27:** You earned {cur}{annual_income:.2f} and spent {cur}{exp:.2f}, profit {cur}{profit:.2f}. First £12,570 tax-free PA, taxable {cur}{taxable:.2f}, tax {cur}{total_tax:.2f} (Income Tax {cur}{income_tax:.2f} at 20% + NI {cur}{ni:.2f} at 6%).
- Income {cur}{annual_income:.2f} - Expenses {cur}{exp:.2f} = Profit {cur}{profit:.2f}
- Taxable = Profit {cur}{profit:.2f} - PA £12,570 = {cur}{taxable:.2f}
- Total = {cur}{income_tax:.2f} + {cur}{ni:.2f} = {cur}{total_tax:.2f} | {bracket_info}"""
    return f"{country} | Profit {cur}{profit:.2f} | Taxable {cur}{taxable:.2f} | Tax {cur}{total_tax:.2f} | {bracket_info}"

def extract_receipt_data(image_path):
    result={"shop":"", "total":0.0, "date":datetime.now().strftime("%Y-%m-%d"), "debug":""}
    api_key = os.getenv("OPENAI_API_KEY")
    try:
        if hasattr(st,'secrets') and "OPENAI_API_KEY" in st.secrets: api_key = st.secrets["OPENAI_API_KEY"]
    except: pass
    country = st.session_state.country; cur = CURRENCY_MAP.get(country, "£")
    if not api_key:
        result["debug"]=f"❌ OPENAI_API_KEY NOT FOUND for {country} ({cur})"
        return result
    try:
        import openai
        client=openai.OpenAI(api_key=api_key)
        img=Image.open(image_path)
        if img.mode!="RGB": img=img.convert("RGB")
        img.thumbnail((1024,1024))
        buf=io.BytesIO(); img.save(buf, format="JPEG", quality=90)
        b64=base64.b64encode(buf.getvalue()).decode()
        prompt = f"You are a receipt OCR for {country}. Currency is {cur}. Extract shop, total number, date YYYY-MM-DD. Return ONLY JSON"
        resp=client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+b64}}]}], max_tokens=300)
        txt=resp.choices[0].message.content
        m=re.search(r"\{.*\}", txt, re.DOTALL)
        if m:
            import json
            data=json.loads(m.group(0))
            if data.get("shop"): result["shop"]=str(data["shop"])[:40]
            if data.get("total"):
                try:
                    val=str(data["total"]).replace(",","").replace("£","").replace("$","").replace("€","").replace("₦","").replace("C","").replace("A","")
                    result["total"]=float(re.findall(r"[0-9]+\.?[0-9]*", val)[0])
                except: pass
            if data.get("date"):
                try:
                    d=datetime.strptime(str(data["date"])[:10], "%Y-%m-%d")
                    result["date"]=d.strftime("%Y-%m-%d")
                except: pass
            result["debug"]=f"✅ {country} {cur}{result['total']} - {result['shop']}"
            return result
    except Exception as e: result["debug"]=f"❌ {country} {cur} {e}"
    if not result["shop"]: result["shop"]="Receipt"
    return result

def get_db_file():
    uid=st.session_state.user_id or "default"; c=st.session_state.country
    return f"receipts_{uid}_{c}.csv"

def get_upload_dir():
    uid=st.session_state.user_id or "default"; c=st.session_state.country
    d=f"receipt_images_{uid}_{c}"; os.makedirs(d, exist_ok=True); return d

def load_receipts():
    if st.session_state.user_id=="admin":
        df_all=load_all_receipts_admin()
        if not df_all.empty: return df_all
    if st.session_state.receipts_data:
        df = pd.DataFrame(st.session_state.receipts_data)
        if not df.empty: return df
    f=get_db_file()
    if not os.path.exists(f):
        try:
            files=glob.glob(f"receipts_{st.session_state.user_id}_*.csv")
            if files:
                df=pd.read_csv(files[0])
                if not df.empty:
                    st.session_state.receipts_data = df.to_dict('records')
                    return df
        except: pass
        return pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at","owner","country_file"])
    try:
        df=pd.read_csv(f)
        if not df.empty: st.session_state.receipts_data = df.to_dict('records')
        return df
    except: return pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at","owner","country_file"])

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
            try:
                st.query_params["user"]=safe; st.query_params["country"]=country_sel
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
    try:
        st.query_params["country"]=country_sel
        f = f"receipts_{st.session_state.user_id}_{st.session_state.country}.csv"
        if os.path.exists(f):
            df_tmp = pd.read_csv(f)
            if not df_tmp.empty: st.session_state.receipts_data = df_tmp.to_dict('records')
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
        uf=st.file_uploader(f"Pick receipt - {cur} will be auto-detected for {st.session_state.country}", type=["jpg","jpeg","png","heic"], key=uploader_key, label_visibility="collapsed")
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
                st.image(img, width=200, caption=f"Ready for {st.session_state.user_id} - {st.session_state.country} {cur}")
            except: st.write("Image ready")
            with st.spinner(f"Reading receipt as {st.session_state.country} {cur}..."):
                detected=extract_receipt_data(st.session_state.current_image_path)
                st.session_state.detected=detected
                if detected["total"]>0:
                    st.success(f"✅ {st.session_state.country} {cur}{detected['total']} - {detected['shop']} {detected['date']}")
                else:
                    st.error(f"❌ Could not auto-read {cur}")
                    st.code(detected.get("debug","")[:800])
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
                    st.success(f"Saved {shop} {cur}{total:.2f} - Go to List")
                    st.rerun()

if main_nav=="List":
    if st.session_state.user_id=="admin":
        st.markdown(f"**🔑 Admin - All Users Receipts - {st.session_state.country} {cur}**")
    else:
        st.markdown(f"**Receipts - List - {st.session_state.country} {cur}**")
    df=load_receipts()
    if df.empty: st.info("No receipts yet - Add in Add tab")
    else:
        st.success(f"{len(df)} receipts for {st.session_state.user_id} - {st.session_state.country} {cur}")
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
                    if row.get("image_path") and os.path.exists(str(row["image_path"])): st.image(Image.open(row["image_path"]), width=200)
                    if st.button("DELETE", key=f"del_{idx}_{st.session_state.upload_counter}_{st.session_state.country}", type="secondary", use_container_width=True):
                        try: st.session_state.receipts_data.pop(idx)
                        except: pass
                        try: pd.DataFrame(st.session_state.receipts_data).to_csv(get_db_file(), index=False)
                        except: pass
                        st.rerun()

if main_nav=="Dashboard":
    st.markdown(f"**Dashboard - {st.session_state.country} Tax 2026**")
    df=load_receipts()
    total_exp=df["total"].sum() if not df.empty else 0
    st.caption(f"Country: {st.session_state.country} | Currency: {cur} | {len(df)} receipts total {cur}{total_exp:.2f}")

    c_clear1, c_clear2 = st.columns([1,2])
    with c_clear1:
        if st.button("Clear All", type="secondary", key="clear_incomes", use_container_width=True):
            st.session_state.q1=0.0; st.session_state.q2=0.0; st.session_state.q3=0.0; st.session_state.q4=0.0
            for k in ["q1_text","q2_text","q3_text","q4_text","q1_input","q2_input","q3_input","q4_input"]:
                if k in st.session_state: st.session_state[k]="0" if "text" in k else 0.0
            try:
                st.query_params["q1"]="0"; st.query_params["q2"]="0"; st.query_params["q3"]="0"; st.query_params["q4"]="0"
            except: pass
            st.rerun()
    with c_clear2: st.caption("Type amount, Enter. Delete = set to 0. Clear All = all 0.")

    col1,col2=st.columns(2)
    with col1:
        q1_str=st.text_input(f"Q1 Income (Apr-Jul) {cur}", value=str(int(st.session_state.q1) if st.session_state.q1==int(st.session_state.q1) else st.session_state.q1), key="q1_text", placeholder="0")
        q2_str=st.text_input(f"Q2 Income (Jul-Oct) {cur}", value=str(int(st.session_state.q2) if st.session_state.q2==int(st.session_state.q2) else st.session_state.q2), key="q2_text", placeholder="0")
    with col2:
        q3_str=st.text_input(f"Q3 Income (Oct-Jan) {cur}", value=str(int(st.session_state.q3) if st.session_state.q3==int(st.session_state.q3) else st.session_state.q3), key="q3_text", placeholder="0")
        q4_str=st.text_input(f"Q4 Income (Jan-Apr) {cur}", value=str(int(st.session_state.q4) if st.session_state.q4==int(st.session_state.q4) else st.session_state.q4), key="q4_text", placeholder="0")
    
    def parse_income(s):
        try:
            s=str(s).strip().replace(",","").replace(cur,"").replace("£","").replace("$","").replace("€","").replace("₦","").replace("C","").replace("A","")
            if s=="" or s.lower()=="none": return 0.0
            return float(s)
        except: return 0.0
    
    q1=parse_income(q1_str); q2=parse_income(q2_str); q3=parse_income(q3_str); q4=parse_income(q4_str)
    annual_income = float(q1) + float(q2) + float(q3) + float(q4)
    st.session_state.q1=float(q1); st.session_state.q2=float(q2); st.session_state.q3=float(q3); st.session_state.q4=float(q4)
    try:
        st.query_params["q1"]=str(float(q1)); st.query_params["q2"]=str(float(q2)); st.query_params["q3"]=str(float(q3)); st.query_params["q4"]=str(float(q4))
    except: pass
    annual_profit=annual_income-total_exp
    taxable, total_annual, income_tax, ni_val, bracket_info = calc_tax_for_country(st.session_state.country, annual_profit)

    st.markdown(f"""
    <div style="display:flex; gap:10px; margin:10px 0;">
        <div style="flex:1; background:white; border:1px solid #000; border-radius:8px; padding:10px; text-align:center;">
            <div style="font-size:0.8rem; color:#64748b;">Expenses</div>
            <div style="font-size:1.2rem; font-weight:600; word-break:break-all;">{cur}{total_exp:.2f}</div>
        </div>
        <div style="flex:1; background:white; border:1px solid #000; border-radius:8px; padding:10px; text-align:center;">
            <div style="font-size:0.8rem; color:#64748b;">Profit</div>
            <div style="font-size:1.2rem; font-weight:600; word-break:break-all;">{cur}{annual_profit:.2f}</div>
        </div>
        <div style="flex:1; background:white; border:1px solid #000; border-radius:8px; padding:10px; text-align:center;">
            <div style="font-size:0.8rem; color:#64748b;">Tax</div>
            <div style="font-size:1.2rem; font-weight:600; word-break:break-all;">{cur}{total_annual:.2f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if annual_income>0:
        st.success(f"{st.session_state.country} {cur} | Income {cur}{annual_income:.2f} | Profit {cur}{annual_profit:.2f} | Taxable {cur}{taxable:.2f} | Tax {cur}{total_annual:.2f}")
        st.caption(f"Brackets: {bracket_info}")
        explanation = get_tax_explanation(st.session_state.country, annual_income, total_exp, annual_profit, taxable, total_annual, income_tax, ni_val, bracket_info)
        with st.expander(f"📖 Explain this tax - How {cur}{total_annual:.2f} calculated?", expanded=False):
            st.markdown(explanation)
    else:
        st.info(f"Enter Q1-Q4 income for {st.session_state.country} to see {cur} tax")

if main_nav=="Accountant":
    st.markdown(f"**Send to Accountant - {st.session_state.country} {cur}**")
    df=load_receipts()
    if df.empty: st.info("No receipts - Add in Add tab")
    else:
        st.success(f"{len(df)} receipts ready - {st.session_state.country} {cur}")
        your_name=st.text_input("Your name", value=st.session_state.user_id, key="acct_name")
        accountant_email=st.text_input("Accountant email", value="accountant@example.com", key="acct_email")
        qi=st.session_state.q1+st.session_state.q2+st.session_state.q3+st.session_state.q4
        profit=qi-df["total"].sum()
        taxable, total_annual, income_tax, ni_val, bracket_info = calc_tax_for_country(st.session_state.country, profit)
        st.markdown("### Preview")
        preview_text=f"""Hello,

Please find my records ({st.session_state.country} - {cur}):

- Name: {your_name}
- Annual Income: {cur}{qi:.2f}
  (Q1 {cur}{st.session_state.q1:.2f} + Q2 {cur}{st.session_state.q2:.2f} + Q3 {cur}{st.session_state.q3:.2f} + Q4 {cur}{st.session_state.q4:.2f})
- Total Expenses: {cur}{df['total'].sum():.2f} ({len(df)} receipts)
- Annual Profit: {cur}{profit:.2f}
- Taxable Profit: {cur}{taxable:.2f}
- Estimated Tax: {cur}{total_annual:.2f} ({bracket_info})

Thanks,
{your_name}
"""
        st.text_area("Preview", preview_text, height=240, key="preview_simple", label_visibility="collapsed")
        st.download_button(f"Download CSV {cur}", df.to_csv(index=False).encode(), f"MTD_{st.session_state.country}.csv", "text/csv", use_container_width=True, type="secondary")
        import urllib.parse
        st.link_button("Open Email App", f"mailto:{accountant_email}?subject={urllib.parse.quote(f'Records {st.session_state.country} - '+your_name)}&body={urllib.parse.quote(preview_text)}", use_container_width=True, type="secondary")
