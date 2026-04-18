import streamlit as st
import google.generativeai as genai
from groq import Groq
import pandas as pd
from gtts import gTTS
import io
import os
import PyPDF2 # New requirement
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="Falcon Eye V5", layout="wide", page_icon="🦅")

# Aesthetic
st.markdown("<style>.main { background-color: #0e1117; color: #00f2ff; }</style>", unsafe_allow_html=True)

# ====================== MANUAL DIGESTION ENGINE ======================
def digest_manual():
    """Reads the PDF and converts it to text for the AI to study."""
    if os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except Exception:
            return "Error reading manual."
    return "No manual found."

# ====================== THE DUAL-BRAIN ======================
def falcon_query(prompt: str, brain_mode: str) -> str:
    manual_content = digest_manual() if brain_mode == "Gate 4 Protocol" else ""

    if brain_mode == "Gate 4 Protocol":
        system_rules = f"""
        You are the Gate 4 Intelligence System. 
        Your ONLY source of truth is the following manual:
        ---
        {manual_content}
        ---
        The user (pappi) might type thoughts roughly or with errors. 
        Interpret his intent, but provide answers ONLY based on the manual above. 
        If the manual doesn't cover it, say 'This is not in the Gate 4 protocols.'
        """
    else:
        system_rules = "You are a general-purpose AI. Answer anything using your global knowledge."

    # Engine logic
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"CONTEXT: {system_rules}\n\nUSER: {prompt}")
        return response.text.strip()
    except:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content

# ====================== AUTHORIZATION ======================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🦅 Falcon Eye V5")
    if st.text_input("Auth Code:", type="password") == "Gate4Pass2026":
        if st.button("Initialize"): st.session_state.auth = True; st.rerun()
    st.stop()

# ====================== COMMAND CENTER ======================
st.title("🦅 Falcon Eye | Gate 4 Command")
t1, t2, t3 = st.tabs(["📡 Intelligence", "📖 Protocols", "📝 Mission Log"])

with t1:
    brain_choice = st.radio("Brain Mode:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    target_lang = st.selectbox("Translate/Speak:", ["None", "Urdu", "Arabic", "Hindi", "Tagalog"])
    user_input = st.text_area("Command Input:", placeholder="Type your thoughts here...")

    if st.button("🚀 RUN SCAN"):
        if user_input:
            with st.spinner(f"Digesting Manual & Analyzing..."):
                result = falcon_query(user_input, brain_choice)
                st.info(result)
                if target_lang != "None":
                    v_map = {"Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
                    tts = gTTS(text=result, lang=v_map[target_lang])
                    rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
                    st.audio(rv)

with t2:
    st.subheader("Manual Access")
    if os.path.exists("gate_manual.pdf"):
        with open("gate_manual.pdf", "rb") as f:
            st.download_button("📂 Download Manual", f, "gate_manual.pdf")
    else: st.error("Manual missing from GitHub root.")

with t3:
    st.subheader("Mission Log")
    raw = st.text_area("Raw notes:")
    if st.button("🚀 Log Entry"):
        report = falcon_query(f"Summarize as a security log: {raw}", "Gate 4 Protocol")
        st.code(report)
        # G-Sheets connection code here...
