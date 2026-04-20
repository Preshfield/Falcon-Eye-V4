import streamlit as st
import os, io, json
from datetime import datetime, timedelta, timezone
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

# ====================== NEW: PERSISTENT MEMORY ENGINE ======================

def get_chat_file(username):
    # Creates a unique memory file for each worker
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
        sys_rules = "Short, clear safety instructions and translations for truck drivers."
    elif mode == "Audit Mode":
        sys_rules = "Forensic Auditor. Analyze logs for plate numbers and incidents."
    else:
        sys_rules = "Real-Time Intelligence Engine. Date: April 20, 2026."

    # MEMORY INTEGRATION (Using the saved messages)
    conversation = [{"role": "system", "content": sys_rules}]
    for msg in st.session_state.messages[-10:]: # Remember more context
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
            # LOAD THE PERMANENT CHAT FOR THIS USER
            st.session_state.messages = load_chat_history(user_identity)
            st.rerun()
    st.stop()

# ====================== DASHBOARD UI ======================

if st.sidebar.button("🔒 LOGOUT", type="secondary"):
    # SAVE CHAT BEFORE LOGGING OUT
    save_chat_history(st.session_state.current_worker, st.session_state.messages)
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
    
    # CHAT HISTORY INTERFACE
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if k_query := st.chat_input("Ask Falcon anything..."):
        st.session_state.messages.append({"role": "user", "content": k_query})
        with chat_container:
            with st.chat_message("user"): st.markdown(k_query)
            with st.chat_message("assistant"):
                response = falcon_query(k_query, k_mode)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        # AUTO-SAVE AFTER EVERY MESSAGE
        save_chat_history(st.session_state.current_worker, st.session_state.messages)

    st.divider()
    # Intercom and Translator Logic follows here...
    st.markdown('<div class="intercom-box">', unsafe_allow_html=True)
    st.subheader("🚛 Driver Intercom")
    full_langs = {"Bengali": "bn", "Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
    d_lang = st.selectbox("Select Driver Language:", list(full_langs.keys()))
    c1, c2 = st.columns([3, 1])
    with c1: st.write(f"🎤 **Listen to {d_lang} Driver**")
    with c2: driver_v = speech_to_text(language=full_langs[d_lang], start_prompt="👂 LISTEN", key='d_mic')
    if driver_v:
        intent = falcon_query(f"The driver said this in {d_lang}: {driver_v}.", "Driver Instruction")
        st.markdown(f'<div class="driver-msg"><b>Driver:</b> {driver_v}<br><b>AI Interpretation:</b> {intent}</div>', unsafe_allow_html=True)
    d_reply = st.text_input("Reply to driver...", key="driver_reply_input")
    if d_reply:
        trans = falcon_query(f"Translate this to {d_lang}: {d_reply}", "Driver Instruction")
        st.success(f"**AI Translation:** {trans}")
        tts = gTTS(text=trans, lang=full_langs[d_lang])
        stream = io.BytesIO()
        tts.write_to_fp(stream)
        st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t2:
    if os.path.exists("gate_manual.pdf"):
        pdf_viewer("gate_manual.pdf", height=700)

with t3:
    notes = st.text_area("Observations:", key="logs")
    if st.button("🚀 GENERATE & SAVE LOG"):
        if notes:
            report = falcon_query(f"Format: {notes} | Officer: {st.session_state.current_worker}", "Gate 4 Protocol")
            st.code(report)
            with open("security_logs.txt", "a", encoding="utf-8") as f:
                f.write(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n{report}\n{'='*50}\n")
            st.success("✅ Log Archived.")

with t4:
    st.subheader("🕵️ Supervisor Audit Terminal")
    audit_query = st.text_input("Search archives:")
    if st.button("🔍 RUN DEEP AUDIT"):
        if os.path.exists("security_logs.txt") and audit_query:
            with open("security_logs.txt", "r", encoding="utf-8") as f:
                records = f.read()
            st.info(falcon_query(f"Search logs for '{audit_query}': \n\n {records}", "Audit Mode"))

    if st.sidebar.button("🗑️ Wipe My Station Memory"):
        if os.path.exists(get_chat_file(st.session_state.current_worker)):
            os.remove(get_chat_file(st.session_state.current_worker))
        st.session_state.messages = []
        st.rerun()
