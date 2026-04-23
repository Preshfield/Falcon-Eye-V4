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

# ====================== 1. CRITICAL INITIALIZATION ======================
st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")

if "auth" not in st.session_state:
    st.session_state.auth = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_worker" not in st.session_state:
    st.session_state.current_worker = "Guest"

# ====================== 2. FULL TACTICAL CSS ======================
st.markdown('''
    <style>
    .stApp { background: radial-gradient(circle at top right, #0f172a, #020617); color: #f8fafc; }
    .hero-container {
        background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(10px);
        padding: 60px 40px; border-radius: 20px; margin-bottom: 30px;
        border: 1px solid rgba(173, 255, 47, 0.3); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    .hero-title { color: #ffffff !important; font-size: 72px !important; font-weight: 900 !important; letter-spacing: -3px !important; margin: 0;}
    .status-dot { color: #ADFF2F; font-weight: 800; text-shadow: 0 0 15px #ADFF2F; animation: pulse 2s infinite; }
    .custom-header { background: rgba(15, 23, 42, 0.9); padding: 15px 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ADFF2F; }
    .intercom-box { background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); }
    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.3; } 100% { opacity: 1; } }
    </style>
''', unsafe_allow_html=True)

# ====================== 3. UTILITY ENGINES (DATABASE & SEARCH) ======================
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def save_to_google_sheets(worker, payload, sheet_name="LOG"):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        now = datetime.now(timezone(timedelta(hours=4)))
        date_s = now.strftime("%d-%m-%Y")
        
        if sheet_name == "LOG":
            row_data = [date_s, now.strftime("%H:%M:%S"), "GATE 4", worker, str(payload), "VERIFIED"]
        elif sheet_name == "MANUAL PASS":
            # FIXED ALIGNMENT: SL NO is Col 1, DATE is Col 2
            row_data = [payload[0], date_s, payload[1], payload[2], payload[3], payload[4], payload[5], payload[6], payload[7], worker, payload[8], payload[9]]
        else:
            row_data = [date_s] + [str(i).upper() for i in payload] + [worker]
            
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"❌ DATABASE ERROR: {str(e)}"); return False

def update_google_sheet(row_index, payload, sheet_name):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        now = datetime.now(timezone(timedelta(hours=4)))
        date_s = now.strftime("%d-%m-%Y")
        if sheet_name == "MANUAL PASS":
            row_data = [payload[0], date_s, payload[1], payload[2], payload[3], payload[4], payload[5], payload[6], payload[7], st.session_state.current_worker, payload[8], payload[9]]
        else:
            row_data = [date_s] + [str(i).upper() for i in payload] + [st.session_state.current_worker]
        sheet.update(f"A{row_index}", [row_data])
        return True
    except Exception as e:
        st.error(f"Update Failed: {e}"); return False

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

def get_last_ids(sheet_name):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        vals = sheet.get_all_values()
        if len(vals) < 2: return "1", "1"
        last_row = vals[-1]
        return last_row[0], last_row[3] # SL NO and GP NO
    except: return "1", "1"

# ====================== 4. AI & AUDIO ENGINE ======================
@st.cache_data(ttl=3600)
def falcon_query(prompt: str, mode: str, chat_history=None) -> str:
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    sys_rules = "You are the Falcon Eye Gate 4 Tactical AI."
    if mode == "Driver Instruction": sys_rules = "Short translator for truck drivers."
    
    conversation = [{"role": "system", "content": sys_rules}]
    if chat_history: conversation.extend(chat_history[-10:])
    conversation.append({"role": "user", "content": prompt})
    try:
        completion = client.chat.completions.create(model="deepseek-chat", messages=conversation, stream=False)
        return completion.choices[0].message.content
    except Exception as e: return f"AI ERROR: {str(e)}"

def play_audio(text, lang='en'):
    tts = gTTS(text=text, lang=lang)
    stream = io.BytesIO()
    tts.write_to_fp(stream)
    st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)

# ====================== 5. AUTHENTICATION ======================
WORKER_DB = {"Precious Akpezi Ojah": "Falcon01", "Bambi": "Nancy", "Mr_Ali": "Ali"}
if not st.session_state.auth:
    st.title("🦅 FALCON EYE | GATE 4 LOGIN")
    u_id = st.selectbox("OPERATOR:", list(WORKER_DB.keys()))
    u_pwd = st.text_input("PASSWORD:", type="password")
    if st.button("AUTHORIZE") and u_pwd == WORKER_DB[u_id]:
        st.session_state.auth, st.session_state.current_worker = True, u_id
        st.rerun()
    st.stop()

# ====================== 6. MASTER UI ======================
dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")
st.markdown(f'<div class="custom-header"><b>Station:</b> {st.session_state.current_worker} | <b>Gate 4:</b> {dubai_time}</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-container"><h1 class="hero-title">FALCON EYE</h1><h2>GATE 4 <span class="status-dot">● OPERATIONAL</span></h2></div>', unsafe_allow_html=True)

tabs = st.tabs(["🛰️ INTEL", "📟 LOGISTICS", "🕵️ AUDIT", "📖 PROTOCOL", "📝 DAILY LOG"])

