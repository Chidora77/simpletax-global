
import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os, re, base64, io

st.set_page_config(page_title="SimpleTax Global", page_icon="🌍", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"] {background-color: #eef2f7 !important;}
.block-container {background-color: #eef2f7 !important; max-width: 430px !important;}
#MainMenu, header, footer, [data-testid="stToolbar"] {display: none !important;}

/* BUTTONS BLUE */
button, div[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button,
a[data-testid="stLinkButton"] {
    background-color: #1e40af !important; background: #1e40af !important;
    color: white !important; border-color: #1e40af !important; border-radius: 10px !important;
}

/* RADIO BLUE - STRONGEST */
input[type="radio"] { accent-color: #1e40af !important; }
div[data-baseweb="radio"] input { accent-color: #1e40af !important; }
div[data-baseweb="radio"] { --accent: #1e40af !important; }
div[data-baseweb="radio"] > div > div:first-child {
    border-color: #1e40af !important;
    border-width: 2px !important;
}
div[data-baseweb="radio"] svg, div[data-baseweb="radio"] svg circle,
span[data-baseweb="radioMarkInner"], span[data-baseweb="radioMarkOuter"] {
    fill: #1e40af !important;
    background-color: #1e40af !important;
    border-color: #1e40af !important;
    stroke: #1e40af !important;
}
div[data-baseweb="radio"] div[aria-checked="true"] {
    background-color: #1e40af !important;
    border-color: #1e40af !important;
}

/* FIX OVERLAPPING LABELS - Description, Total, Date */
label, div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label,
div[data-testid="stSelectbox"] label, div[data-testid="stTextArea"] label {
    margin-bottom: 6px !important;
    padding-bottom: 4px !important;
    display: block !important;
    position: relative !important;
    z-index: 1 !important;
    background: transparent !important;
    color: #1e293b !important;
    font-size: 0.9rem !important;
}
div[data-testid="stTextInput"], div[data-testid="stNumberInput"], div[data-testid="stSelectbox"] {
    margin-top: 4px !important;
    padding-top: 2px !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] textarea {
    border: 1.5px solid #94a3b8 !important;
    background-color: white !important;
    border-radius: 8px !important;
    color: #1e293b !important;
    margin-top: 2px !important;
}

/* ACCOUNTANT FIELDS VISIBLE */
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
    border: 1.5px solid #94a3b8 !important;
    background: white !important;
}
</style>
""", unsafe_allow_html=True)

st.components.v1.html("""
<script>
(function(){
  function forceBlue(){
    try{
      const doc = window.parent.document;
      if(!doc.getElementById('blue-v9')){
        const s=doc.createElement('style');
        s.id='blue-v9';
        s.textContent=`
          input[type="radio"]{accent-color:#1e40af !important;}
          div[data-baseweb="radio"] svg, span[data-baseweb="radioMarkInner"]{fill:#1e40af !important; background:#1e40af !important; border-color:#1e40af !important;}
          button, [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button, a[data-testid="stLinkButton"]{background:#1e40af !important; color:white !important;}
          label{margin-bottom:6px !important;}
          div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input{border:1.5px solid #94a3b8 !important; background:white !important; margin-top:2px !important;}
        `;
        doc.head.appendChild(s);
      }
      doc.querySelectorAll('button, a[data-testid="stLinkButton"]').forEach(b=>{
        b.style.setProperty('background-color','#1e40af','important');
        b.style.setProperty('color','white','important');
      });
      doc.querySelectorAll('input[type="radio"]').forEach(r=>{
        r.style.setProperty('accent-color','#1e40af','important');
      });
      doc.querySelectorAll('div[data-baseweb="radio"] svg, span[data-baseweb="radioMarkInner"], div[data-baseweb="radio"] div[aria-checked="true"]').forEach(el=>{
        try{
          el.style.setProperty('fill','#1e40af','important');
          el.style.setProperty('background-color','#1e40af','important');
          el.style.setProperty('border-color','#1e40af','important');
          el.style.setProperty('accent-color','#1e40af','important');
        }catch(e){}
      });
    }catch(e){}
  }
  forceBlue();
  setInterval(forceBlue, 400);
  try{ new MutationObserver(forceBlue).observe(window.parent.document.body,{childList:true,subtree:true}); }catch(e){}
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
if "detected" not in st.session_state:
    st.session_state.detected = {"shop": "", "total": 0.0, "date": datetime.now().strftime("%Y-%m-%d"), "debug": ""}
if "receipts_data" not in st.session_state:
    st.session_state.receipts_data = []

if "logout" in st.query_params:
    st.session_state.user_id = None
    st.session_state.receipts_data = []
    st.query_params.clear()
    st.rerun()

def calc_tax_uk(profit):
    pa=12570; taxable=max(0,profit-pa); rem=taxable; tax=0
    amt=min(rem,37700); tax+=amt*0.20; rem-=amt
    if rem>0:
        limit=125140-12570-37700
        amt2=min(rem,limit); tax+=amt2*0.40; rem-=amt2
        if rem>0: tax+=rem*0.45
    ni=0
    if profit>12570:
        ni+=(min(profit,50270)-12570)*0.06
        if profit>50270: ni+=(profit-50270)*0.02
    return taxable, tax+ni, tax, ni

def extract_receipt_data(image_path):
    result={"shop":"", "total":0.0, "date":datetime.now().strftime("%Y-%m-%d"), "debug":""}
    api_key = os.getenv("OPENAI_API_KEY")
    try:
        if hasattr(st,'secrets') and "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
    except: pass
    if not api_key:
        result["debug"]="❌ OPENAI_API_KEY NOT FOUND"
        return result
    try:
        import openai
        client=openai.OpenAI(api_key=api_key)
        img=Image.open(image_path)
        if img.mode!="RGB": img=img.convert("RGB")
        img.thumbnail((1024,1024))
        buf=io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        b64=base64.b64encode(buf.getvalue()).decode()
        resp=client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":[
                {"type":"text","text":"Extract receipt: shop name, total amount, date YYYY-MM-DD. Return ONLY JSON {\"shop\":\"Monsoon Foods\",\"total\":49.84,\"date\":\"2026-11-05\"}"},
                {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+b64}}
            ]}],
            max_tokens=250
        )
        txt=resp.choices[0].message.content
        m=re.search(r"\{.*\}", txt, re.DOTALL)
        if m:
            import json
            data=json.loads(m.group(0))
            if data.get("shop"): result["shop"]=str(data["shop"])[:40]
            if data.get("total"):
                try: result["total"]=float(str(data["total"]).replace(",","").replace("£",""))
                except: pass
            if data.get("date"):
                try:
                    d=datetime.strptime(str(data["date"])[:10], "%Y-%m-%d")
                    result["date"]=d.strftime("%Y-%m-%d")
                except: pass
            result["debug"]=f"✅ {result['shop']} £{result['total']}"
            return result
    except Exception as e:
        result["debug"]=f"❌ {e}"
    if not result["shop"]: result["shop"]="Receipt"
    return result

def get_db_file():
    uid=st.session_state.user_id or "default"; c=st.session_state.country
    return f"receipts_{uid}_{c}.csv"

def get_upload_dir():
    uid=st.session_state.user_id or "default"; c=st.session_state.country
    d=f"receipt_images_{uid}_{c}"; os.makedirs(d, exist_ok=True); return d

def load_receipts():
    if st.session_state.receipts_data:
        df = pd.DataFrame(st.session_state.receipts_data)
        if not df.empty:
            return df
    f=get_db_file()
    if not os.path.exists(f):
        return pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at"])
    try:
        df=pd.read_csv(f)
        if not df.empty:
            st.session_state.receipts_data = df.to_dict('records')
        return df
    except:
        return pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at"])

def save_receipt(shop, date, total, category, filename, image_path=""):
    record={"date":date,"shop":shop,"total":float(total),"category":category,"filename":filename,"image_path":image_path,"created_at":datetime.now().strftime("%Y-%m-%d %H:%M")}
    st.session_state.receipts_data.append(record)
    try:
        pd.DataFrame(st.session_state.receipts_data).to_csv(get_db_file(), index=False)
    except:
        pass

if not st.session_state.user_id:
    st.markdown("### 🌍 SimpleTax Global")
    st.markdown("**👋 Welcome - Easy Receipts Submission**")
    with st.form("login_form"):
        user_code=st.text_input("code", placeholder="type a memorable name or code", label_visibility="collapsed")
        st.caption("You should remember your memorable code")
        country_sel=st.selectbox("Select Country / Tax Region", ["UK","US","Nigeria","Canada","Australia","Germany"], index=0)
        submitted=st.form_submit_button("🔒 Login / Create Private Space", type="secondary", use_container_width=True)
        if submitted and user_code.strip() and len(user_code.strip())>=2:
            safe="".join(c for c in user_code if c.isalnum() or c in ("-","_")).strip()[:30]
            if not safe: safe=user_code.strip().replace(" ","_")[:30]
            st.session_state.user_id=safe; st.session_state.country=country_sel; st.session_state.receipts_data=[]; st.rerun()
    st.stop()

col_h1, col_h2=st.columns([2,1])
with col_h1: st.markdown("**🌍 SimpleTax Global**")
with col_h2:
    if st.button("Logout", type="secondary", use_container_width=True, key="logout_btn"):
        st.session_state.user_id=None
        st.session_state.receipts_data=[]
        st.query_params.clear()
        st.rerun()
    st.caption(f"Private: {st.session_state.user_id}")
st.markdown("---")
country_sel=st.selectbox("Country / Tax Region", ["UK","US","Nigeria","Canada","Australia","Germany"], index=["UK","US","Nigeria","Canada","Australia","Germany"].index(st.session_state.country) if st.session_state.country in ["UK","US","Nigeria","Canada","Australia","Germany"] else 0)
if country_sel!=st.session_state.country: st.session_state.country=country_sel; st.rerun()

main_nav=st.radio("nav", ["Add","List","Dashboard","Accountant"], horizontal=True, label_visibility="collapsed", key="main_nav")

if main_nav=="Add":
    st.markdown("**Add Receipt**")
    upload_method=st.radio("method", ["Browse files","Take photo"], horizontal=True, label_visibility="collapsed", key="upload_method")
    uploaded=None
    uploader_key=f"uploader_{st.session_state.user_id}_{st.session_state.upload_counter}"
    if upload_method=="Browse files":
        uf=st.file_uploader("Pick receipt", type=["jpg","jpeg","png","heic"], key=uploader_key, label_visibility="collapsed")
        if uf: uploaded=uf
    else:
        cam=st.camera_input("Take photo", key=f"cam_{st.session_state.user_id}_{st.session_state.upload_counter}", label_visibility="collapsed")
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
            with st.spinner("Reading receipt..."):
                detected=extract_receipt_data(st.session_state.current_image_path)
                st.session_state.detected=detected
                if detected["total"]>0:
                    st.success(f"✅ Auto-detected: {detected['shop']} £{detected['total']} {detected['date']}")
                else:
                    st.error("❌ Could not auto-read")
                    st.code(detected.get("debug","")[:800])
        with st.form("add_form"):
            def_shop=st.session_state.detected.get("shop","")
            def_total=float(st.session_state.detected.get("total",0.0))
            def_date=st.session_state.detected.get("date", datetime.now().strftime("%Y-%m-%d"))
            shop=st.text_input("Description", value=def_shop)
            total=st.number_input("Total £", value=def_total, step=0.01)
            date=st.text_input("Date", value=def_date)
            cat=st.selectbox("Category", ["Cost of goods sold","Tools","Travel","Materials","Office costs","Fuel","Other"])
            if st.form_submit_button("SUBMIT RECEIPT", type="secondary", use_container_width=True):
                if not shop.strip(): st.error("Please enter description")
                else:
                    save_receipt(shop, date, total, cat, safe_name, image_path_saved)
                    st.session_state.upload_counter+=1
                    st.session_state.current_image_path=None
                    st.session_state.detected={"shop":"","total":0.0,"date":datetime.now().strftime("%Y-%m-%d"),"debug":""}
                    st.success(f"Saved {shop} £{total:.2f} - Go to List")
                    st.rerun()

if main_nav=="List":
    st.markdown("**Receipts - List**")
    df=load_receipts()
    if df.empty:
        st.info("No receipts yet - Add in Add tab")
    else:
        st.success(f"{len(df)} receipts for {st.session_state.user_id}")
        for idx in range(len(df)-1, -1, -1):
            row=df.iloc[idx]
            c1,c2,c3,c4=st.columns([1,3,2,2])
            with c1:
                if row.get("image_path") and os.path.exists(str(row["image_path"])):
                    try:
                        im=Image.open(row["image_path"]); im.thumbnail((40,40)); st.image(im, width=40)
                    except: pass
            with c2: st.write(str(row['shop'])[:20])
            with c3: st.write(f"£{float(row['total']):.2f}")
            with c4:
                with st.popover("View"):
                    st.write(f"{row['shop']} {row['total']}")
                    if row.get("image_path") and os.path.exists(str(row["image_path"])): st.image(Image.open(row["image_path"]), width=200)
                    if st.button("DELETE", key=f"del_{idx}_{st.session_state.upload_counter}", type="secondary", use_container_width=True):
                        try: st.session_state.receipts_data.pop(idx)
                        except: pass
                        try: pd.DataFrame(st.session_state.receipts_data).to_csv(get_db_file(), index=False)
                        except: pass
                        st.rerun()

if main_nav=="Dashboard":
    st.markdown("**Dashboard**")
    df=load_receipts()
    total_exp=df["total"].sum() if not df.empty else 0
    st.caption(f"Loaded {len(df)} receipts, total £{total_exp:.2f}")
    col1,col2=st.columns(2)
    with col1:
        q1=st.number_input("Q1 Income (Apr-Jul)", value=st.session_state.q1, min_value=0.0, step=0.01, key="q1_input")
        q2=st.number_input("Q2 Income (Jul-Oct)", value=st.session_state.q2, min_value=0.0, step=0.01, key="q2_input")
    with col2:
        q3=st.number_input("Q3 Income (Oct-Jan)", value=st.session_state.q3, min_value=0.0, step=0.01, key="q3_input")
        q4=st.number_input("Q4 Income (Jan-Apr)", value=st.session_state.q4, min_value=0.0, step=0.01, key="q4_input")
    if q1!=st.session_state.q1: st.session_state.q1=q1
    if q2!=st.session_state.q2: st.session_state.q2=q2
    if q3!=st.session_state.q3: st.session_state.q3=q3
    if q4!=st.session_state.q4: st.session_state.q4=q4
    annual_income=st.session_state.q1+st.session_state.q2+st.session_state.q3+st.session_state.q4
    annual_profit=annual_income-total_exp
    c1,c2,c3=st.columns(3)
    c1.metric("Expenses", f"£{total_exp:.2f}"); c2.metric("Profit", f"£{annual_profit:.2f}")
    if annual_income>0:
        taxable,total_annual,income_tax,ni_val=calc_tax_uk(annual_profit)
        c3.metric("Tax", f"£{total_annual:.2f}")
        st.success(f"Income £{annual_income:.0f} | Profit £{annual_profit:.0f} | Tax £{total_annual:.0f}")
    else:
        c3.metric("Tax","£0.00")

if main_nav=="Accountant":
    st.markdown("**Send to Accountant**")
    df=load_receipts()
    if df.empty:
        st.info("No receipts - Add in Add tab")
    else:
        st.success(f"{len(df)} receipts ready")
        your_name=st.text_input("Your name", value=st.session_state.user_id, key="acct_name")
        accountant_email=st.text_input("Accountant email", value="accountant@example.com", key="acct_email")
        qi=st.session_state.q1+st.session_state.q2+st.session_state.q3+st.session_state.q4
        profit=qi-df["total"].sum()
        # FIXED PREVIEW - removed Dynamic labels and Private line
        st.markdown("### Preview")
        preview_text=f"""Hello,

Please find my MTD records:

- Name: {your_name}
- Annual Income: £{qi:.2f}
  (Q1 £{st.session_state.q1:.2f} + Q2 £{st.session_state.q2:.2f} + Q3 £{st.session_state.q3:.2f} + Q4 £{st.session_state.q4:.2f})
- Total Expenses: £{df['total'].sum():.2f} ({len(df)} receipts)
- Annual Profit: £{profit:.2f}

Thanks,
{your_name}
"""
        st.text_area("Preview", preview_text, height=200, key="preview_simple", label_visibility="collapsed")
        st.download_button("Download CSV", df.to_csv(index=False).encode(), "MTD.csv", "text/csv", use_container_width=True, type="secondary")
        import urllib.parse
        st.link_button("Open Email App", f"mailto:{accountant_email}?subject={urllib.parse.quote('MTD Records - '+your_name)}&body={urllib.parse.quote(preview_text)}", use_container_width=True, type="secondary")
