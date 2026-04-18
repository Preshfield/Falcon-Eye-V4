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
# 1. Initialize the Conversation History (add this near the top of your app)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

with t1:
    st.subheader("📡 Gate 4 Intercom")
    
    # Brain and Language Setup
    col1, col2 = st.columns(2)
    with col1:
        brain_mode = st.radio("Brain Context:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    with col2:
        driver_lang = st.selectbox("Driver's Language:", ["Urdu", "Arabic", "Hindi", "Tagalog"])

    # --- STEP 1: LISTEN TO DRIVER ---
    st.write("🎤 **Step 1: Driver is speaking...**")
    # We set this to listen in the driver's language
    lang_map = {"Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl", "None": "en"}
    driver_speech = speech_to_text(
        language=lang_map.get(driver_lang, 'en'), 
        start_prompt="👂 Listen to Driver", 
        stop_prompt="✅ Stop Listening", 
        just_once=True, 
        key='driver_mic'
    )

    if driver_speech:
        # Save driver's words to history
        st.session_state.chat_history.append({"role": "driver", "text": driver_speech})
        # AI explains what the driver said in English for you
        driver_intent = falcon_query(f"The driver said this in {driver_lang}: '{driver_speech}'. Explain what they want in English briefly.", brain_mode)
        st.warning(f"Driver says: {driver_speech} \n\n(AI Analysis: {driver_intent})")

    st.divider()

    # --- STEP 2: YOUR RESPONSE ---
    st.write("⌨️ **Step 2: Type your response to the driver:**")
    my_reply = st.chat_input("Type your instructions here...")

    if my_reply:
        # Save your reply to history
        st.session_state.chat_history.append({"role": "pappi", "text": my_reply})
        
        with st.spinner("Translating & Preparing Voice..."):
            # Translate your instruction to the driver's language
            translated_reply = falcon_query(f"Translate this instruction to {driver_lang} clearly: {my_reply}", "Global Knowledge")
            
            # Show the translation and play it out loud
            st.success(f"Response (translated): {translated_reply}")
            
            # Generate Audio for the driver to hear
            tts = gTTS(text=translated_reply, lang=lang_map.get(driver_lang, 'en'))
            rv = io.BytesIO()
            tts.write_to_fp(rv)
            st.audio(rv.getvalue(), format="audio/mp3", autoplay=True) # Autoplay for speed!

    # --- STEP 3: THE CONVERSATION LOG ---
    st.write("📜 **Live Conversation Log**")
    for chat in reversed(st.session_state.chat_history):
        if chat["role"] == "driver":
            st.chat_message("user", avatar="🚚").write(chat["text"])
        else:
            st.chat_message("assistant", avatar="🦅").write(chat["text"])
    
    if st.button("🗑️ Clear Intercom"):
        st.session_state.chat_history = []
        st.rerun()
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
    audio_path = "protocol_lecture.wav.mp3"
    if os.path.exists(audio_path):
        with open(audio_path, "rb") as a:
            st.audio(a.read(), format="audio/mp3")
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
