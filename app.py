import streamlit as st
import os, io, json, base64
from datetime import datetime, timedelta, timezone
from gtts import gTTS
import PyPDF2
import openai
import gspread
from google.oauth2.service_account import Credentials
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer

# ====================== 1. INITIALIZATION ======================
st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")

if "auth" not in st.session_state:
    st.session_state.auth = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_worker" not in st.session_state:
    st.session_state.current_worker = "Guest"

# ====================== 2. TACTICAL UI CSS ======================
st.markdown('''
    <style>
    .stApp { background: radial-gradient(circle at top right, #0f172a, #020617); color: #f8fafc; }
    .hero-container {
        background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(10px);
        padding: 40px; border-radius: 20px; border: 1px solid rgba(173, 255, 47, 0.3);
    }
    .hero-title { color: #ffffff; font-size: 60px; font-weight: 900; letter-spacing: -2px; margin: 0; }
    .status-dot { color: #ADFF2F; text-shadow: 0 0 10px #ADFF2F; }
    .custom-header { background: rgba(15, 23, 42, 0.9); padding: 10px 20px; border-radius: 10px; border: 1px solid #ADFF2F; margin-bottom: 20px; }
    </style>
''', unsafe_allow_html=True)

# ====================== 3. CORE LOGISTICS ENGINES ======================
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def get_last_ids(sheet_name):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        vals = sheet.get_all_values()
        if len(vals) < 2: return "1", "1"
        last_row = vals[-1]
        # Column 0 = SL NO, Column 3 = GP NO
        return last_row[0], last_row[3]
    except: return "1", "1"

def save_to_google_sheets(worker, payload, sheet_name):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        now = datetime.now(timezone(timedelta(hours=4)))
        date_s = now.strftime("%d-%m-%Y")
        
        if sheet_name == "MANUAL PASS":
            # ALIGNMENT FIX: [SL NO, DATE, BOOK NO, GP NO, CONSIGNEE, BILL NO, DESCRIPTION, UNIT, CASH REC, UPDATED BY, REMARKS, AMOUNT]
            row_data = [payload[0], date_s, payload[1], payload[2], payload[3], payload[4], payload[5], payload[6], payload[7], worker, payload[8], payload[9]]
        else:
            row_data = [date_s] + [str(i).upper() for i in payload] + [worker]
            
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"❌ DATABASE ERROR: {str(e)}"); return False

def search_logs(query, sheet_name):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        all_rows = sheet.get_all_values()
        if len(all_rows) < 2: return None, None
        header = all_rows[0]
        for idx, row in enumerate(all_rows[1:], start=2): 
            if any(query.upper() in str(c).upper() for c in row):
                return dict(zip(header, row)), idx
        return None, None
    except: return None, None

# ====================== 4. AUTHENTICATION ======================
WORKER_DB = {"Precious Akpezi Ojah": "Falcon01", "Bambi": "Nancy", "Mr_Ali": "Ali"}
if not st.session_state.auth:
    st.title("🦅 FALCON EYE | GATE 4 LOGIN")
    user_id = st.selectbox("USER:", list(WORKER_DB.keys()))
    pwd = st.text_input("PASSWORD:", type="password")
    if st.button("AUTHORIZE") and pwd == WORKER_DB[user_id]:
        st.session_state.auth, st.session_state.current_worker = True, user_id
        st.rerun()
    st.stop()

