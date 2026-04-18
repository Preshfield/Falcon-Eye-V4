import streamlit as st
import google.generativeai as genai
from groq import Groq
import pandas as pd
from gtts import gTTS
import io
import os
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="Falcon Eye V5", layout="wide", page_icon="🦅")

# Custom CSS for the Falcon Eye Look
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #00f2ff; }
    .stButton>button { border-radius: 20px; border: 1px solid #00f2ff; background-color: #161b22; color: #00f2ff; }
    </style>
    """, unsafe_allow_html=True)

# ====================== THE DUAL-ENGINE BRAIN ======================
def falcon_query(prompt: str, brain_mode: str) -> str:
    # SYSTEM INSTRUCTIONS
    if brain_mode == "Gate 4 Protocol":
        system_rules = "You are the Gate 4 Intelligence System. Strictly answer based on security protocols and the gate manual. Be professional, concise, and focused on safety."
    else:
        system_rules = "You are a general-purpose AI assistant. Provide helpful, broad, and creative answers on any topic."

    full_prompt = f"SYSTEM: {system_rules}\nUSER: {prompt}"

    # Try Gemini (Primary)
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(full_prompt, request_options={"timeout": 10})
        return response.text.strip()
    except Exception:
        # Failover to Groq
        try:
            client = Groq(api_key=st.secrets["GROQ_API_KEY"])
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"❌ CONNECTION ERROR: {str(e)}"

# ====================== AUTHORIZATION ======================
if "authorized" not in st.session_state: st.session_state.authorized = False
if not st.session_state.authorized:
    st.title("🦅 Falcon Eye V5 | Secure Terminal")
    if st.text_input("Authorization Code:", type="password") == "Gate4Pass2026":
        if st.button("Initialize System"):
            st.session_state.authorized = True
            st.rerun()
    st.stop()

# ====================== MAIN COMMAND CENTER ======================
st.title("🦅 Falcon Eye | Gate 4 Command")

tab1, tab2, tab3 = st.tabs(["📡 Intelligence", "📖 Protocols", "📝 Mission Log"])

# ------------------- TAB 1: INTELLIGENCE -------------------
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        brain_choice = st.radio("Select Brain Mode:", ["Gate 4 Protocol", "Global Knowledge"], help="Switch between work-only and general-use AI.")
    with col2:
        target_lang = st.selectbox("Translate/Speak in:", ["None", "Urdu", "Arabic", "Hindi", "Tagalog"])

    user_input = st.text_area("Enter instruction or scan request:", height=100)

    if st.button("🚀 RUN SCAN"):
        if user_input:
            with st.spinner(f"Querying {brain_choice}..."):
                result = falcon_query(user_input, brain_choice)
                st.info(result)
                
                if target_lang != "None":
                    v_map = {"Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
                    tts = gTTS(text=result, lang=v_map[target_lang])
                    rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
                    st.audio(rv)

# ------------------- TAB 2: PROTOCOLS -------------------
with tab2:
    st.subheader("Manual & Procedures")
    if os.path.exists("gate_manual.pdf"):
        with open("gate_manual.pdf", "rb") as f:
            st.download_button("📂 Download Gate Manual", f, "Gate_Manual.pdf")
    else:
        st.warning("Manual not found on main page.")

# ------------------- TAB 3: MISSION LOG -------------------
with tab3:
    st.subheader("Shift Report Generator")
    raw_notes = st.text_area("Enter shift notes:")
    if st.button("🚀 Log to Database"):
        report = falcon_query(f"Format as a professional security log: {raw_notes}", "Gate 4 Protocol")
        st.code(report)
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            log_entry = pd.DataFrame([{"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Operator": "pappi", "Report": report}])
            conn.create(spreadsheet=st.secrets["gsheets_url"], data=log_entry)
            st.success("✅ Entry recorded.")
        except Exception as e: st.error(f"Sync failed: {e}")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.success("🟢 System Online")
    st.caption("Operator: pappi")
    if st.button("🔌 Shutdown"):
        st.session_state.authorized = False
        st.rerun()
