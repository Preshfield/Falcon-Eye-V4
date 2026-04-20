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

# --- NEW: INITIALIZE CONVERSATION MEMORY ---
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

    # Define Rules
    if mode == "Gate 4 Protocol":
        sys_rules = f"You are a Gate Security AI. Use ONLY this manual: {manual_context}. Be firm and precise."
    elif mode == "Driver Instruction":
        sys_rules = "Short, clear safety instructions for truck drivers. Professional translator."
    elif mode == "Audit Mode":
        sys_rules = "You are a Forensic Auditor. Analyze the provided historical logs to find specific plate numbers or incidents."
    else:
        sys_rules = "You are a Real-Time Intelligence Engine. Date: April 20, 2026. Focus on site security."

    # --- INTEGRATING MEMORY LOOP ---
    conversation = [{"role": "system", "content": sys_rules}]
    # Add last 5 exchanges to the current "Brain" state
    for msg in st.session_state.messages[-5:]:
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
        # Adding a timestamp for the Audit engine to track months ago
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

if st.button("🔒 LOGOUT", type="secondary"):
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

# --- COMMAND TABS ---
t1, t2, t3, t4 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "🕵️ AUDIT"])

with t1:
    st.subheader("🔍 Knowledge Scan (With Memory)")
    k_mode = st.radio("Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    
    # Display Memory Flow
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if k_query := st.chat_input("Ask Falcon anything (it remembers our talk)..."):
        st.session_state.messages.append({"role": "user", "content": k_query})
        with st.chat_message("user"):
            st.markdown(k_query)
        
        with st.chat_message("assistant"):
            response = falcon_query(k_query, k_mode)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    if st.button("🗑️ Clear Local Memory"):
        st.session_state.messages = []
        st.rerun()

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
                report = falcon_query(f"Format this: {notes} | Officer: {st.session_state.current_worker}", "Gate 4 Protocol")
                st.code(report)
                save_log(report)
                st.success("✅ Report Synchronized and Saved to Vault.")
        else:
            st.warning("Please enter observations first.")

with t4:
    st.subheader("🕵️ Supervisor Audit Terminal")
    st.info("Cross-referencing saved history with Intelligence Core...")
    
    audit_query = st.text_input("Enter Plate Number, Name, or Event (e.g. 'Plate K-55 from 2 months ago'):")
    
    if st.button("🔍 RUN DEEP AUDIT"):
        if os.path.exists("security_logs.txt") and audit_query:
            with open("security_logs.txt", "r", encoding="utf-8") as f:
                past_records = f.read()
            
            with st.spinner("Scanning Vaulted Records..."):
                # We feed the entire log history to the AI specifically to find the audit target
                audit_result = falcon_query(f"Search these logs for '{audit_query}' and summarize all reoccurrences: \n\n {past_records}", "Audit Mode")
                st.markdown(f'<div class="intercom-box"><b>Audit Result:</b><br>{audit_result}</div>', unsafe_allow_html=True)
        else:
            st.warning("Database empty or no query entered.")

    st.divider()
    st.subheader("📁 Archive Access")
    if os.path.exists("security_logs.txt"):
        with open("security_logs.txt", "r", encoding="utf-8") as f:
            log_history = f.read()
        st.download_button("📥 Export Full Forensic History", log_history, file_name="falcon_forensics.txt")