# ====================== 5. MAIN INTERFACE ======================
dubai_now = datetime.now(timezone(timedelta(hours=4)))
st.markdown(f'<div class="custom-header"><b>Operator:</b> {st.session_state.current_worker} | <b>Time:</b> {dubai_now.strftime("%H:%M")}</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-container"><h1 class="hero-title">FALCON EYE</h1><h3 style="margin:0;">GATE 4 <span class="status-dot">● SECURE</span></h3></div>', unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🛰️ INTELLIGENCE", "📟 LOGISTICS", "🕵️ AUDIT", "📖 PROTOCOLS"])

with t1:
    st.subheader("Intelligence & Translation")
    full_langs = {"Arabic": "ar", "Bengali": "bn", "Hindi": "hi", "Urdu": "ur", "Pashto": "ps", "Malayalam": "ml"}
    d_lang = st.selectbox("Driver Language:", list(full_langs.keys()))
    driver_speech = speech_to_text(language=full_langs[d_lang], start_prompt="👂 LISTEN TO DRIVER", key='d_mic')
    
    if driver_speech:
        st.info(f"Driver said: {driver_speech}")
    
    cmd = st.text_input("English Command to Driver:")
    if st.button("🔊 SPEAK TO DRIVER") and cmd:
        # Simple AI Translation placeholder - uses gTTS for output
        tts = gTTS(text=cmd, lang=full_langs[d_lang])
        stream = io.BytesIO(); tts.write_to_fp(stream)
        st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)

with t2:
    st.subheader("Logistics Entry Control")
    
    # FETCH LAST IDS FOR AUTO-INCREMENT
    last_sl, last_gp = get_last_ids("MANUAL PASS")
    try: next_sl = str(int(last_sl) + 1)
    except: next_sl = ""
    try: next_gp = str(int(last_gp) + 1)
    except: next_gp = ""

    form_type = st.radio("Select Form:", ["Manual Gate Pass", "Labour Charge"], horizontal=True)

    with st.form("logistics_form", clear_on_submit=True):
        if form_type == "Manual Gate Pass":
            c1, c2, c3 = st.columns(3)
            f_sl = c1.text_input("SL NO (Auto)", value=next_sl).upper()
            f_bk = c2.text_input("BOOK NO").upper()
            f_gp = c3.text_input("GATE PASS NO (Auto)", value=next_gp).upper()
            
            f_con = st.text_input("CONSIGNEE / COMPANY").upper()
            f_bill = st.text_input("CUSTOMS BILL NO").upper()
            f_desc = st.text_area("DESCRIPTION OF GOODS").upper()
            
            c4, c5, c6 = st.columns(3)
            f_unit = c4.text_input("TYPE / UNIT").upper()
            f_cash = c5.text_input("CASH RECEIPT NO").upper()
            f_amt = c6.text_input("AMOUNT (AED)").upper()
            f_rem = st.text_input("REMARKS").upper()
            
            payload = [f_sl, f_bk, f_gp, f_con, f_bill, f_desc, f_unit, f_cash, f_rem, f_amt]
            target_sheet = "MANUAL PASS"
            unique_id = f_gp # For duplicate check

        elif form_type == "Labour Charge":
            c1, c2 = st.columns(2)
            f_start = c1.text_input("START TIME (e.g. 14:00)").upper()
            f_end = c2.text_input("FINISH TIME").upper()
            f_vouch = st.text_input("VOUCHER NO").upper()
            f_amt_l = st.text_input("AMOUNT").upper()
            payload = [f_start, f_end, f_vouch, f_amt_l]
            target_sheet = "LABOUR CHARGE"
            unique_id = f_vouch

        if st.form_submit_button("🚀 SYNC TO DATABASE"):
            # 1. DUPLICATE CHECK
            dup, _ = search_logs(unique_id, target_sheet)
            if dup:
                st.error(f"⚠️ DUPLICATE DETECTED! ID {unique_id} already exists in {target_sheet}.")
            else:
                if save_to_google_sheets(st.session_state.current_worker, payload, target_sheet):
                    st.success(f"✅ RECORD {unique_id} SUCCESSFULLY SYNCED")
                    st.balloons()

with t3:
    st.subheader("Audit & Correction")
    search_q = st.text_input("Search any ID (SL NO / GP NO / BILL NO):")
    if st.button("🔍 RUN SEARCH"):
        res, row_idx = search_logs(search_q, "MANUAL PASS")
        if res:
            st.write(f"Record found at Row: {row_idx}")
            st.table(res)
        else:
            st.warning("No records found.")

with t4:
    st.subheader("Gate 4 Protocols")
    if os.path.exists("gate_manual.pdf"):
        pdf_viewer("gate_manual.pdf", height=600)
    else:
        st.info("Upload 'gate_manual.pdf' to the root folder to view protocols here.")