# --- TAB 1: INTELLIGENCE & INTERCOM ---
with tabs[0]:
    st.subheader("Tactical Intelligence & Driver Intercom")
    if q := st.chat_input("Query Falcon Eye..."):
        st.session_state.messages.append({"role": "user", "content": q})
        ans = falcon_query(q, "Global", st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()
    
    st.divider()
    st.markdown('<div class="intercom-box">', unsafe_allow_html=True)
    langs = {"Arabic": "ar", "Bengali": "bn", "Hindi": "hi", "Urdu": "ur", "Pashto": "ps", "Malayalam": "ml"}
    sel_lang = st.selectbox("Driver Language:", list(langs.keys()))
    if driver_v := speech_to_text(language=langs[sel_lang], start_prompt="👂 LISTEN", key='d_mic'):
        st.info(f"Driver Input: {driver_v}")
    
    msg_to_driver = st.text_input("English Command:")
    if st.button("🔊 TRANSLATE & SPEAK") and msg_to_driver:
        trans = falcon_query(f"Translate to {sel_lang}: {msg_to_driver}", "Driver Instruction")
        st.success(f"Output: {trans}")
        play_audio(trans, langs[sel_lang])
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 2: LOGISTICS (AUTO-INCREMENT + DUPLICATE GUARD) ---
with tabs[1]:
    st.subheader("Logistics Entry Control")
    last_sl, last_gp = get_last_ids("MANUAL PASS")
    try: n_sl = str(int(last_sl) + 1); n_gp = str(int(last_gp) + 1)
    except: n_sl = ""; n_gp = ""

    is_edit = "edit_row_idx" in st.session_state
    if is_edit:
        st.warning(f"EDIT MODE ACTIVE: Row {st.session_state.edit_row_idx}")
        if st.button("❌ EXIT EDIT"): del st.session_state.edit_row_idx; st.rerun()

    dtype = st.radio("Form Type:", ["Manual Gate Pass", "Labour Charge"], horizontal=True)
    with st.form("main_log_form", clear_on_submit=True):
        if dtype == "Manual Gate Pass":
            c1, c2, c3 = st.columns(3)
            f_sl = c1.text_input("SL NO", value=n_sl).upper()
            f_bk = c2.text_input("BOOK NO").upper()
            f_gp = c3.text_input("GATE PASS NO", value=n_gp).upper()
            f_con = st.text_input("CONSIGNEE").upper()
            f_bill = st.text_input("CUSTOMS BILL NO").upper()
            f_desc = st.text_area("CARGO DESCRIPTION").upper()
            c4, c5, c6 = st.columns(3)
            f_unit = c4.text_input("TYPE/UNIT").upper()
            f_cash = c5.text_input("CASH RECEIPT NO").upper()
            f_amt = c6.text_input("AMOUNT").upper()
            f_rem = st.text_input("REMARKS").upper()
            payload = [f_sl, f_bk, f_gp, f_con, f_bill, f_desc, f_unit, f_cash, f_rem, f_amt]
            target, check_id = "MANUAL PASS", f_gp
        else:
            payload = [st.text_input("START").upper(), st.text_input("FINISH").upper(), st.text_input("VOUCHER").upper(), st.text_input("AMOUNT").upper()]
            target, check_id = "LABOUR CHARGE", payload[2]

        if st.form_submit_button("💾 SAVE RECORD"):
            if not is_edit:
                dup, _ = search_logs(check_id, target)
                if dup: st.error("⚠️ DUPLICATE ID!"); st.stop()
            
            if is_edit:
                if update_google_sheet(st.session_state.edit_row_idx, payload, st.session_state.target_sheet):
                    st.success("✅ UPDATED"); del st.session_state.edit_row_idx
            else:
                if save_to_google_sheets(st.session_state.current_worker, payload, target):
                    st.success(f"✅ SYNCED TO {target}")

# --- TAB 3: AUDIT & CORRECTION ---
with tabs[2]:
    st.subheader("Audit & Correction Terminal")
    audit_q = st.text_input("Search ID to Audit/Correct:")
    if st.button("🔍 FETCH DATA"):
        res, ridx = search_logs(audit_q, "MANUAL PASS")
        if res:
            st.session_state.edit_row_idx, st.session_state.target_sheet = ridx, "MANUAL PASS"
            st.success(f"Found Row {ridx}. Recalled to Logistics Tab."); st.json(res)

# --- TAB 4: PROTOCOL (PDF + AUDIO) ---
with tabs[3]:
    st.subheader("Gate 4 Official Protocols")
    col_a, col_b = st.columns([2, 1])
    with col_b:
        if st.button("🔊 PLAY PROTOCOL AUDIO LECTURE"):
            play_audio("Attention Operator. You are at Gate 4. Ensure all Manual Gate Passes are logged with correct Bill numbers. Check cargo descriptions against customs documents.")
    with col_a:
        if os.path.exists("gate_manual.pdf"):
            pdf_viewer("gate_manual.pdf", height=800)
        else:
            st.info("Upload 'gate_manual.pdf' to enable visual protocol.")

# --- TAB 5: DAILY LOGS ---
with tabs[4]:
    day_notes = st.text_area("Security and Operational Notes:")
    if st.button("🚀 SYNC DAILY LOG"):
        if save_to_google_sheets(st.session_state.current_worker, day_notes, "LOG"):
            st.success("Daily Log Synchronized.")
