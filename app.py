import streamlit as st
import google.generativeai as genai
from groq import Groq
import pandas as pd
from gtts import gTTS
import io
import os
import PyPDF2
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_mic_recorder import speech_to_text # The new tool

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="Falcon Eye V5", layout="wide", page_icon="🦅")

# Aesthetic
st.markdown("<style>.main { background-color: #0e1117; color: #00f2ff; }</style>", unsafe_allow_html=True)

# ====================== MANUAL DIGESTION ======================
def digest_manual():
    if os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = "".join([page.extract_text() for page in reader.pages])
                return text
        except: return ""
    return ""

# ====================== THE DUAL-BRAIN ENGINE ======================
def falcon_query(prompt: str, brain_mode: str) -> str:
    manual_data = digest_manual() if brain_mode == "Gate 4 Protocol" else ""
    
    # Strictly defining the "Source of Truth"
    if brain_mode == "Gate 4 Protocol":
        system_rules = f"You are the Gate 4 Supervisor. Use ONLY this manual: {manual_data}. If not in manual, say so."
    else:
        system_rules = "You are a general assistant."

    # Direct Groq Pipeline (No Google timeout)
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_rules},
            {"role": "user", "content": prompt}
        ]
    )
    return completion.choices[0].message.content
# ====================== MAIN APP ======================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🦅 Falcon Eye V5")
    if st.text_input("Code:", type="password") == "Gate4Pass2026":
        if st.button("Access"): st.session_state.auth = True; st.rerun()
    st.stop()

st.title("🦅 Falcon Eye | Gate 4 Command")
t1, t2, t3 = st.tabs(["📡 Intelligence", "📖 Protocols", "📝 Mission Log"])

with t1:
    brain = st.radio("Mode:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    lang = st.selectbox("Speech Language:", ["None", "Urdu", "Arabic", "Hindi", "Tagalog"])
    
    # New Voice Input Tool
    st.write("🎙️ Voice Command:")
    text_from_voice = speech_to_text(language='en', use_container_width=True, just_once=True, key='STT')
    
    user_input = st.text_area("Type Command:", value=text_from_voice if text_from_voice else "")

    if st.button("🚀 RUN SCAN"):
        if user_input:
            with st.spinner("Analyzing against protocols..."):
                result = falcon_query(user_input, brain)
                st.info(result)
                if lang != "None":
                    v_map = {"Urdu":"ur", "Arabic":"ar", "Hindi":"hi", "Tagalog":"tl"}
                    tts = gTTS(text=result, lang=v_map[lang])
                    rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
                    st.audio(rv)

import base64 # Ensure this is at the top of your app.py

with t2:
    st.subheader("📖 Gate 4 Library")
    
    # --- SECTION 1: PDF MANUAL ---
    if os.path.exists("gate_manual.pdf"):
        with open("gate_manual.pdf", "rb") as f:
            pdf_bytes = f.read()
            b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            
        # Clean button for mobile
        pdf_link = f'<a href="data:application/pdf;base64,{b64_pdf}" target="_blank" style="text-decoration: none;"><div style="background-color: #00f2ff; color: black; padding: 12px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 20px;">📖 OPEN MANUAL (FULL SCREEN)</div></a>'
        st.markdown(pdf_link, unsafe_allow_html=True)
    else:
        st.error("Manual PDF missing from GitHub.")

    st.write("---")

    # --- SECTION 2: NOTEBOOK LM AUDIO ---
    st.subheader("🎧 Audio Briefing")
    audio_file = "protocol_lecture.wav" # Make sure this matches your filename on GitHub
    
    if os.path.exists(audio_file):
        st.info("Listen to the AI-generated overview of Gate 4 protocols:")
        with open(audio_file, "rb") as a:
            audio_bytes = a.read()
            st.audio(audio_bytes, format="audio/wav")
        st.caption("Powered by NotebookLM Intelligence")
    else:
        st.warning("No audio lecture found. Upload 'protocol_lecture.wav' to GitHub to activate this feature.")
