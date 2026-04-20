import streamlit as st
import os, io, base64
from datetime import datetime, timedelta, timezone
from duckduckgo_search import DDGS
from gtts import gTTS
import PyPDF2
import openai
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer

# 1. LOAD EXTERNAL CSS
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")
local_css("css/style.css")

# --- INITIALIZE MEMORY ---
if "messages" not in st.session_state:
    st.session_state.messages = []

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
        sys_rules = "Short, clear safety instructions and translations for truck drivers. Professional translator."
    elif mode == "Audit Mode":
        sys_rules = "Forensic Auditor. Analyze logs for plate numbers, names, or reoccurring incidents."
    else:
        sys_rules = "Real-Time Intelligence Engine. Date: April 20, 2026. Site security focus."

    # MEMORY INTEGRATION
    conversation = [{"role": "system", "content": sys_rules}]
    for msg in st.session_state.messages[-5:]:
        conversation.append({"role": msg["role"], "content": msg["content"]})
    conversation.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(model="deepseek-chat", messages=conversation, stream=False)
        return completion.choices[0].message.content
    except Exception as e:
        return f"FALCON ENGINE ERROR: {str(e)}"

def save_log(report_text):
    with open("security_logs.txt", "a", encoding="utf-8") as f:
        f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{report_text}\n{'='*50}\n")

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
            st.rerun()
    st.stop()

# ====================== DASHBOARD UI ======================

if st.sidebar.button("🔒 LOGOUT", type="secondary"):
    st.session_state.auth = False
    st.rerun()

dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")
st.markdown(f'<div class="custom-header"><b>Station Active:</b> {st.session_state.current_worker} | {dubai_time}</div>', unsafe_allow_html=True)

st.markdown("""
    <div style='text-align: left; padding: 40px 0 20px 0;'>
        <h1 class='falcon-title'>FALCON EYE</h1>
        <h2 class='gate-sub'>GATE 4 <span style='font-size:20px; color:#22d3ee; vertical-align:middle;'>● ONLINE</span></h2>
        <p style='color: #94a3b8; font-size: 14px; letter-spacing: 5px; font-weight: bold; text-transform: uppercase;'>
            Tactical AI Intelligence & Protocol Management
        </p>
    </div>
""", unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "🕵️ AUDIT"])

with t1:
    st.subheader("🔍 Knowledge Scan")
    k_mode = st.radio("Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if k_query := st.chat_input("Ask Falcon anything..."):
        st.session_state.messages.append({"role": "user", "content": k_query})
        with st.chat_message("user"): st.markdown(k_query)
        with st.chat_message("assistant"):
            response = falcon_query(k_query, k_mode)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    st.divider()

    # --- DRIVER INTERCOM (TRANSLATOR ADDED) ---
    st.markdown('<div class="intercom-box">', unsafe_allow_html=True)
    st.subheader("🚛 Driver Intercom")
    
    full_langs = {"Bengali": "bn", "Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
    d_lang = st.selectbox("Select Driver Language:", list(full_langs.keys()))
    
    c1, c2 = st.columns([3, 1])
    with c1: st.write(f"🎤 **Listen to {d_lang} Driver**")
    with c2: driver_v = speech_to_text(language=full_langs[d_lang], start_prompt="👂 LISTEN", key='d_mic')

    if driver_v:
        intent = falcon_query(f"The driver said this in {d_lang}: {driver_v}. Translate to English and explain intent.", "Driver Instruction")
        st.markdown(f'<div class="driver-msg"><b>Driver:</b> {driver_v}<br><b>AI Interpretation:</b> {intent}</div>', unsafe_allow_html=True)

    d_reply = st.text_input("Reply to driver (translated to their language)...", key="driver_reply_input")
    if d_reply:
        trans = falcon_query(f"Translate this command to {d_lang}: {d_reply}", "Driver Instruction")
        st.success(f"**AI Translation ({d_lang}):** {trans}")
        tts = gTTS(text=trans, lang=full_langs[d_lang])
        stream = io.BytesIO()
        tts.write_to_fp(stream)
        st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t2:
    st.subheader("Active Protocols")
    if os.path.exists("gate_manual.pdf"):
        pdf_viewer("gate_manual.pdf", height=700)

with t3:
    st.subheader("📋 Security Mission Logs")
    notes = st.text_area("Observations:", key="logs")
    if st.button("🚀 GENERATE & SAVE LOG"):
        if notes:
            report = falcon_query(f"Format: {notes} | Officer: {st.session_state.current_worker}", "Gate 4 Protocol")
            st.code(report)
            save_log(report)
            st.success("✅ Log Archived.")

with t4:
    st.subheader("🕵️ Supervisor Audit Terminal")
    audit_query = st.text_input("Search archives (Plate #, Name, Date):")
    if st.button("🔍 RUN DEEP AUDIT"):
        if os.path.exists("security_logs.txt") and audit_query:
            with open("security_logs.txt", "r", encoding="utf-8") as f:
                records = f.read()
            result = falcon_query(f"Search logs for '{audit_query}': \n\n {records}", "Audit Mode")
            st.info(result)

    if st.button("🗑️ Reset Station Memory"):
        st.session_state.messages = []
        st.rerun()
