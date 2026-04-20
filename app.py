import streamlit as st
import os, io, base64
from datetime import datetime, timedelta, timezone
from duckduckgo_search import DDGS
from gtts import gTTS
import PyPDF2
import openai
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer

# 1. LOAD EXTERNAL CSS (Keeps your interface beautiful)
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")
local_css("css/style.css")

# --- INITIALIZE MEMORY (THE RECENT ADDITION) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# ====================== SYSTEM ENGINES ======================

def digest_manual():
    # Looks for your gate manual
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
    
    # Connect to the DeepSeek Server (PAID TIER)
    client = openai.OpenAI(
        api_key=st.secrets["DEEPSEEK_API_KEY"], 
        base_url="https://api.deepseek.com"
    )

    # Tactical Security Rules
    if mode == "Gate 4 Protocol":
        sys_rules = f"You are a Gate Security AI. Use ONLY this manual: {manual_context}. Be firm and precise."
    elif mode == "Driver Instruction":
        sys_rules = "Short, clear safety instructions for truck drivers. Professional translator."
    else:
        sys_rules = "You are a Real-Time Intelligence Engine. Date: April 20, 2026. Focus on site security and Law No. 3."

    # BUILD MEMORY PACKET (The "Precious" Memory Loop)
    conversation = [{"role": "system", "content": sys_rules}]
    # We loop through session messages to keep the context alive
    for msg in st.session_state.messages[-6:]: # Keeps the last 6 messages for stability
        conversation.append({"role": msg["role"], "content": msg["content"]})
    
    conversation.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=conversation,
            stream=False
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"FALCON ENGINE ERROR: {str(e)}"

def save_log(report_text):
    with open("security_logs.txt", "a", encoding="utf-8") as f:
        f.write(f"{report_text}\n{'='*50}\n")

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

# Logout Logic
if st.sidebar.button("🔒 LOGOUT", type="secondary"):
    st.session_state.auth = False
    st.rerun()

# Forces the time to Dubai (UTC +4)
dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")
st.markdown(f'<div class="custom-header"><b>Station Active:</b> {st.session_state.current_worker} | {dubai_time}</div>', unsafe_allow_html=True)

# HERO SECTION
st.markdown("""
    <div style='text-align: left; padding: 40px 0 20px 0;'>
        <h1 class='falcon-title'>FALCON EYE</h1>
        <h2 class='gate-sub'>GATE 4 <span style='font-size:20px; color:#22d3ee; vertical-align:middle;'>● ONLINE</span></h2>
        <p style='color: #94a3b8; font-size: 14px; letter-spacing: 5px; font-weight: bold; text-transform: uppercase;'>
            Tactical AI Intelligence & Protocol Management
        </p>
    </div>
""", unsafe_allow_html=True)

# COMMAND TABS
t1, t2, t3 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS"])

with t1:
    st.subheader("🔍 Knowledge Scan")
    k_mode = st.radio("Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    
    # CHAT HISTORY DISPLAY
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # INPUT BLOCK
    if k_query := st.chat_input("Enter Protocol Query or Command..."):
        st.session_state.messages.append({"role": "user", "content": k_query})
        with st.chat_message("user"):
            st.markdown(k_query)
        
        with st.chat_message("assistant"):
            response = falcon_query(k_query, k_mode)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    st.divider()

    # INTERCOM BOX
    st.markdown('<div class="intercom-box">', unsafe_allow_html=True)
    st.subheader("🚛 Driver Intercom")
    full_langs = {"Bengali": "bn", "Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
    d_lang = st.selectbox("Language:", list(full_langs.keys()))
    
    c1, c2 = st.columns([3, 1])
    with c1: st.write("🎤 **Listen to Driver**")
    with c2: driver_v = speech_to_text(language=full_langs[d_lang], start_prompt="👂 LISTEN", key='d_mic')

    if driver_v:
        intent = falcon_query(f"Driver said: {driver_v}", "Driver Instruction")
        st.markdown(f'<div class="driver-msg"><b>Driver:</b> {driver_v}<br><b>AI:</b> {intent}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t2:
    st.subheader("Manuals")
    if os.path.exists("protocol_lecture.wav.mp3"):
        st.audio("protocol_lecture.wav.mp3")
    if os.path.exists("gate_manual.pdf"):
        pdf_viewer("gate_manual.pdf", height=700)

with t3:
    st.subheader("📋 Security Mission Logs")
    notes = st.text_area("Observations:", key="logs", placeholder="Enter shift details...")
    
    if st.button("🚀 GENERATE & SAVE LOG"):
        if notes:
            with st.spinner("Finalizing Report..."):
                report = falcon_query(f"Format this into a professional security report: {notes} | Officer: {st.session_state.current_worker}", "Gate 4 Protocol")
                st.code(report)
                save_log(report)
                st.success("✅ Report Synchronized and Saved to Database.")
        else:
            st.warning("Please enter observations first.")

    st.divider()
    st.subheader("📁 Archive: Recent Reports")
    if os.path.exists("security_logs.txt"):
        with open("security_logs.txt", "r", encoding="utf-8") as f:
            log_history = f.read()
        st.text_area("Historical Records:", log_history, height=300, disabled=True)
        st.download_button("📥 Download Full Log History", log_history, file_name="falcon_eye_logs.txt")
