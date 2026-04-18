import streamlit as st
import google.generativeai as genai
from groq import Groq
from streamlit_mic_recorder import speech_to_text # New tool for the mic
from gtts import gTTS
import io
import os
import PyPDF2

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="Falcon Eye V6", layout="wide", page_icon="🦅")
st.markdown("<style>.main { background-color: #0e1117; color: #00f2ff; }</style>", unsafe_allow_html=True)

# ====================== THE BRAIN ENGINE ======================
def falcon_query(prompt: str, brain_mode: str) -> str:
    # (Same logic as before - reading manual for Gate 4, Global for others)
    manual_content = ""
    if brain_mode == "Gate 4 Protocol" and os.path.exists("gate_manual.pdf"):
        with open("gate_manual.pdf", "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages: manual_content += page.extract_text()

    system_rules = f"Source Manual: {manual_content}\nAnswer only based on manual." if brain_mode == "Gate 4 Protocol" else "General Assistant mode."
    
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(f"{system_rules}\nUser: {prompt}").text
    except:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
        return client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": system_rules}, {"role": "user", "content": prompt}]).choices[0].message.content

# ====================== AUTH ======================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    if st.text_input("Auth:", type="password") == "Gate4Pass2026":
        if st.button("Login"): st.session_state.auth = True; st.rerun()
    st.stop()

# ====================== COMMAND CENTER ======================
st.title("🦅 Falcon Eye | Gate 4 Bridge")
t1, t2, t3, t4 = st.tabs(["📡 Intelligence", "🎤 Live Bridge", "📖 Protocols", "📝 Log"])

# --- TAB 1 & 3 & 4 (Keep your existing code here) ---

# --- NEW TAB 2: LIVE BRIDGE ---
with t2:
    st.subheader("Interactive Voice Bridge")
    st.write("Ask the client/driver to tap the mic and speak.")
    
    # 1. Select the Client's Language
    client_lang = st.selectbox("Client speaks:", ["Arabic", "Urdu", "Hindi", "Tagalog"], key="bridge_lang")
    lang_codes = {"Arabic": "ar-SA", "Urdu": "ur-PK", "Hindi": "hi-IN", "Tagalog": "tl-PH"}

    # 2. THE RECORDING BUTTON
    # This listens, converts to text, and gives it back to us.
    text_from_client = speech_to_text(
        language=lang_codes[client_lang],
        start_prompt="Tap to Listen (Client)",
        stop_prompt="Processing...",
        just_once=True,
        key='client_speech'
    )

    if text_from_client:
        st.warning(f"Client Said ({client_lang}): {text_from_client}")
        
        # Translate it for you (pappi)
        with st.spinner("Translating for Operator..."):
            translation_for_me = falcon_query(f"The client said '{text_from_client}' in {client_lang}. What does this mean in English?", "Global Knowledge")
            st.success(f"Translation for you: {translation_for_me}")

    st.divider()
    
    # 3. YOUR RESPONSE
    my_reply = st.text_input("Your response to client (English):")
    if st.button("Translate & Speak to Client"):
        if my_reply:
            reply_in_client_lang = falcon_query(f"Translate this to {client_lang}: {my_reply}", "Global Knowledge")
            st.info(f"Speaking to client: {reply_in_client_lang}")
            
            # Voice output for them
            v_map = {"Urdu": "ur", "Arabic": "ar", "Hindi": "hi", "Tagalog": "tl"}
            tts = gTTS(text=reply_in_client_lang, lang=v_map[client_lang])
            rv = io.BytesIO(); tts.write_to_fp(rv); rv.seek(0)
            st.audio(rv, autoplay=True)
