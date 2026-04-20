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
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")
local_css("css/style.css?v=1.1")

# ====================== GOOGLE SHEETS ENGINE ======================
def save_to_google_sheets(worker, log_text):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("Falcon_Eye_Database").worksheet("LOG")
        dubai_now = datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([dubai_now, worker, log_text])
        return True
    except Exception as e:
        st.error(f"Google Sheet Error: {e}")
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

@st.cache_data(ttl=3600)
def falcon_query(prompt: str, mode: str) -> str:
    manual_context = digest_manual()
    client = openai.OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

    if mode == "Gate 4 Protocol":
        sys_rules = f"You are a Gate Security AI. Use ONLY this manual: {manual_context}. Be firm and precise."
    elif mode == "Driver Instruction":
        sys_rules = "Short, clear instructions for truck drivers. Professional translator."
    else:
        sys_rules = "Real-Time Intelligence Engine. Date: April 21, 2026."

    conversation = [{"role": "system", "content": sys_rules}]
    for msg in st.session_state.get("messages", [])[-10:]:
        conversation.append({"role": msg["role"], "content": msg["content"]})
    conversation.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(model="deepseek-chat", messages=conversation, stream=False)
        return completion.choices[0].message.content
    except Exception as e:
        return f"FALCON ENGINE ERROR: {str(e)}"

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

# --- REFINED HERO DASHBOARD ---
# --- REFINED HERO DASHBOARD ---
st.markdown('''
    <div class="hero-container">
        <h1 class="hero-title">FALCON EYE</h1>
        <h2 class="hero-subtitle">GATE 4 <span class="status-dot">● ONLINE</span></h2>
        <div class="hero-divider"></div>
        <p class="hero-tagline">Tactical AI Intelligence & Protocol Management</p>
    </div>
''', unsafe_allow_html=True)

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
