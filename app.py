import streamlit as st
import os
import io
import base64
from datetime import datetime
import google.generativeai as genai
from groq import Groq
from gtts import gTTS
import PyPDF2
from streamlit_gsheets import GSheetsConnection
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer  # Your new addition!

# ====================== PAGE SETUP ======================
st.set_page_config(page_title="Falcon Eye V6", layout="wide", page_icon="🦅")

# Falcon Eye Dark Theme
st.markdown("<style>.main { background-color: #0e1117; color: #00f2ff; }</style>", unsafe_allow_html=True)

# ====================== CORE ENGINES ======================
def digest_manual():
    if os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "".join([page.extract_text() for page in reader.pages])
        except: return ""
    return ""

def falcon_query(prompt: str, brain_mode: str) -> str:
    manual_data = digest_manual() if brain_mode == "Gate 4 Protocol" else ""
    if brain_mode == "Gate 4 Protocol":
        system_rules = f"You are the Gate 4 Supervisor. Source: {manual_data}. If not in manual, say so. Pappi may type messy; interpret his intent."
    else:
        system_rules = "You are a general AI assistant."

    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content

# ====================== AUTHENTICATION ======================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🦅 Falcon Eye V6")
    if st.text_input("Authorization:", type="password") == "Gate4Pass2026":
        if st.button("Initialize System"): st.session_state.auth = True; st.rerun()
    st.stop()

# ====================== COMMAND CENTER ======================
st.title("🦅 Falcon Eye | Gate 4 Command")
t1, t2, t3 = st.tabs(["📡 Intelligence", "📖 Protocols", "📝 Mission Log"])

# --- TAB 1: AI SCANNER & TRANSLATOR ---
with t1:
    brain = st.radio("System Brain:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    lang = st.selectbox("Speech Language:", ["None", "Urdu", "Arabic", "Hindi", "Tagalog"])
    
    st.write("🎙️ Voice Command:")
    voice_txt = speech_to_text(language='en', use_container_width=True, just_once=True, key='STT')
    user_input = st.text_area("Input Command:", value=voice_txt if voice_txt else "")

    if st.button("🚀 RUN SCAN"):
        if user_input:
            with st.spinner("Analyzing..."):
                result = falcon_query(user_input, brain)
                st.info(result)
                if lang != "None":
                    v_map = {"Urdu":"ur", "Arabic":"ar", "Hindi":"hi", "Tagalog":"tl"}
                    tts = gTTS(text=result, lang=v_map[lang])
                    rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
                    st.audio(rv)

# --- TAB 2: PROTOCOLS (PDF + AUDIO) ---
with t2:
    st.subheader("📖 Gate 4 Library")
    
    if os.path.exists("gate_manual.pdf"):
        # Download Button as backup
        with open("gate_manual.pdf", "rb") as f:
            st.download_button("📥 Download Copy to Phone", f, "gate_manual.pdf", use_container_width=True)
        
        st.write("---")
        
        # IN-APP PDF VIEWER (Your requested feature)
        st.info("📜 Scroll to read the manual below. Stay in-app!")
        pdf_viewer("gate_manual.pdf", height=700) 
        
    else:
        st.error("Manual 'gate_manual.pdf' not found.")

    st.write("---")
    
    # NOTEBOOK LM AUDIO STATION
    st.subheader("🎧 Audio Training")
    audio_path = "protocol_lecture.wav"
    if os.path.exists(audio_path):
        with open(audio_path, "rb") as a:
            st.audio(a.read(), format="audio/wav")
        st.caption("NotebookLM Protocol Briefing")
    else:
        st.caption("Upload 'protocol_lecture.wav' for audio training.")

# --- TAB 3: MISSION LOG ---
with t3:
    st.subheader("Shift Reporting")
    notes = st.text_area("Observations:")
    if st.button("🚀 Record Log"):
        report = falcon_query(f"Format as security log: {notes}", "Gate 4 Protocol")
        st.code(report)
        # G-Sheets logic here...
