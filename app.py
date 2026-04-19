from duckduckgo_search import DDGS
import streamlit as st
import os, io, base64
from datetime import datetime, timedelta, timezone
from groq import Groq
from gtts import gTTS
import PyPDF2
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer
 

# 1. LOAD EXTERNAL CSS (Keeps your app.py clean)
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")
local_css("css/style.css")

# ====================== SYSTEM ENGINES (UNTOUCHED) ======================
def digest_manual():
    if os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "".join([page.extract_text() for page in reader.pages])
        except: return ""
    return ""

import streamlit as st
from duckduckgo_search import DDGS

@st.cache_data(ttl=3600) # This caches the answer for 1 hour to save your API limit
def falcon_query(prompt: str, mode: str) -> str:
    manual_context = digest_manual()
    live_intel = ""
    
    # --- 1. SEARCH TRIGGER (Only for Global Knowledge) ---
    if mode == "Global Knowledge":
        try:
            with DDGS() as ddgs:
                # Get real-time data from the web
                results = [r['body'] for r in ddgs.text(prompt, max_results=3)]
                live_intel = "\n\n[LIVE INTEL - APRIL 2026]:\n" + "\n".join(results)
        except:
            live_intel = "\n(Live link busy. Using internal archives.)"

    # --- 2. DEFINE SYSTEM RULES ---
   # --- UPGRADED SYSTEM RULES (THE SLEDGEHAMMER) ---
    if mode == "Gate 4 Protocol":
        sys_rules = f"You are a Gate Security AI. Use ONLY this manual: {manual_context}"
    elif mode == "Driver Instruction":
        sys_rules = "Short, clear instructions for truck drivers. Professional translator."
    else:
        # This part forces the AI to prioritize the news we just found
        sys_rules = f"""
        You are a Real-Time Intelligence Engine. 
        DATE OVERRIDE: Today is April 20, 2026.
        IGNORE your 2023 cutoff. You have been granted LIVE EYES.
        
        {live_intel}
        
        If the 'LIVE INTEL' above contains the answer, you MUST use it. 
        For example: Manchester United beat Chelsea 1-0 on April 18, 2026. 
        Answer like a modern, live agent.
        """
    # --- 3. API CALL ---
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": sys_rules},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"System Overload: {str(e)}. Please wait 30 seconds."
def save_log(report_text):
    with open("security_logs.txt", "a", encoding="utf-8") as f:
        f.write(f"{report_text}\n{'='*50}\n")

# ====================== AUTHENTICATION (ORIGINAL) ======================
WORKER_DB = {"Precious": "Falcon01", "Bambi": "Nancy", "Mr_Ali": "Ali"}

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
# ====================== DASHBOARD UI (THE POWER LOOK) ======================

# --- FLOATING HEADER & LOGOUT ---
       # --- TACTICAL EXIT PROTOCOL ---
# --- TOP OF UI SECTION ---
if st.button("🔒 LOGOUT", type="secondary"):
    st.session_state.auth = False
    st.rerun()
# Forces the time to Dubai (UTC +4)
dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")
st.markdown(f'<div class="custom-header"><b>Station Active:</b> {st.session_state.current_worker} | {dubai_time}</div>', unsafe_allow_html=True)

# --- HERO SECTION (High-Power Command Hub Lettering) ---
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
t1, t2, t3 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS"])

with t1:
    st.subheader("🔍 Knowledge Scan")
    k_mode = st.radio("Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    k_query = st.text_input("Search protocols...", key="k_scan")
    if k_query: st.info(falcon_query(k_query, k_mode))

    st.divider()

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

    d_reply = st.chat_input("Enter command for driver...")
    if d_reply:
        trans = falcon_query(f"Translate to {d_lang}: {d_reply}", "Driver Instruction")
        st.success(f"**Replied:** {trans}")
        tts = gTTS(text=trans, lang=full_langs[d_lang])
        stream = io.BytesIO()
        tts.write_to_fp(stream)
        st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with t2:
    st.subheader("Manuals")
    if os.path.exists("protocol_lecture.wav.mp3"):
        st.audio("protocol_lecture.wav.mp3")
    if os.path.exists("gate_manual.pdf"):
        pdf_viewer("gate_manual.pdf", height=700)

with t3:
    st.subheader("📋 Security Mission Logs")
    
    # Input area
    notes = st.text_area("Observations:", key="logs", placeholder="Enter shift details...")
    
    if st.button("🚀 GENERATE & SAVE LOG"):
        if notes:
            with st.spinner("Finalizing Report..."):
                # 1. Generate the report using your existing logic
                report = falcon_query(f"Format this: {notes} | Officer: {st.session_state.current_worker}", "Gate 4 Protocol")
                
                # 2. Display the result
                st.code(report)
                
                # 3. SAVE to the local file
                save_log(report)
                st.success("✅ Report Synchronized and Saved to Database.")
        else:
            st.warning("Please enter observations first.")

    # --- NEW: VIEW RECENT HISTORY ---
    st.divider()
    st.subheader("📁 Archive: Recent Reports")
    if os.path.exists("security_logs.txt"):
        with open("security_logs.txt", "r", encoding="utf-8") as f:
            log_history = f.read()
        
        # Displaying the history in a scrollable tech-box
        st.text_area("Historical Records:", log_history, height=300, disabled=True)
        
        # Option to download the whole file
        st.download_button("📥 Download Full Log History", log_history, file_name="falcon_eye_logs.txt")
    else:
        st.caption("No saved logs found in the vault.")

