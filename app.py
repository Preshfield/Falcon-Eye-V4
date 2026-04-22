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

# Global Fallbacks to prevent crashes on first run
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
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(10px);
            padding: 60px 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            border: 1px solid rgba(173, 255, 47, 0.3);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
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

# ====================== 3. ENGINES ======================
def save_to_google_sheets(worker, log_text, sheet_name="LOG"):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        clean_log = log_text.replace("**", "").replace("###", "").replace("- ", "").strip()
        now = datetime.now(timezone(timedelta(hours=4)))
        row_data = [now.strftime("%d-%m-%Y"), now.strftime("%H:%M:%S"), "GATE 4", worker, clean_log, "VERIFIED"]
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Cloud Sync Unavailable: {e}"); return False

def search_logs(query):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Falcon_Eye_Database").worksheet("LOG")
        all_rows = sheet.get_all_values()
        if not all_rows: return []
        header = all_rows[0]
        return [dict(zip(header, row)) for row in all_rows[1:] if any(query.lower() in str(c).lower() for c in row)]
    except Exception as e:
        st.error(f"Audit Search Error: {e}"); return []

# FIXED SCANNER: Now targets DeepSeek OCR vision model to solve ccc.jpeg error
def process_receipt(image_file):
    api_key = st.secrets.get("DEEPSEEK_API_KEY") # Fixes KeyError from dppp.jpeg
    if not api_key:
        return "System Error: DEEPSEEK_API_KEY missing in Secrets."
        
    base64_image = base64.b64encode(image_file.getvalue()).decode('utf-8')
    try:
        client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-vl-7b-chat", # Paid DeepSeek Vision Model
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "Extract details: Date, Name, Amount, and Receipt Number."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]}],
        )
        return response.choices[0].message.content
    except Exception as e: return f"Vision Error: {str(e)}"

def generate_shift_pdf(worker_name, logs):
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "FALCON EYE - SHIFT HANDOVER REPORT", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(190, 10, f"Station: GATE 4 | Date: {datetime.now().strftime('%d-%m-%Y')}", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, f"Operator: {worker_name}", ln=True); pdf.ln(5)
    pdf.set_fill_color(173, 255, 47); pdf.set_font("Arial", 'B', 10)
    pdf.cell(30, 10, "TIME", 1, 0, 'C', True); pdf.cell(160, 10, "LOG DETAILS", 1, 1, 'C', True)
    pdf.set_font("Arial", '', 9)
    for log in logs:
        log_txt = str(log.get("LOG DETAILS", "N/A")).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(30, 10, str(log.get("TIME", "N/A")), 1)
        pdf.multi_cell(160, 10, log_txt, 1)
    return pdf.output(dest='S').encode('latin-1')

def get_chat_file(username):
    return f"memory_{username.replace(' ', '_').lower()}.json"

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

# PAID DEEPSEEK CORE
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
        sys_rules = "Real-Time Intelligence Engine. Current Date: April 22, 2026."
    
    conversation = [{"role": "system", "content": sys_rules}]
    if chat_history: conversation.extend(chat_history[-10:])
    conversation.append({"role": "user", "content": prompt})
    
    try:
        completion = client.chat.completions.create(model="deepseek-chat", messages=conversation, stream=False)
        return completion.choices[0].message.content
    except Exception as e: return f"DEEPSEEK ERROR: {str(e)}"

# ====================== 4. AUTHENTICATION ======================
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

# ====================== 5. DASHBOARD UI (IRONCLAD VERSION) ======================
dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")

if st.session_state.get("auth"):
    with st.sidebar:
        st.title("🦅 MISSION LOGS")
        
        # --- SHIELDED DATA FETCHING: Fixes AttributeError in di.jpeg ---
        sessions_data = st.session_state.get("all_sessions")
        if not isinstance(sessions_data, dict):
            sessions_data = {"New Conversation": []}
            st.session_state.all_sessions = sessions_data
        
        chat_list = list(sessions_data.keys())
        
        if st.button("➕ START NEW CHAT", use_container_width=True):
            new_id = f"Session {len(chat_list) + 1} ({dubai_time})"
            st.session_state.all_sessions[new_id] = []
            st.session_state.current_chat_id = new_id
            st.rerun()

        st.divider()
        
        # --- SHIELDED SELECTION ---
        current_id = st.session_state.get("current_chat_id", "New Conversation")
        if current_id not in chat_list:
            current_id = chat_list[0] if chat_list else "New Conversation"
        
        try:
            curr_index = chat_list.index(current_id)
        except (ValueError, IndexError):
            curr_index = 0

        selected_chat = st.radio("History:", chat_list, index=curr_index)
        st.session_state.current_chat_id = selected_chat
        
        # SHIELDED MESSAGE LOAD: Fixes rrr.jpeg crash
        st.session_state.messages = sessions_data.get(selected_chat, [])

        st.divider()
        if st.button("🔒 LOGOUT", type="secondary", use_container_width=True):
            save_all_sessions(st.session_state.current_worker, st.session_state.all_sessions)
            st.session_state.auth = False
            st.rerun()

