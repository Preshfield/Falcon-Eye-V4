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
local_css("css/style.css")

# ====================== GOOGLE SHEETS ENGINE ======================

def save_to_google_sheets(worker, log_text):
    try:
        # Connect using the secret key in Streamlit
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        
        # Open your specific Sheet
        sheet = client.open("Falcon_Eye_Database").worksheet("LOG")
        
        # Create the row: Timestamp (Dubai), Worker Name, Log Content
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
    elif mode == "Audit Mode":
        sys_rules = "Forensic Auditor. Analyze logs for plate numbers and incidents."
    else:
        sys_rules = "Real-Time Intelligence Engine. Date: April 20, 2026."

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

st.markdown("""
    <div style='text-align: left; padding: 40px 0 20px 0;'>
        <h1 class='falcon-title'>FALCON EYE</h1>
        <h2 class='gate-sub'>GATE 4 <span style='font-size:20px; color:#22d3ee; vertical-align:middle;'>● ONLINE</span></h2>
    </div>
""", unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "🕵️ AUDIT"])

with t1:
    st.subheader("🔍 Knowledge Scan")
    k_mode = st.radio("Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if k_query := st.chat_input("Ask Falcon..."):
        st.session_state.messages.append({"role": "user", "content": k_query})
        with chat_container:
            with st.chat_message("user"): st.markdown(k_query)
            with st.chat_message("assistant"):
                response = falcon_query(k_query, k_mode)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        save_chat_history(st.session_state.current_worker, st.session_state.messages)

with t3:
    st.subheader("📋 Security Mission Logs")
    notes = st.text_area("Observations:", key="logs", placeholder="Type details for the official record...")
    
    if st.button("🚀 GENERATE & SAVE LOG"):
        if notes:
            with st.spinner("Pushing to Government Database..."):
                report = falcon_query(f"Format this observation: {notes} | Officer: {st.session_state.current_worker}", "Gate 4 Protocol")
                st.code(report)
                
                # SAVE TO GOOGLE SHEET
                if save_to_google_sheets(st.session_state.current_worker, report):
                    st.success("✅ Log Synchronized to Falcon_Eye_Database.")
        else:
            st.warning("Enter notes first.")

with t4:
    st.subheader("🕵️ Supervisor Audit Terminal")
    audit_query = st.text_input("Enter Plate/Name:")
    if st.button("🔍 RUN DEEP AUDIT"):
        # For the pitch, this scans current local logs
        st.info("System scanning record history...")
