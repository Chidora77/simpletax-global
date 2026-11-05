
import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import os, re, base64, io

st.set_page_config(page_title="SimpleTax Global", page_icon="🌍", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"] {background-color: #eef2f7 !important;}
.block-container {background-color: #eef2f7 !important; max-width: 420px !important;}
#MainMenu, header, footer, [data-testid="stToolbar"] {display: none !important;}
button, .stButton > button, div[data-testid="stButton"] button,
[data-testid="stFormSubmitButton"] button, a[data-testid="stLinkButton"] {
    background-color: #1e40af !important; background: #1e40af !important;
    color: white !important; border-color: #1e40af !important; border-radius: 10px !important;
    white-space: nowrap !important;
}
/* Radio - make blue */
div[data-baseweb="radio"] svg, div[data-baseweb="radio"] svg circle,
span[data-baseweb="radioMarkInner"], div[data-baseweb="radio"] div[aria-checked="true"],
div[role="radiogroup"] > div > div > div {
    fill: #1e40af !important;
    background-color: #1e40af !important;
    border-color: #1e40af !important;
    stroke: #1e40af !important;
}
/* Radio outer border blue */
div[data-baseweb="radio"] > div > div:first-child {
    border-color: #1e40af !important;
}
</style>
""", unsafe_allow_html=True)

st.components.v1.html("""
<script>
(function() {
  function forceBlue() {
    try {
      const doc = window.parent.document;
      if (!doc.getElementById('force-blue-v5')) {
        const s = doc.createElement('style');
        s.id = 'force-blue-v5';
        s.textContent = `
          button, div[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button,
          a[data-testid="stLinkButton"] { background-color: #1e40af !important; background: #1e40af !important; color: white !important; }
          div[data-baseweb="radio"] svg, span[data-baseweb="radioMarkInner"] { fill: #1e40af !important; background-color: #1e40af !important; }
          div[data-baseweb="radio"] div[aria-checked="true"] { background-color: #1e40af !important; border-color: #1e40af !important; }
        `;
        doc.head.appendChild(s);
      }
      doc.querySelectorAll('button, a[data-testid="stLinkButton"]').forEach(b=>{
        b.style.setProperty('background-color','#1e40af','important');
        b.style.setProperty('background','#1e40af','important');
        b.style.setProperty('color','white','important');
      });
      doc.querySelectorAll('div[data-baseweb="radio"] svg, span[data-baseweb="radioMarkInner"], div[data-baseweb="radio"] div[aria-checked="true"]').forEach(el=>{
        el.style.setProperty('fill','#1e40af','important');
        el.style.setProperty('background-color','#1e40af','important');
        el.style.setProperty('border-color','#1e40af','important');
      });
    } catch(e){}
  }
  forceBlue();
  setInterval(forceBlue, 300);
  try { new MutationObserver(forceBlue).observe(window.parent.document.body, {childList:true, subtree:true}); } catch(e){}
  setTimeout(forceBlue, 1000);
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

if "logout" in st.query_params:
    st.session_state.user_id = None
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

def extract_receipt_data_final(image_path):
    result={"shop":"", "total":0.0, "date":datetime.now().strftime("%Y-%m-%d"), "debug":""}
    api_key = os.getenv("OPENAI_API_KEY")
    try:
        if hasattr(st,'secrets') and "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
    except: pass
    if not api_key:
        result["debug"]="❌ OPENAI_API_KEY NOT FOUND\n\nFix:\n1. Go to Render.com → Your Service → Environment\n2. Add Variable: Key=OPENAI_API_KEY Value=sk-...\n3. Save → Wait 2 mins Live\n4. Upload receipt again\n\nGet key at: platform.openai.com/api-keys"
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
                {"type":"text","text":"Extract receipt: shop name (store name top), total amount (final total), date YYYY-MM-DD. Return ONLY JSON {\"shop\":\"Monsoon Foods\",\"total\":49.84,\"date\":\"2026-11-05\"}"},
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
            result["debug"]=f"✅ Success: {result['shop']} £{result['total']} {result['date']}"
            return result
    except Exception as e:
        result["debug"]=f"❌ OpenAI error: {e}\nCheck your API key is correct and has credit"
    if not result["shop"]: result["shop"]="Receipt"
    return result

def get_db_file():
    uid=st.session_state.user_id or "default"; c=st.session_state.country
    return f"receipts_{uid}_{c}.csv"

def get_upload_dir():
    uid=st.session_state.user_id or "default"; c=st.session_state.country
    d=f"receipt_images_{uid}_{c}"; os.makedirs(d, exist_ok=True); return d

def load_receipts():
    f=get_db_file()
    if not os.path.exists(f): pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at"]).to_csv(f, index=False)
    try: return pd.read_csv(f)
    except: return pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at"])

def save_receipt(shop, date, total, category, filename, image_path=""):
    f=get_db_file(); df=load_receipts()
    new_row=pd.DataFrame([{"date":date,"shop":shop,"total":float(total),"category":category,"filename":filename,"image_path":image_path,"created_at":datetime.now().strftime("%Y-%m-%d %H:%M")}])
    df=pd.concat([df,new_row], ignore_index=True); df.to_csv(f, index=False)

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
            st.session_state.user_id=safe; st.session_state.country=country_sel; st.rerun()
    st.stop()

# FIXED: wider column for logout full text - was [4,1] truncated to Log... now [3,1.5] shows full Logout
col_h1, col_h2=st.columns([2.5,1.5])
with col_h1: st.markdown("**🌍 SimpleTax Global**")
with col_h2:
    st.link_button("Logout", "?logout=1", type="secondary", use_container_width=True)
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
                st.image(img, width=200, caption=f"Ready to submit - only this receipt for {st.session_state.user_id}")
            except: st.write("Image ready")
        if st.session_state.current_image_path and os.path.exists(st.session_state.current_image_path):
            with st.spinner("Reading receipt with OpenAI..."):
                detected=extract_receipt_data_final(st.session_state.current_image_path)
                st.session_state.detected=detected
                if detected["total"]>0 or (detected["shop"] and detected["shop"]!="Receipt"):
                    st.success(f"✅ Auto-detected: {detected['shop']} £{detected['total']} {detected['date']}")
                else:
                    st.error("❌ Could not auto-read")
                    st.code(detected.get("debug","")[:1000])
        with st.form("add_form"):
            def_shop=st.session_state.detected.get("shop","")
            def_total=float(st.session_state.detected.get("total",0.0))
            def_date=st.session_state.detected.get("date", datetime.now().strftime("%Y-%m-%d"))
            shop=st.text_input("Description", value=def_shop, placeholder="e.g. Monsoon Foods - auto from receipt")
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
                    st.success(f"Saved {shop} {total:.2f}"); st.rerun()