# Main Header
st.markdown(f'<div class="custom-header"><b>Station Active:</b> {st.session_state.current_worker} | {dubai_time}</div>', unsafe_allow_html=True)

st.markdown('''
    <div class="hero-container">
        <h1 class="hero-title">FALCON EYE</h1>
        <h2 class="hero-subtitle">GATE 4 <span class="status-dot">● ONLINE</span></h2>
        <div class="hero-divider"></div>
        <p class="hero-tagline">Tactical AI Intelligence & Protocol Management</p>
    </div>
''', unsafe_allow_html=True)

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
    st.markdown('<div class="intercom-box">', unsafe_allow_html=True)
    st.subheader("🚛 Driver Intercom")
    full_langs = {
        "Arabic": "ar", "Bengali": "bn", "Chinese (Mandarin)": "zh-cn",
        "English": "en", "Hindi": "hi", "Malayalam": "ml", "Pashto": "ps", 
        "Punjabi": "pa", "Russian": "ru", "Tagalog": "tl", "Urdu": "ur"
    }
    sorted_langs = dict(sorted(full_langs.items()))
    d_lang = st.selectbox("Select Driver Language:", list(sorted_langs.keys()))

    c1, c2 = st.columns([3, 1])
    with c1: st.write(f"🎤 **Listen to {d_lang} Driver**")
    with c2: driver_v = speech_to_text(language=full_langs[d_lang], start_prompt="👂 LISTEN", key='d_mic')

    if driver_v:
        intent = falcon_query(f"The driver said: {driver_v} in {d_lang}. Translate to English.", "Driver Instruction")
        st.markdown(f'<div class="driver-msg"><b>Driver:</b> {driver_v}<br><b>AI Interpretation:</b> {intent}</div>', unsafe_allow_html=True)

    st.write("💬 **Reply to Driver**")
    op_voice = speech_to_text(language='en', start_prompt="🎤 TAP TO SPEAK REPLY", key='op_mic')
    d_reply_text = st.text_input("Type command here", key="driver_reply_box")
    final_reply = op_voice if op_voice else d_reply_text

    if st.button("📤 SEND COMMAND TO DRIVER"):
        if final_reply:
            with st.spinner("Translating..."):
                trans = falcon_query(f"Translate to {d_lang}: {final_reply}", "Driver Instruction")
                st.success(f"**Replied in {d_lang}:** {trans}")
                tts = gTTS(text=trans, lang=full_langs[d_lang])
                stream = io.BytesIO(); tts.write_to_fp(stream)
                st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t2:
    st.subheader("📖 Active Protocols")
    st.markdown("### 🎧 Protocol Audio Briefing")
    audio_path = "protocol_lecture.wav.mp3"
    if os.path.exists(audio_path):
        st.audio(audio_path, format="audio/mpeg")
    else:
        st.info("📢 Audio briefing file not found.")
    st.divider()
    st.markdown("### 📜 Standard Operating Procedures")
    if os.path.exists("gate_manual.pdf"):
        pdf_viewer("gate_manual.pdf", height=700)
    else:
        st.warning("Manual file 'gate_manual.pdf' not found.")

with t3:
    st.subheader("📋 Security Logs")
    notes = st.text_area("Observations:", key="logs_input")
    if st.button("🚀 SAVE LOG"):
        if notes:
            with st.spinner("Processing..."):
                report = falcon_query(f"Format this observation: {notes}", "Gate 4 Protocol")
                st.code(report)
                if save_to_google_sheets(st.session_state.current_worker, report): st.success("✅ Synchronized.")

with t4:
    st.subheader("🕵️ Supervisor Audit Terminal")
    audit_query = st.text_input("Search archives (Plate No, Name):")
    if st.button("🔍 RUN AUDIT"):
        found = search_logs(audit_query)
        if found: st.table(found)
        else: st.info("No matching records found.")
    
    st.divider()
    st.subheader("📋 Shift Handover")
    if st.button("📄 GENERATE HANDOVER PDF"):
        all_data = search_logs(st.session_state.current_worker)
        if all_data:
            pdf_data = generate_shift_pdf(st.session_state.current_worker, all_data[-10:])
            st.download_button("📥 Download Handover PDF", pdf_data, f"Handover_{st.session_state.current_worker}.pdf", "application/pdf")

with t5:
    st.subheader("📟 Digital Ledger Scanner")
    captured_image = st.camera_input("Scan Document")
    if captured_image:
        with st.spinner("Processing with DeepSeek Vision..."):
            extracted = process_receipt(captured_image)
            st.write("### Extracted Data")
            final_entry = st.text_area("Edit if needed:", value=extracted, height=200)
            if st.button("✅ SYNC TO FINANCE"):
                if save_to_google_sheets(st.session_state.current_worker, final_entry, "FINANCE"):
                    st.success("Logged to Finance database.")
