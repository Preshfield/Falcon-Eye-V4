import streamlit as st
import os, io, json
from datetime import datetime, timedelta, timezone
from gtts import gTTS
import PyPDF2
import openai
import gspread
from google.oauth2.service_account import Credentials
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer

# 1. LOAD EXTERNAL CSS

  # 1. LOAD EXTERNAL AND INTERNAL CSS
def local_css(file_name):
    # This part keeps your existing style.css working
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    
    # This part FORCES the Tech HQ look even if the file fails
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
        
        /* Tactical Tabs */
        .stTabs [data-baseweb="tab-list"] { background-color: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 12px; }
        .stTabs [aria-selected="true"] { color: #ADFF2F !important; background-color: rgba(173, 255, 47, 0.1) !important; }
        </style>
    ''', unsafe_allow_html=True)

st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")
local_css("css/style.css")

# ... (Authentication and Logic remain exactly the same)

# --- REFINED HERO DASHBOARD ---
st.markdown('''
    <div class="hero-container">
        <h1 class="hero-title">FALCON EYE</h1>
        <h2 class="hero-subtitle">GATE 4 <span class="status-dot">● ONLINE</span></h2>
        <div class="hero-divider"></div>
        <p class="hero-tagline">Tactical AI Intelligence & Protocol Management</p>
    </div>
''', unsafe_allow_html=True)

# ====================== GOOGLE SHEETS ENGINE ======================
# ====================== OFFICE-STANDARD LOGGING ENGINE ======================
# ====================== OFFICE-STANDARD LOGGING ENGINE ======================
def save_to_google_sheets(worker, log_text):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Falcon_Eye_Database").worksheet("LOG")
        
        # --- CLEAN TEXT FOR EXCEL ---
        # This removes the ** bold markers and other markdown clutter
        clean_log = log_text.replace("**", "").replace("###", "").replace("- ", "").strip()
        
        # Dubai Timestamping
        now = datetime.now(timezone(timedelta(hours=4)))
        date_str = now.strftime("%d-%m-%Y")
        time_str = now.strftime("%H:%M:%S")
        
        # --- OFFICE FORMAT ROW ---
        row_data = [
            date_str, 
            time_str, 
            "GATE 4", 
            worker, 
            clean_log, 
            "VERIFIED"
        ]
        
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Data Synchronization Error: {e}")
        return False
# ====================== PERSISTENT MEMORY ENGINE ======================
def get_chat_file(username):
    return f"memory_{username.replace(' ', '_').lower()}.json"

def save_chat_history(username, messages):
    with open(get_chat_file(username), "w") as f:
        json.dump(messages, f)

def load_chat_history(username):
    file_path = get_chat_file(username)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

# ====================== SYSTEM ENGINES ======================
def digest_manual():
    if os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "".join([page.extract_text() for page in reader.pages])
        except: return ""
    return ""

# --- DUAL-MODE OPERATOR REPLY (TEXT OR VOICE) ---
    st.write("💬 **Reply to Driver**")
    
    # 1. Voice Reply Option
    operator_v = speech_to_text(language='en', start_prompt="🎤 VOICE REPLY", key='op_mic')
    
    # 2. Text Reply Option (Keeping your original box)
    d_reply = st.text_input("Or type command here:", key="driver_reply_box")
    
    # Logic to handle whichever input you use (Voice or Text)
    final_input = operator_v if operator_v else d_reply

    if st.button("📤 SEND COMMAND TO DRIVER"):
        if final_input:
            with st.spinner("Translating..."):
                # The AI converts your English (Voice or Text) to the Driver's Language
                trans = falcon_query(f"Translate to {d_lang}: {final_input}", "Driver Instruction")
                
                st.success(f"**Translated ({d_lang}):** {trans}")
                
                # Generate and play the audio for the driver
                tts = gTTS(text=trans, lang=full_langs[d_lang])
                stream = io.BytesIO()
                tts.write_to_fp(stream)
                st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)
        else:
            st.warning("Please provide a voice command or type a message.")
# ====================== AUTHENTICATION ======================
WORKER_DB = {"Precious Akpezi Ojah": "Falcon01", "Bambi": "Nancy", "Mr_Ali": "Ali"}

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🦅 FALCON EYE | LOGIN")
    user_identity = st.selectbox("USER:", list(WORKER_DB.keys()))
    user_password = st.text_input("PASSWORD:", type="password")
    if st.button("SIGN IN"):
        if user_password == WORKER_DB[user_identity]:
            st.session_state.auth = True
            st.session_state.current_worker = user_identity
            st.session_state.messages = load_chat_history(user_identity)
            st.rerun()
    st.stop()

# ====================== DASHBOARD UI ======================
if st.sidebar.button("🔒 LOGOUT", type="secondary"):
    save_chat_history(st.session_state.current_worker, st.session_state.messages)
    st.session_state.auth = False
    st.rerun()

dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")
st.markdown(f'<div class="custom-header"><b>Station Active:</b> {st.session_state.current_worker} | {dubai_time}</div>', unsafe_allow_html=True)


t1, t2, t3, t4 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "🕵️ AUDIT"])

with t1:
    st.subheader("🔍 Knowledge Scan")
    
    # --- RESTORED BRAIN SELECTION ---
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
                response = falcon_query(k_query, k_mode)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        save_chat_history(st.session_state.current_worker, st.session_state.messages)

    st.divider()
    st.markdown('<div class="intercom-box">', unsafe_allow_html=True)
    st.subheader("🚛 Driver Intercom")
    full_langs = {"Bengali": "bn", "Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
    d_lang = st.selectbox("Select Driver Language:", list(full_langs.keys()))
    
    c1, c2 = st.columns([3, 1])
    with c1: st.write(f"🎤 **Listen to {d_lang} Driver**")
    with c2: driver_v = speech_to_text(language=full_langs[d_lang], start_prompt="👂 LISTEN", key='d_mic')

    if driver_v:
        intent = falcon_query(f"The driver said: {driver_v} in {d_lang}. Translate to English.", "Driver Instruction")
        st.markdown(f'<div class="driver-msg"><b>Driver:</b> {driver_v}<br><b>AI Interpretation:</b> {intent}</div>', unsafe_allow_html=True)

    st.write("💬 **Reply to Driver**")
    d_reply = st.text_input("Type command here", key="driver_reply_box")
    if st.button("📤 SEND COMMAND TO DRIVER"):
        if d_reply:
            with st.spinner("Translating..."):
                trans = falcon_query(f"Translate to {d_lang}: {d_reply}", "Driver Instruction")
                st.success(f"**Replied in {d_lang}:** {trans}")
                tts = gTTS(text=trans, lang=full_langs[d_lang])
                stream = io.BytesIO()
                tts.write_to_fp(stream)
                st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t2:
    st.subheader("📖 Active Protocols & Training")
    st.markdown("#### 🎧 Protocol Audio Lecture")
    audio_file = "protocol_lecture.wav.mp3"
    if os.path.exists(audio_file):
        st.audio(audio_file, format="audio/mpeg")
    else:
        st.error(f"⚠️ System Error: File '{audio_file}' not detected.")
    
    st.divider()
    st.markdown("#### 📄 Gate 4 Manual")
    pdf_path = "gate_manual.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button(label="📥 Download Protocol Manual (PDF)", data=f, file_name="Gate_4_Security_Manual.pdf", mime="application/pdf")
        pdf_viewer(pdf_path, height=700)
    else:
        st.error("Protocol Manual (gate_manual.pdf) not found.")

with t3:
    st.subheader("📋 Security Mission Logs")
    notes = st.text_area("Observations:", key="logs")
    if st.button("🚀 GENERATE & SAVE LOG"):
        if notes:
            with st.spinner("Syncing..."):
                report = falcon_query(f"Format: {notes}", "Gate 4 Protocol")
                st.code(report)
                if save_to_google_sheets(st.session_state.current_worker, report):
                    st.success("✅ Log Synchronized to Google Sheet.")

with t4:
    st.subheader("🕵️ Supervisor Audit Terminal")
    audit_query = st.text_input("Enter Plate/Name:")
    if st.button("🔍 RUN DEEP AUDIT"):
        st.info("Scanning database archives...")
