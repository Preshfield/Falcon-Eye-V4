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
from fpdf import FPDF

# ====================== 1. CRITICAL INITIALIZATION ======================
st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")

if "auth" not in st.session_state:
    st.session_state.auth = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_worker" not in st.session_state:
    st.session_state.current_worker = "Guest"

# ====================== 2. FULL RESTORED CSS ======================
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    st.markdown('''
        <style>
        .stApp { background: radial-gradient(circle at top right, #0f172a, #020617); color: #f8fafc; }
        .hero-container {
            background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(10px);
            padding: 60px 40px; border-radius: 20px; margin-bottom: 30px;
            border: 1px solid rgba(173, 255, 47, 0.3); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        .hero-title { color: #ffffff !important; font-size: 72px !important; font-weight: 900 !important; letter-spacing: -3px !important; }
        .status-dot { color: #ADFF2F; font-weight: 800; text-shadow: 0 0 15px #ADFF2F; animation: pulse 2s infinite; }
        .custom-header { background: rgba(15, 23, 42, 0.9); padding: 10px 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ADFF2F; }
        .intercom-box { background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); }
        </style>
    ''', unsafe_allow_html=True)

local_css("css/style.css")

# ====================== 3. UTILITY ENGINES ======================
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
        for idx, row in enumerate(all_rows[1:][-50:], start=max(2, len(all_rows)-49)): 
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

# ====================== 4. AI ENGINES ======================
@st.cache_data(ttl=3600)
def falcon_query(prompt: str, mode: str, chat_history=None) -> str:
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    sys_rules = "Tactical Security AI Gate 4 Dubai DWC."
    if mode == "Driver Instruction": sys_rules = "Translator for truck drivers. Short & clear."
    
    conversation = [{"role": "system", "content": sys_rules}]
    if chat_history: conversation.extend(chat_history[-10:])
    conversation.append({"role": "user", "content": prompt})
    try:
        completion = client.chat.completions.create(model="deepseek-chat", messages=conversation, stream=False)
        return completion.choices[0].message.content
    except Exception as e: return f"AI ERROR: {str(e)}"

# ====================== 5. AUTHENTICATION ======================
WORKER_DB = {"Precious Akpezi Ojah": "Falcon01", "Bambi": "Nancy", "Mr_Ali": "Ali"}
if not st.session_state.auth:
    st.title("🦅 FALCON EYE | LOGIN")
    user_id = st.selectbox("USER:", list(WORKER_DB.keys()))
    pwd = st.text_input("PASSWORD:", type="password")
    if st.button("SIGN IN") and pwd == WORKER_DB[user_id]:
        st.session_state.auth, st.session_state.current_worker = True, user_id
        st.rerun()
    st.stop()

# ====================== 6. UI DASHBOARD ======================
dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")
st.markdown(f'<div class="custom-header"><b>Station:</b> {st.session_state.current_worker} | {dubai_time}</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-container"><h1 class="hero-title">FALCON EYE</h1><h2>GATE 4 <span class="status-dot">● ONLINE</span></h2><div class="hero-divider"></div><p class="hero-tagline">Tactical AI & Protocol Management</p></div>', unsafe_allow_html=True)

t1, t2, t3, t4, t5 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "🕵️ AUDIT", "📟 SCANNER"])

