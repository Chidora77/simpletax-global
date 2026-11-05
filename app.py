
import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageEnhance
import os, re, base64, io, sys

st.set_page_config(page_title="SimpleTax Global", page_icon="🌍", layout="centered")

# NUCLEAR BLUE WITH JAVASCRIPT - FORCE EVEN INLINE STYLES
st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"] {background-color: #eef2f7 !important;}
.block-container {background-color: #eef2f7 !important; max-width: 380px !important; padding-top: 0.6rem !important;}
#MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
/* CSS Attempt */
button, .stButton > button, div[data-testid="stButton"] button,
[data-testid="stFormSubmitButton"] button, button[kind="primary"],
button[data-testid="stBaseButton-primaryFormSubmit"], button[data-testid="stBaseButton-primary"] {
    background-color: #1e40af !important; background: #1e40af !important; color: white !important;
    border-color: #1e40af !important; border-radius: 10px !important;
}
div[data-baseweb="radio"] svg {fill: #1e40af !important;}
</style>
""", unsafe_allow_html=True)

# JAVASCRIPT THAT FORCES BLUE EVERY 500ms - BEATS INLINE STYLE
st.components.v1.html("""
<script>
function forceBlue(){
  const sel = document.querySelectorAll('button, [role="button"], a[data-testid="stLinkButton"]');
  sel.forEach(b=>{
    const bg = b.style.backgroundColor;
    const txt = (b.innerText||'').toLowerCase();
    // Force if red or is our target buttons
    if(bg.includes('255') || bg.includes('75') || txt.includes('submit') || txt.includes('login') || txt.includes('logout')){
      b.style.setProperty('background-color','#1e40af','important');
      b.style.setProperty('background','#1e40af','important');
      b.style.setProperty('color','white','important');
      b.style.setProperty('border-color','#1e40af','important');
    }
  });
  // Radio dots
  document.querySelectorAll('div[data-baseweb="radio"] svg, span[data-baseweb="radioMarkInner"]').forEach(el=>{
    el.style.setProperty('fill','#1e40af','important');
    el.style.setProperty('background-color','#1e40af','important');
  });
}
setInterval(forceBlue, 500);
forceBlue();
</script>
""", height=0)

# --- rest of app ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "country" not in st.session_state:
    st.session_state.country = "UK"
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
    pa=12570
    taxable=max(0,profit-pa)
    rem=taxable; tax=0
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
    debug_logs=[]
    # Try OpenAI
    try:
        api_key=os.getenv("OPENAI_API_KEY")
        try:
            if hasattr(st,'secrets') and "OPENAI_API_KEY" in st.secrets:
                api_key=st.secrets["OPENAI_API_KEY"]
        except: pass
        if api_key:
            import openai
            client=openai.OpenAI(api_key=api_key)
            img=Image.open(image_path)
            if img.mode!="RGB": img=img.convert("RGB")
            img.thumbnail((1024,1024))
            buffered=io.BytesIO()
            img.save(buffered, format="JPEG", quality=90)
            b64=base64.b64encode(buffered.getvalue()).decode()
            debug_logs.append("Trying OpenAI Vision...")
            resp=client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":[
                    {"type":"text","text":"Extract receipt: shop name (top line), total amount (total/balance), date YYYY-MM-DD. Return JSON {\"shop\":\"...\",\"total\":12.34,\"date\":\"2026-11-05\"}. If blurry guess best."},
                    {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+b64}}
                ]}],
                max_tokens=200
            )
            txt=resp.choices[0].message.content
            debug_logs.append(f"OpenAI raw: {txt[:200]}")
            m=re.search(r"\{.*\}", txt, re.DOTALL)
            if m:
                import json
                data=json.loads(m.group(0))
                if data.get("shop"): result["shop"]=str(data["shop"])[:40]
                if data.get("total"):
                    try: result["total"]=float(str(data["total"]).replace(",","").replace("£","").replace("$",""))
                    except: pass
                if data.get("date"):
                    try:
                        d=datetime.strptime(str(data["date"])[:10], "%Y-%m-%d")
                        result["date"]=d.strftime("%Y-%m-%d")
                    except: pass
                if result["total"]>0 or result["shop"]:
                    result["debug"]="\n".join(debug_logs)
                    return result
    except Exception as e:
        debug_logs.append(f"OpenAI failed: {str(e)[:100]}")

    # Tesseract
    try:
        import pytesseract
        debug_logs.append("Trying pytesseract...")
        img=Image.open(image_path)
        if img.mode!="L": img=img.convert("L")
        # BIGGER + MORE CONTRAST
        img=img.resize((img.width*4, img.height*4), Image.LANCZOS)
        enhancer=ImageEnhance.Contrast(img)
        img=enhancer.enhance(2.5)
        enhancer2=ImageEnhance.Sharpness(img)
        img=enhancer2.enhance(2.5)

        text=""
        for psm in [6,4,3,11]:
            try:
                t=pytesseract.image_to_string(img, config=f'--oem 3 --psm {psm}')
                if len(t.strip())>len(text.strip()):
                    text=t
            except Exception as e:
                debug_logs.append(f"PSM {psm} fail {e}")
        
        debug_logs.append(f"OCR text length {len(text)} chars")
        debug_logs.append(f"OCR preview: {text[:300].replace(chr(10),' | ')}")

        if not text.strip():
            result["debug"]="\n".join(debug_logs) + "\nTesseract returned empty - image too blurry or tesseract not installed. Check packages.txt"
            return result

        lines=[l.strip() for l in text.split("\n") if l.strip()]

        # Shop
        for l in lines[:10]:
            up=l.upper()
            if len(l)<3: continue
            if "TOTAL" in up or "BALANCE" in up or "CHANGE" in up or "CASH" in up: continue
            if re.match(r'^[£$€]?\s*\d+\.\d{2}$', l): continue
            clean=re.sub(r'[^A-Za-z0-9 &\-]', '', l).strip()
            if len(clean)>=3:
                result["shop"]=clean[:40]
                break
        if not result["shop"] and lines:
            result["shop"]=re.sub(r'[^A-Za-z0-9 &\-]', '', lines[0])[:40]

        # Total amounts
        all_amounts=[]
        total_match=re.findall(r'TOTAL[\s:]*[£$€]?\s*(\d+\.\d{2})', text, re.IGNORECASE)
        for m in total_match:
            try: all_amounts.append(float(m))
            except: pass
        pound_amounts=re.findall(r'[£$€]?\s*(\d+\.\d{2})', text)
        for amt_str in pound_amounts:
            try:
                v=float(amt_str)
                if 0.1 <= v <= 20000:
                    all_amounts.append(v)
            except: pass
        if all_amounts:
            result["total"]=max(all_amounts)

        # Date
        for pat, fmt in [(r'(\d{2}/\d{2}/\d{4})','%d/%m/%Y'),(r'(\d{2}-\d{2}-\d{4})','%d-%m-%Y'),(r'(\d{4}-\d{2}-\d{2})','%Y-%m-%d')]:
            m=re.search(pat, text)
            if m:
                try:
                    d=datetime.strptime(m.group(1), fmt)
                    result["date"]=d.strftime("%Y-%m-%d")
                    break
                except: pass

    except ImportError as e:
        debug_logs.append(f"pytesseract not installed: {e}")
    except Exception as e:
        debug_logs.append(f"Tesseract error: {e}. Need packages.txt with tesseract-ocr")
    
    result["debug"]="\n".join(debug_logs)
    if not result["shop"]:
        result["shop"]="Receipt"
    return result

def get_db_file():
    uid=st.session_state.user_id or "default"
    c=st.session_state.country
    return f"receipts_{uid}_{c}.csv"

def get_upload_dir():
    uid=st.session_state.user_id or "default"
    c=st.session_state.country
    d=f"receipt_images_{uid}_{c}"
    os.makedirs(d, exist_ok=True)
    return d

def load_receipts():
    f=get_db_file()
    if not os.path.exists(f):
        pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at"]).to_csv(f, index=False)
    try: return pd.read_csv(f)
    except: return pd.DataFrame(columns=["date","shop","total","category","filename","image_path","created_at"])

def save_receipt(shop, date, total, category, filename, image_path=""):
    f=get_db_file()
    df=load_receipts()
    new_row=pd.DataFrame([{"date":date,"shop":shop,"total":float(total),"category":category,"filename":filename,"image_path":image_path,"created_at":datetime.now().strftime("%Y-%m-%d %H:%M")}])
    df=pd.concat([df,new_row], ignore_index=True)
    df.to_csv(f, index=False)

if not st.session_state.user_id:
    st.markdown("### 🌍 SimpleTax Global")
    st.markdown("**👋 Welcome - Easy Receipts Submission**")
    with st.form("login_form"):
        user_code=st.text_input("code", placeholder="type a memorable name or code", label_visibility="collapsed")
        st.caption("You should remember your memorable code")
        country_sel=st.selectbox("Select Country / Tax Region", ["UK","US","Nigeria","Canada","Australia","Germany"], index=0)
        submitted=st.form_submit_button("🔒 Login / Create Private Space", type="primary", use_container_width=True)
        if submitted and user_code.strip() and len(user_code.strip())>=2:
            safe="".join(c for c in user_code if c.isalnum() or c in ("-","_")).strip()[:30]
            if not safe: safe=user_code.strip().replace(" ","_")[:30]
            st.session_state.user_id=safe
            st.session_state.country=country_sel
            st.rerun()
    st.stop()

col_h1, col_h2=st.columns([4,1])
with col_h1: st.markdown("**🌍 SimpleTax Global**")
with col_h2:
    st.link_button("Logout", "?logout=1", type="primary", use_container_width=True)
    st.caption(f"Private: {st.session_state.user_id}")
st.markdown("---")
country_sel=st.selectbox("Country / Tax Region", ["UK","US","Nigeria","Canada","Australia","Germany"], index=["UK","US","Nigeria","Canada","Australia","Germany"].index(st.session_state.country) if st.session_state.country in ["UK","US","Nigeria","Canada","Australia","Germany"] else 0)
if country_sel!=st.session_state.country:
    st.session_state.country=country_sel
    st.rerun()
st.caption(f"Private: {st.session_state.user_id} - {st.session_state.country}")

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
            with st.spinner("Reading receipt (enhanced 4x)..."):
                detected=extract_receipt_data_final(st.session_state.current_image_path)
                st.session_state.detected=detected
                if detected["total"]>0 or (detected["shop"] and detected["shop"]!="Receipt"):
                    st.success(f"✅ Auto-detected: {detected['shop']} £{detected['total']} {detected['date']}")
                else:
                    st.error("❌ Could not auto-read - please enter manually")
                    st.caption("Debug info (why it failed):")
                    st.code(detected.get("debug","No debug")[:1000])
                    # Show install check
                    try:
                        import pytesseract
                        st.info(f"pytesseract installed: {pytesseract.get_tesseract_version()}")
                    except Exception as e:
                        st.warning(f"pytesseract NOT working: {e} - You need packages.txt with tesseract-ocr + clear cache deploy")
                    if not os.getenv("OPENAI_API_KEY"):
                        st.warning("Tip: Add OPENAI_API_KEY in Render Environment for 95% accuracy")
        with st.form("add_form"):
            def_shop=st.session_state.detected.get("shop","")
            def_total=float(st.session_state.detected.get("total",0.0))
            def_date=st.session_state.detected.get("date", datetime.now().strftime("%Y-%m-%d"))
            shop=st.text_input("Description", value=def_shop, placeholder="e.g. Monsoon Foods - auto from receipt")
            total=st.number_input("Total £", value=def_total, step=0.01)
            date=st.text_input("Date", value=def_date)
            cat=st.selectbox("Category", ["Cost of goods sold","Tools","Travel","Materials","Office costs","Fuel","Other"])
            if st.form_submit_button("SUBMIT RECEIPT", type="primary", use_container_width=True):
                if not shop.strip(): st.error("Please enter description")
                else:
                    save_receipt(shop, date, total, cat, safe_name, image_path_saved)
                    st.session_state.upload_counter+=1
                    st.session_state.current_image_path=None
                    st.session_state.detected={"shop":"","total":0.0,"date":datetime.now().strftime("%Y-%m-%d"),"debug":""}
                    st.success(f"Saved {shop} {total:.2f}")
                    st.rerun()

if main_nav=="List":
    st.markdown("**Receipts**")
    df_personal=load_receipts()
    if df_personal.empty: st.info("No receipts yet")
    else:
        st.caption(f"{len(df_personal)} receipts - only your private receipts for {st.session_state.user_id}")
        for idx in reversed(df_personal.index.tolist()):
            row=df_personal.loc[idx]
            c1,c2,c3,c4=st.columns([1,3,2,2])
            with c1:
                if row.get("image_path") and os.path.exists(str(row["image_path"])):
                    try:
                        im=Image.open(row["image_path"]); im.thumbnail((40,40)); st.image(im, width=40)
                    except: pass
            with c2: st.write(str(row['shop'])[:16])
            with c3: st.write(f"{float(row['total']):.2f}")
            with c4:
                with st.popover("View"):
                    st.write(f"{row['shop']} {row['total']}")
                    if row.get("image_path") and os.path.exists(str(row["image_path"])): st.image(Image.open(row["image_path"]), width=200)
                    st.write(f"Date: {row.get('date','')}")
                    if st.button("DELETE", key=f"del_{st.session_state.user_id}_{idx}", type="primary", use_container_width=True):
                        try:
                            if os.path.exists(str(row["image_path"])): os.remove(str(row["image_path"]))
                        except: pass
                        df_personal.drop(idx).to_csv(get_db_file(), index=False)
                        st.rerun()

if main_nav=="Dashboard":
    st.markdown("**Dashboard**")
    df=load_receipts()
    total_exp=df["total"].sum() if not df.empty else 0
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
    c1.metric("Expenses", f"{total_exp:.2f}")
    c2.metric("Profit Annual", f"{annual_profit:.2f}")
    if annual_income>0:
        taxable,total_annual,income_tax,ni_val=calc_tax_uk(annual_profit)
        c3.metric("Tax Annual", f"{total_annual:.2f}")
        st.success(f"Annual Income {annual_income:.0f} | Profit {annual_profit:.0f} | Tax {total_annual:.0f}/yr")
        with st.expander("Full UK breakdown"):
            st.markdown(f"Taxable £{taxable:.0f} | Income Tax £{income_tax:.0f} | NI £{ni_val:.0f} | Total £{total_annual:.0f}/yr")
    else: c3.metric("Tax Annual","0.00")

if main_nav=="Accountant":
    st.markdown("**Send to Accountant**")
    df=load_receipts()
    if df.empty: st.info("Add receipts first")
    else:
        st.caption(f"{len(df)} receipts")
        your_name=st.text_input("Your name", value=st.session_state.user_id)
        accountant_email=st.text_input("Accountant email", value="accountant@example.com")
        qi=st.session_state.q1+st.session_state.q2+st.session_state.q3+st.session_state.q4
        profit=qi-df["total"].sum()
        txt=f"Annual Income: {qi:.2f} Expenses: {df['total'].sum():.2f} Profit: {profit:.2f} Thanks {your_name}"
        st.text_area("Preview", txt, height=100, label_visibility="collapsed")
        st.download_button("Download CSV", df.to_csv(index=False).encode(), "MTD.csv", "text/csv", use_container_width=True)
        import urllib.parse
        st.link_button("Open Email App", f"mailto:{accountant_email}?subject={urllib.parse.quote('MTD')}&body={urllib.parse.quote(txt)}", use_container_width=True, type="primary")
