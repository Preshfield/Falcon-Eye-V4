import streamlit as st
import PyPDF2
import google.generativeai as genai
import os
import io
import pandas as pd
from gtts import gTTS
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. VISUAL HUD SETUP
st.set_page_config(page_title="Falcon Eye V4 | Command", layout="wide", page_icon="🦅")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #00f2ff; }
    stButton>button { border-radius: 20px; border: 1px solid #00f2ff; background-color: #161b22; color: #00f2ff; }
    </style>
    """, unsafe_allow_html=True)

# 2. ENCRYPTED ACCESS
if "authorized" not in st.session_state:
    st.session_state.authorized = False

if not st.session_state.authorized:
    st.title("🦅 Falcon Eye V4 | Secure Terminal")
    key = st.text_input("Enter Command Authorization Code:", type="password")
    if st.button("Initialize System"):
        if key == "Gate4Pass2026":
            st.session_state.authorized = True
            st.rerun()
        else:
            st.error("🚫 Access Denied: Invalid Key")
else:
    # 3. CORE AI ENGINE
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    
    def falcon_query(prompt):
        try:
            model = genai.GenerativeModel('gemini-pro')
            return model.generate_content(prompt).text
        except:
            return "⏳ Signal Interference. Please wait 15 seconds for the next sweep."

    # 4. COMMAND HUD
    st.title("🦅 Falcon Eye | Gate 4 Command")
    tab1, tab2, tab3 = st.tabs(["📡 Intelligence", "📖 Protocols", "📝 Mission Log"])

    with tab1:
        st.subheader("Field Intelligence & Translation")
        user_input = st.chat_input("Ask a procedure or enter a driver command...")
        target_lang = st.selectbox("Translate to:", ["None", "Urdu", "Arabic", "Hindi", "Tagalog"])
        
        if user_input:
            with st.spinner("Falcon Eye Scanning..."):
                final_p = f"Translate to {target_lang}: {user_input}" if target_lang != "None" else user_input
                response = falcon_query(final_p)
                st.info(response)
                
                if target_lang != "None":
                    try:
                        voice_map = {"Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
                        tts = gTTS(text=response, lang=voice_map[target_lang])
                        rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
                        st.audio(rv)
                    except: st.warning("Audio comms offline.")

    with tab2:
        st.subheader("Standard Operating Procedures")
        if os.path.exists("master_docs/gate_manual.pdf"):
            with open("master_docs/gate_manual.pdf", "rb") as f:
                st.download_button("📂 Access Digital Manual", f, "Gate_Manual.pdf")
        else:
            st.warning("Protocol Manual not found in master_docs/")

    with tab3:
        st.subheader("Shift Report Generation")
        raw_notes = st.text_area("Input Shift Observations:")
        if st.button("🚀 Finalize & Log Report"):
            with st.spinner("Processing Log..."):
                final_report = falcon_query(f"Format as a professional security report: {raw_notes}")
                st.code(final_report)
                
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    log_data = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Operator": "pappi",
                        "Raw_Notes": raw_notes,
                        "AI_Formatted_Report": final_report
                    }])
                    conn.create(spreadsheet=st.secrets["gsheets_url"], data=log_data)
                    st.success("✅ Logged to Falcon Eye Database")
                except:
                    st.error("Database connection failed. Check Sheet permissions.")

    if st.sidebar.button("System Shutdown"):
        st.session_state.authorized = False
        st.rerun()