with t1:
    st.subheader("Intelligence Terminal")
    if k_query := st.chat_input("Ask Falcon..."):
        st.session_state.messages.append({"role": "user", "content": k_query})
        ans = falcon_query(k_query, "Global", st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()
    
    st.divider()
    st.markdown('<div class="intercom-box">', unsafe_allow_html=True)
    st.subheader("🚛 Driver Intercom")
    full_langs = {"Arabic": "ar", "Bengali": "bn", "English": "en", "Hindi": "hi", "Urdu": "ur", "Pashto": "ps", "Malayalam": "ml"}
    d_lang = st.selectbox("Driver Language:", sorted(list(full_langs.keys())))
    
    col_mic1, col_mic2 = st.columns(2)
    with col_mic1:
        driver_v = speech_to_text(language=full_langs[d_lang], start_prompt="👂 LISTEN TO DRIVER", key='d_mic')
    with col_mic2:
        operator_v = speech_to_text(language='en-US', start_prompt="🎤 SPEAK TO DRIVER", key='o_mic')

    if driver_v:
        intent = falcon_query(f"Translate to English: {driver_v}", "Driver Instruction")
        st.info(f"DRIVER: {driver_v}\n\nINTEL: {intent}")

    op_cmd = st.text_input("Type response to driver (English):", value=operator_v if operator_v else "")
    
    if st.button("📤 SEND TO DRIVER") and op_cmd:
        trans = falcon_query(f"Translate to {d_lang}: {op_cmd}", "Driver Instruction")
        st.success(f"Sent: {trans}")
        tts = gTTS(text=trans, lang=full_langs[d_lang])
        stream = io.BytesIO(); tts.write_to_fp(stream)
        st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t2:
    if os.path.exists("gate_manual.pdf"): pdf_viewer("gate_manual.pdf", height=700)

with t3:
    notes = st.text_area("Observations:")
    if st.button("🚀 SAVE LOG") and notes:
        if save_to_google_sheets(st.session_state.current_worker, notes, "LOG"): st.success("✅ Logged.")

with t4:
    aq = st.text_input("Search Database Records:")
    if st.button("🔍 RUN AUDIT"):
        res, _ = search_logs(aq, "MANUAL PASS")
        if res: st.table(res)
        else: st.info("No matching records found.")

with t5:
    st.subheader("📟 Logistics Command Center")
    
    # 1. EXPRESS ENTRY BAR
    quick_code = st.text_input("⚡ EXPRESS ENTRY (e.g. PASS 1234):").upper()
    
    # 2. FREQUENT CONSIGNEE BUTTONS
    st.write("📌 Frequent Consignees:")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    freq_con = ""
    if col_f1.button("DHL"): freq_con = "DHL EXPRESS"
    if col_f2.button("FEDEX"): freq_con = "FEDEX LOGISTICS"
    if col_f3.button("ARAMEX"): freq_con = "ARAMEX DUBAI"
    if col_f4.button("PERSONAL"): freq_con = "PERSONAL EFFECTS"

    # Auto-Increment Logic
    last_sl, last_gp = get_last_ids("MANUAL PASS")
    try: 
        next_sl = str(int(last_sl) + 1)
        next_gp = str(int(last_gp) + 1)
    except: 
        next_sl = ""; next_gp = ""

    # Parse Express Code
    if "PASS" in quick_code:
        next_gp = quick_code.replace("PASS", "").strip()

    is_editing = "edit_row_idx" in st.session_state
    dtype = st.radio("Form:", ["Manual Gate Pass", "Labour Charge", "Official Report"], horizontal=True)

    with st.form("main_form", clear_on_submit=True):
        if dtype == "Manual Gate Pass":
            c1, c2, c3 = st.columns(3)
            f_sl = c1.text_input("SL NO", value=next_sl).upper()
            f_bk = c2.text_input("BOOK NO").upper()
            f_gp = c3.text_input("GATE PASS NO", value=next_gp).upper()
            f_con = st.text_input("CONSIGNEE", value=freq_con).upper()
            f_bill = st.text_input("CUSTOMS BILL NO").upper()
            f_desc = st.text_area("CARGO DESCRIPTION").upper()
            c4, c5, c6 = st.columns(3)
            f_unit = c4.text_input("TYPE/UNIT").upper()
            f_cash = c5.text_input("CASH RECEIPT NO").upper()
            f_amt = c6.number_input("AMOUNT", min_value=0.0, format="%.2f")
            f_rem = st.text_input("REMARKS").upper()
            payload = [f_sl, f_bk, f_gp, f_con, f_bill, f_desc, f_unit, f_cash, f_rem, str(f_amt)]
            target, check_id = "MANUAL PASS", f_gp
        
        elif dtype == "Labour Charge":
            c1, c2, c3 = st.columns(3)
            # Time Pickers for Data Guard
            t_start = c1.time_input("START", value=datetime.now().time())
            t_end = c2.time_input("FINISH", value=datetime.now().time())
            payload = [t_start.strftime("%H:%M"), t_end.strftime("%H:%M"), c3.text_input("BOOK").upper(),
                       st.text_input("VOUCHER").upper(), st.text_input("HRS").upper(), st.text_input("LABOURS").upper(),
                       st.selectbox("FORKLIFT", ["YES", "NO"]), st.number_input("AMOUNT", min_value=0.0), st.text_input("FROM").upper(), st.text_input("REMARKS").upper()]
            target, check_id = "LABOUR CHARGE", payload[3]
        else:
            payload = [st.text_input("BOOK").upper(), st.text_input("GP").upper(), st.text_input("CONSIGNEE").upper(),
                       st.text_input("BILL").upper(), st.text_input("REMARKS").upper(), st.number_input("AMOUNT", min_value=0.0), st.text_area("REASON").upper()]
            target, check_id = "OFFICIAL REPORT", payload[1]

        if st.form_submit_button("💾 OVERWRITE" if is_editing else "🚀 SYNC TO DATABASE"):
            if not is_editing:
                # 4. DUPLICATE CHECK (Last 50 entries)
                dup, _ = search_logs(check_id, target)
                if dup: 
                    st.error(f"⚠️ DUPLICATE ENTRY DETECTED! Gate Pass {check_id} is already in the ledger.")
                    st.stop()
            
            success = update_google_sheet(st.session_state.edit_row_idx, payload, target) if is_editing else save_to_google_sheets(st.session_state.current_worker, payload, target)
            if success:
                st.success("✅ SYNCED SUCCESSFULLY")
                if is_editing: del st.session_state.edit_row_idx; st.rerun()

    with st.expander("🛠️ CORRECTION TERMINAL"):
        rid = st.text_input("ID to recall:")
        if st.button("🔍 FETCH"):
            rec, row_idx = search_logs(rid, "MANUAL PASS")
            if rec:
                st.session_state.edit_row_idx, st.session_state.target_sheet = row_idx, "MANUAL PASS"
                st.success(f"Recalled Row {row_idx}. Ready to edit."); st.json(rec)
