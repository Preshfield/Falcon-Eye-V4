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
if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = {"New Conversation": []}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "New Conversation"
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
        .hero-divider { height: 3px; width: 80px; background: linear-gradient(90deg, #ADFF2F, transparent); margin: 20px 0; }
        .hero-tagline { color: #ADFF2F !important; font-size: 14px !important; letter-spacing: 5px !important; font-weight: 700 !important; text-transform: uppercase; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        .stTabs [data-baseweb="tab-list"] { background-color: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 12px; }
        .stTabs [aria-selected="true"] { color: #ADFF2F !important; background-color: rgba(173, 255, 47, 0.1) !important; }
        .driver-msg { background: rgba(173, 255, 47, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #ADFF2F; margin: 10px 0; }
        .intercom-box { background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); }
        .custom-header { background: rgba(15, 23, 42, 0.9); padding: 10px 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ADFF2F; }
        </style>
    ''', unsafe_allow_html=True)

local_css("css/style.css")

# ====================== 3. UTILITY ENGINES ======================
def save_to_google_sheets(worker, payload, sheet_name="LOG"):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        now = datetime.now(timezone(timedelta(hours=4)))
        date_s = now.strftime("%d-%m-%Y")
        
        if sheet_name in ["LOG", "FINANCE"]:
            clean_log = str(payload).replace("**", "").replace("###", "").replace("- ", "").strip()
            row_data = [date_s, now.strftime("%H:%M:%S"), "GATE 4", worker, clean_log, "VERIFIED"]
        else:
            row_data = [date_s] + [str(i).upper() for i in payload] + [worker]
            
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"❌ SYNC ERROR: {str(e)}"); return False

def update_google_sheet(row_index, payload, sheet_name):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        now = datetime.now(timezone(timedelta(hours=4)))
        date_s = now.strftime("%d-%m-%Y")
        row_data = [date_s] + [str(i).upper() for i in payload] + [st.session_state.current_worker]
        sheet.update(f"A{row_index}", [row_data])
        return True
    except Exception as e:
        st.error(f"Update Failed: {e}"); return False

def search_logs(query, sheet_name="LOG"):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        all_rows = sheet.get_all_values()
        if not all_rows: return None, None
        header = all_rows[0]
        for idx, row in enumerate(all_rows[1:], start=2): 
            if any(query.upper() in str(c).upper() for c in row):
                return dict(zip(header, row)), idx
        return None, None
    except Exception as e:
        st.error(f"Search Error: {e}"); return None, None

def generate_shift_pdf(worker_name, logs):
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "FALCON EYE - SHIFT HANDOVER REPORT", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"Operator: {worker_name}", ln=True)
    pdf.ln(5); pdf.set_fill_color(173, 255, 47)
    pdf.cell(30, 10, "TIME", 1, 0, 'C', True); pdf.cell(160, 10, "LOG DETAILS", 1, 1, 'C', True)
    pdf.set_font("Arial", '', 9)
    for log in logs:
        pdf.cell(30, 10, str(log.get("TIME", "N/A")), 1)
        pdf.multi_cell(160, 10, str(log.get("LOG DETAILS", "N/A")), 1)
    return pdf.output(dest='S').encode('latin-1')

def get_chat_file(username): return f"memory_{username.replace(' ', '_').lower()}.json"

def save_all_sessions(username, sessions):
    with open(get_chat_file(username), "w") as f: json.dump(sessions, f)

def load_all_sessions(username):
    file_path = get_chat_file(username)
    if os.path.exists(file_path):
        with open(file_path, "r") as f: return json.load(f)
    return {"New Conversation": []}

def digest_manual():
    if os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                return "".join([p.extract_text() for p in PyPDF2.PdfReader(f).pages])
        except: return ""
    return ""

# ====================== 4. AI ENGINES ======================
@st.cache_data(ttl=3600)
def falcon_query(prompt: str, mode: str, chat_history=None) -> str:
    manual_context = digest_manual()
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    if mode == "Gate 4 Protocol":
        sys_rules = f"You are the Falcon Eye Gate 4 Security AI. Use ONLY: {manual_context}."
    elif mode == "Driver Instruction":
        sys_rules = "You are a tactical translator for truck drivers at Dubai DWC. Be short and clear."
    else:
        sys_rules = "Real-Time Intelligence Engine. Current Date: April 23, 2026."
    conversation = [{"role": "system", "content": sys_rules}]
    if chat_history: conversation.extend(chat_history[-10:])
    conversation.append({"role": "user", "content": prompt})
    try:
        completion = client.chat.completions.create(model="deepseek-chat", messages=conversation, stream=False)
        return completion.choices[0].message.content
    except Exception as e: return f"AI ERROR: {str(e)}"

def process_receipt(image_file):
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    base64_image = base64.b64encode(image_file.getvalue()).decode('utf-8')
    try:
        client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-ocr-2",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "Extract Date, Name, Amount, Receipt Number."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}]
        )
        return response.choices[0].message.content
    except Exception as e: return f"Scan Error: {str(e)}"

# ====================== 5. AUTHENTICATION ======================
WORKER_DB = {"Precious Akpezi Ojah": "Falcon01", "Bambi": "Nancy", "Mr_Ali": "Ali"}

if not st.session_state.auth:
    st.title("🦅 FALCON EYE | LOGIN")
    user_identity = st.selectbox("USER:", list(WORKER_DB.keys()))
    user_password = st.text_input("PASSWORD:", type="password")
    if st.button("SIGN IN"):
        if user_password == WORKER_DB[user_identity]:
            st.session_state.auth = True
            st.session_state.current_worker = user_identity
            st.session_state.all_sessions = load_all_sessions(user_identity)
            st.rerun()
    st.stop()

# ====================== 6. DASHBOARD UI ======================
dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")

with st.sidebar:
    st.title("🦅 MISSION LOGS")
    chat_list = list(st.session_state.all_sessions.keys())
    if st.button("➕ START NEW CHAT", use_container_width=True):
        new_id = f"Session {len(chat_list) + 1} ({dubai_time})"
        st.session_state.all_sessions[new_id] = []
        st.session_state.current_chat_id = new_id
        st.rerun()
    st.divider()
    selected_chat = st.radio("History:", chat_list)
    st.session_state.current_chat_id = selected_chat
    st.session_state.messages = st.session_state.all_sessions.get(selected_chat, [])
    if st.button("🔒 LOGOUT", use_container_width=True):
        save_all_sessions(st.session_state.current_worker, st.session_state.all_sessions)
        st.session_state.auth = False
        st.rerun()

st.markdown(f'<div class="custom-header"><b>Station:</b> {st.session_state.current_worker} | {dubai_time}</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-container"><h1 class="hero-title">FALCON EYE</h1><h2>GATE 4 <span class="status-dot">● ONLINE</span></h2><div class="hero-divider"></div><p class="hero-tagline">Tactical AI & Protocol Management</p></div>', unsafe_allow_html=True)

t1, t2, t3, t4, t5 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "🕵️ AUDIT", "📟 SCANNER"])

with t1:
    st.subheader(f"🔍 {st.session_state.current_chat_id}")
    k_mode = st.radio("Intelligence Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    chat_container = st.container(height=350)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]): st.markdown(message["content"])
    if k_query := st.chat_input("Ask Falcon..."):
        st.session_state.messages.append({"role": "user", "content": k_query})
        with chat_container:
            with st.chat_message("user"): st.markdown(k_query)
            with st.chat_message("assistant"):
                response = falcon_query(k_query, k_mode, st.session_state.messages)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.all_sessions[st.session_state.current_chat_id] = st.session_state.messages
        save_all_sessions(st.session_state.current_worker, st.session_state.all_sessions)
    
    st.divider()
    # ====================== TRANSLATION SECTION ======================
    st.markdown('<div class="intercom-box">', unsafe_allow_html=True)
    st.subheader("🚛 Driver Intercom")
    full_langs = {
        "Arabic": "ar", "Bengali": "bn", "English": "en", "Hindi": "hi", 
        "Urdu": "ur", "Pashto": "ps", "Punjabi": "pa", "Malayalam": "ml",
        "Tamil": "ta", "Telugu": "te", "Gujarati": "gu", "Kannada": "kn",
        "Marathi": "mr", "Farsi": "fa", "Turkish": "tr", "Russian": "ru",
        "French": "fr", "Chinese": "zh", "Tagalog": "tl", "Swahili": "sw"
    }
    d_lang = st.selectbox("Select Driver Language:", sorted(list(full_langs.keys())))
    c1, c2 = st.columns([3, 1])
    with c2: driver_v = speech_to_text(language=full_langs[d_lang], start_prompt="👂 LISTEN", key='d_mic')
    if driver_v:
        intent = falcon_query(f"Driver said: {driver_v} in {d_lang}. Translate to English.", "Driver Instruction")
        st.markdown(f'<div class="driver-msg"><b>Driver ({d_lang}):</b> {driver_v}<br><b>Interpretation:</b> {intent}</div>', unsafe_allow_html=True)
    op_voice = speech_to_text(language='en', start_prompt="🎤 TAP TO SPEAK", key='op_mic')
    final_reply = op_voice if op_voice else st.text_input("Type command to driver (English)")
    if st.button("📤 SEND COMMAND"):
        if final_reply:
            trans = falcon_query(f"Translate to {d_lang}: {final_reply}", "Driver Instruction")
            st.success(f"**Replied in {d_lang}:** {trans}")
            try:
                tts = gTTS(text=trans, lang=full_langs[d_lang])
                stream = io.BytesIO(); tts.write_to_fp(stream)
                st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)
            except: st.error("TTS Audio Error.")
    st.markdown('</div>', unsafe_allow_html=True)

with t2:
    st.subheader("📖 Active Protocols")
    if os.path.exists("protocol_lecture.wav.mp3"): st.audio("protocol_lecture.wav.mp3", format="audio/mpeg")
    if os.path.exists("gate_manual.pdf"): pdf_viewer("gate_manual.pdf", height=700)

with t3:
    st.subheader("📋 Security Logs")
    notes = st.text_area("Observations:", key="logs_input")
    if st.button("🚀 SAVE LOG") and notes:
        report = falcon_query(f"Format this observation: {notes}", "Gate 4 Protocol")
        if save_to_google_sheets(st.session_state.current_worker, report): st.success("✅ Synchronized.")

with t4:
    st.subheader("🕵️ Audit Terminal")
    audit_query = st.text_input("Search archives:")
    if st.button("🔍 RUN AUDIT"):
        found, _ = search_logs(audit_query)
        if found: st.table(found)
        else: st.info("No records.")

with t5:
    st.subheader("📟 Digital Ledger Scanner & Logistics")
    captured_image = st.camera_input("Scan Document")
    if captured_image:
        with st.spinner("Scanning..."):
            extracted = process_receipt(captured_image)
            final_entry = st.text_area("Edit scan:", value=extracted.upper(), height=150)
            if st.button("✅ SYNC TO FINANCE"):
                save_to_google_sheets(st.session_state.current_worker, final_entry, "FINANCE")

    st.divider()
    st.write("### 🛠️ Logistics Correction Terminal")
    with st.expander("RECALL & FIX ERRORS"):
        search_tab = st.selectbox("Select Sheet:", ["MANUAL PASS", "LABOUR CHARGE", "OFFICIAL REPORT"])
        recall_id = st.text_input("Enter ID (Gate Pass/Receipt No):")
        if st.button("🔍 FETCH RECORD"):
            record, row_idx = search_logs(recall_id, search_tab)
            if record:
                st.session_state.edit_row_idx, st.session_state.target_sheet = row_idx, search_tab
                st.success(f"Record found at Row {row_idx}. Correct below."); st.json(record)
            else: st.error("No record found.")

    st.divider()
    is_editing = "edit_row_idx" in st.session_state
    if is_editing:
        st.warning(f"⚠️ EDITING Row {st.session_state.edit_row_idx}")
        if st.button("❌ CANCEL EDIT"): del st.session_state.edit_row_idx; st.rerun()

    doc_type = st.radio("Form Type:", ["Manual Gate Pass", "Labour Charge", "Official Report"], horizontal=True)
    with st.form("logistics_form", clear_on_submit=True):
        if doc_type == "Manual Gate Pass":
            c1, c2, c3 = st.columns(3)
            payload = [c1.text_input("SL NO").upper(), c2.text_input("BOOK NO").upper(), c3.text_input("GATE PASS NO").upper(), 
                       st.text_input("CONSIGNEE").upper(), st.text_input("CUSTOMS BILL NO").upper(), st.text_area("DESCRIPTION").upper(),
                       st.text_input("UNIT").upper(), st.text_input("CASH NO").upper(), st.text_input("REMARKS").upper(), st.text_input("AMOUNT").upper()]
            sheet_target = "MANUAL PASS"
        elif doc_type == "Labour Charge":
            c1, c2, c3 = st.columns(3)
            payload = [c1.text_input("START").upper(), c2.text_input("FINISH").upper(), c3.text_input("RECEIPT BOOK").upper(),
                       st.text_input("VOUCHER").upper(), st.text_input("HOURS").upper(), st.text_input("LABOURS").upper(),
                       st.selectbox("FORKLIFT", ["YES", "NO"]), st.text_input("AMOUNT").upper(), st.text_input("FROM").upper(), st.text_input("REMARKS").upper()]
            sheet_target = "LABOUR CHARGE"
        else:
            payload = [st.text_input("BOOK NO").upper(), st.text_input("GATE PASS NO").upper(), st.text_input("CONSIGNEE").upper(),
                       st.text_input("BILL NO").upper(), st.text_input("REMARKS").upper(), st.text_input("AMOUNT").upper(), st.text_area("REASON").upper()]
            sheet_target = "OFFICIAL REPORT"

        if st.form_submit_button("💾 OVERWRITE" if is_editing else "🚀 SYNC TO DATABASE"):
            if is_editing:
                if update_google_sheet(st.session_state.edit_row_idx, payload, st.session_state.target_sheet):
                    st.success("✅ CORRECTED!"); del st.session_state.edit_row_idx
            else:
                if save_to_google_sheets(st.session_state.current_worker, payload, sheet_target):
                    st.success(f"✅ SAVED TO {sheet_target}")
