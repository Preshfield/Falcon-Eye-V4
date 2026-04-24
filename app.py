import streamlit as st
import os, io, json, base64
from datetime import datetime, timedelta, timezone
from gtts import gTTS
import PyPDF2
import openai
import gspread
from google.oauth2.service_account import Credentials
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer
from fpdf import FPDF

# ====================== 1. CRITICAL INITIALIZATION ======================
st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")

if "auth" not in st.session_state:
    st.session_state.auth = False
if "all_sessions" not in st.session_state:
    st.session_state.all_sessions = {"New Conversation": []}
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = "New Conversation"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_worker" not in st.session_state:
    st.session_state.current_worker = "Guest"

# ====================== 2. FULL RESTORED CSS ======================
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    st.markdown('''
        <style>
        .stApp { background: radial-gradient(circle at top right, #0f172a, #020617); color: #f8fafc; }
        .hero-container {
            background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(10px);
            padding: 60px 40px; border-radius: 20px; margin-bottom: 30px;
            border: 1px solid rgba(173, 255, 47, 0.3); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        .hero-title { color: #ffffff !important; font-size: 72px !important; font-weight: 900 !important; letter-spacing: -3px !important; }
        .status-dot { color: #ADFF2F; font-weight: 800; text-shadow: 0 0 15px #ADFF2F; animation: pulse 2s infinite; }
        .hero-divider { height: 3px; width: 80px; background: linear-gradient(90deg, #ADFF2F, transparent); margin: 20px 0; }
        .hero-tagline { color: #ADFF2F !important; font-size: 14px !important; letter-spacing: 5px !important; font-weight: 700 !important; text-transform: uppercase; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        .stTabs [data-baseweb="tab-list"] { background-color: rgba(30, 41, 59, 0.5); padding: 10px; border-radius: 12px; }
        .stTabs [aria-selected="true"] { color: #ADFF2F !important; background-color: rgba(173, 255, 47, 0.1) !important; }
        .driver-msg { background: rgba(173, 255, 47, 0.1); padding: 15px; border-radius: 10px; border-left: 5px solid #ADFF2F; margin: 10px 0; }
        .intercom-box { background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.1); }
        .custom-header { background: rgba(15, 23, 42, 0.9); padding: 10px 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ADFF2F; }
        </style>
    ''', unsafe_allow_html=True)

local_css("css/style.css")

# ====================== 3. UTILITY ENGINES ======================
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def save_to_google_sheets(worker, payload, sheet_name="LOG", custom_date=None):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        # Use custom_date if provided, otherwise use Dubai current date
        if custom_date:
            date_s = custom_date
        else:
            now = datetime.now(timezone(timedelta(hours=4)))
            date_s = now.strftime("%d-%m-%Y")
        
        if sheet_name == "MANUAL PASS":
            # SL NO, DATE, BOOK NO, GP NO...
            row_data = [payload[0], date_s, payload[1], payload[2], payload[3], payload[4], payload[5], payload[6], payload[7], worker, payload[8], payload[9]]
        else:
            row_data = [date_s] + [str(i).upper() for i in payload] + [worker]
            
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"❌ SYNC ERROR: {str(e)}"); return False

def update_google_sheet(row_index, payload, sheet_name, custom_date=None):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        if custom_date:
            date_s = custom_date
        else:
            now = datetime.now(timezone(timedelta(hours=4)))
            date_s = now.strftime("%d-%m-%Y")

        if sheet_name == "MANUAL PASS":
            row_data = [payload[0], date_s, payload[1], payload[2], payload[3], payload[4], payload[5], payload[6], payload[7], st.session_state.current_worker, payload[8], payload[9]]
        else:
            row_data = [date_s] + [str(i).upper() for i in payload] + [st.session_state.current_worker]
        sheet.update(f"A{row_index}", [row_data])
        return True
    except Exception as e:
        st.error(f"Update Failed: {e}"); return False

def search_logs(query, sheet_name="LOG"):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        all_rows = sheet.get_all_values()
        if not all_rows: return None, None
        header = all_rows[0]
        for idx, row in enumerate(all_rows[1:][-50:], start=max(2, len(all_rows)-49)): 
            if any(query.upper() in str(c).upper() for c in row):
                return dict(zip(header, row)), idx
        return None, None
    except: return None, None

def get_last_ids(sheet_name):
    try:
        client = get_gsheet_client()
        sheet = client.open("Falcon_Eye_Database").worksheet(sheet_name)
        vals = sheet.get_all_values()
        if len(vals) < 2: return "1", "1"
        last_row = vals[-1]
        return last_row[0], last_row[3]
    except: return "1", "1"

def load_all_sessions(username):
    file_path = f"memory_{username.replace(' ', '_').lower()}.json"
    if os.path.exists(file_path):
        with open(file_path, "r") as f: return json.load(f)
    return {"New Conversation": []}

def save_all_sessions(username, sessions):
    file_path = f"memory_{username.replace(' ', '_').lower()}.json"
    with open(file_path, "w") as f: json.dump(sessions, f)

# ====================== 4. AI ENGINES ======================
@st.cache_data(ttl=3600)
def falcon_query(prompt: str, mode: str, chat_history=None) -> str:
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    sys_rules = "Tactical Security AI Gate 4 Dubai DWC. Current Date: April 23, 2026."
    if mode == "Driver Instruction": sys_rules = "Short & clear translator for truck drivers."
    
    conversation = [{"role": "system", "content": sys_rules}]
    if chat_history: conversation.extend(chat_history[-10:])
    conversation.append({"role": "user", "content": prompt})
    try:
        completion = client.chat.completions.create(model="deepseek-chat", messages=conversation, stream=False)
        return completion.choices[0].message.content
    except Exception as e: return f"AI ERROR: {str(e)}"

# ====================== 5. AUTHENTICATION ======================
WORKER_DB = {"Precious Akpezi Ojah": "Falcon01", "Bambi": "Nancy", "Mr_Ali": "Ali"}

if not st.session_state.auth:
    st.title("🦅 FALCON EYE | LOGIN")
    user_identity = st.selectbox("USER:", list(WORKER_DB.keys()))
    user_password = st.text_input("PASSWORD:", type="password")
    if st.button("SIGN IN") and user_password == WORKER_DB[user_identity]:
        st.session_state.auth = True
        st.session_state.current_worker = user_identity
        st.session_state.all_sessions = load_all_sessions(user_identity)
        st.rerun()
    st.stop()

# ====================== 6. DASHBOARD UI (SIDEBAR RESTORED) ======================
dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")

with st.sidebar:
    st.title("🦅 MISSION LOGS")
    chat_list = list(st.session_state.all_sessions.keys())
    if st.button("➕ START NEW CHAT", use_container_width=True):
        new_id = f"Session {len(chat_list) + 1} ({dubai_time})"
        st.session_state.all_sessions[new_id] = []
        st.session_state.current_chat_id = new_id
        st.rerun()
    st.divider()
    selected_chat = st.radio("History:", chat_list)
    st.session_state.current_chat_id = selected_chat
    st.session_state.messages = st.session_state.all_sessions.get(selected_chat, [])
    if st.button("🔒 LOGOUT", use_container_width=True):
        save_all_sessions(st.session_state.current_worker, st.session_state.all_sessions)
        st.session_state.auth = False
        st.rerun()

st.markdown(f'<div class="custom-header"><b>Station:</b> {st.session_state.current_worker} | {dubai_time}</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-container"><h1 class="hero-title">FALCON EYE</h1><h2>GATE 4 <span class="status-dot">● ONLINE</span></h2><div class="hero-divider"></div><p class="hero-tagline">Tactical AI & Protocol Management</p></div>', unsafe_allow_html=True)

# TABS
t1, t2, t3, t4, t5 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "🕵️ AUDIT", "📟 LOGISTIC DOCUMENTATION"])

with t1:
    st.subheader(f"🔍 {st.session_state.current_chat_id}")
    
    # 1. SCOPE TOGGLE
    k_mode = st.radio("Intelligence Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    
    # 2. CHAT CONTAINER
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]): 
                st.markdown(message["content"])
    
    # 3. CHAT & AUDIO LOGIC
    if k_query := st.chat_input("Ask Falcon..."):
        st.session_state.messages.append({"role": "user", "content": k_query})
        
        # Get AI response
        ans = falcon_query(k_query, k_mode, st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        
        # --- LECTURE AUDIO ENGINE ---
        # Converts the AI's response into audio immediately
        try:
            tts_lang = 'en' # Default to English for lectures
            tts = gTTS(text=ans, lang=tts_lang)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp.getvalue(), format="audio/mpeg", autoplay=True)
        except Exception as e:
            st.warning("Audio playback unavailable.")
        # ----------------------------

        # Save to memory and refresh
        st.session_state.all_sessions[st.session_state.current_chat_id] = st.session_state.messages
        save_all_sessions(st.session_state.current_worker, st.session_state.all_sessions)
        st.rerun()

    
# --- GLOBAL UNIVERSAL INTERPRETER (INTELLIGENT SYNC) ---
    st.divider()
    st.markdown('<div class="intercom-box">', unsafe_allow_html=True)
    st.subheader("🌍 Global Universal Interpreter")
    
    # 1. Memory Initialization
    if 'intelli_buffer' not in st.session_state:
        st.session_state.intelli_buffer = ""

    full_langs = {
        "Arabic": "ar", "Bengali": "bn", "Chinese (Mandarin)": "zh-CN",
        "English": "en", "French": "fr", "German": "de", "Hindi": "hi", 
        "Italian": "it", "Japanese": "ja", "Korean": "ko", "Malayalam": "ml", 
        "Nigerian Pidgin": "pcm", "Portuguese": "pt", "Russian": "ru", 
        "Spanish": "es", "Swahili": "sw", "Tagalog": "tl", "Tamil": "ta", 
        "Urdu": "ur", "Vietnamese": "vi"
    }
    
    d_lang = st.selectbox("Target Language:", sorted(list(full_langs.keys())), key="global_lang_sel")

    # --- STEP 1: INCOMING (Guest to You) ---
    st.write("### 👂 Step 1: Listen to Guest")
    incoming_v = speech_to_text(language=full_langs[d_lang], start_prompt=f"LISTEN ({d_lang})", key='global_mic_in')
    if incoming_v:
        interpretation = falcon_query(f"Direct interpretation to English ONLY. No commentary: {incoming_v}", "Global Knowledge")
        st.markdown(f'<div class="driver-msg"><b>Interpretation:</b> {interpretation}</div>', unsafe_allow_html=True)

    st.write("---")

    # --- STEP 2: OUTGOING (You to Guest) ---
    st.write("### 🎙️ Step 2: Your Response")
    col_v1, col_v2 = st.columns([0.3, 0.7])
    
    with col_v1:
        # 🎤 Speak Mic
        voice_raw = speech_to_text(language='en-US', start_prompt="🎤 SPEAK", key='global_mic_out')
        
        # INTELLIGENCE SYNC: Use Falcon to clean up and translate voice to text
        if voice_raw:
            # This ensures even if the mic hears background noise, the AI cleans it up for the text box
            clean_text = falcon_query(f"Clean up this speech into a clear professional sentence. English only: {voice_raw}", "Global Knowledge")
            st.session_state.intelli_buffer = clean_text

    with col_v2:
        # ⌨️ The Type/Edit Column (Now intelligently filled by the AI mic)
        st.session_state.intelli_buffer = st.text_input(
            "Type or Edit Response:", 
            value=st.session_state.intelli_buffer, 
            key="final_input_box"
        )

    # --- STEP 3: THE ACTION (Generate Audio) ---
    if st.button("🚀 SEND & GENERATE AUDIO") and st.session_state.intelli_buffer:
        final_msg = st.session_state.intelli_buffer
        
        # Final translation to guest language
        response_trans = falcon_query(f"Translate to {d_lang} ONLY: {final_msg}", "Global Knowledge")
        st.success(f"**Interpretation ({d_lang}):** {response_trans}")
        
        try:
            import io
            from gtts import gTTS
            tts = gTTS(text=response_trans, lang=full_langs[d_lang])
            stream = io.BytesIO()
            tts.write_to_fp(stream)
            stream.seek(0)
            
            st.audio(stream.read(), format="audio/mpeg")
            st.info("👆 Play for speaker.")
            
        except Exception as e:
            st.error(f"Audio Error: {e}")

    st.markdown('</div>', unsafe_allow_html=True)
   # protocol manual)

with t2:
    if os.path.exists("gate_manual.pdf"):
        # Create a layout for the title and the audio player
        col_p1, col_p2 = st.columns([0.6, 0.4])
        
        with col_p1:
            st.subheader("📖 Gate 4 Protocol Manual")
            
        with col_p2:
            # --- PRE-RECORDED LECTURE PLAYER ---
            lecture_path = "protocol_lecture.wav.mp3"
            if os.path.exists(lecture_path):
                st.write("🎵 **Protocol Audio Lecture**")
                st.audio(lecture_path, format="audio/mpeg")
            else:
                st.info("Audio file 'protocol_lecture.wav.mp3' not found.")

        # Display the PDF below
        pdf_viewer("gate_manual.pdf", height=800)
    else:
        st.error("Manual not found. Please ensure 'gate_manual.pdf' is in the repository.")
with t3:
    notes = st.text_area("Observations:")
    if st.button("🚀 SAVE LOG") and notes:
        if save_to_google_sheets(st.session_state.current_worker, notes, "LOG"): st.success("✅ Logged.")

with t4:
    audit_query = st.text_input("Search archives:")
    if st.button("🔍 RUN AUDIT"):
        found, _ = search_logs(audit_query, "MANUAL PASS")
        if found: st.table(found)
        else: st.info("No records found.")

with t5:
    st.subheader("📟 Logistics Command Center")
    
    # 1. EXPRESS ENTRY LOGIC
    quick_code = st.text_input("⚡ EXPRESS ENTRY (e.g. PASS 1234):").upper()
    st.write("📌 Quick Fill:")
    col_q1, col_q2, col_q3 = st.columns(3)
    smart_con = ""
    if col_q1.button("DHL"): smart_con = "DHL EXPRESS"
    if col_q2.button("FEDEX"): smart_con = "FEDEX LOGISTICS"
    if col_q3.button("ARAMEX"): smart_con = "ARAMEX DUBAI"

    # 2. AUTO-ID GENERATION
    last_sl, last_gp = get_last_ids("MANUAL PASS")
    try: next_sl = str(int(last_sl) + 1); next_gp = str(int(last_gp) + 1)
    except: next_sl = ""; next_gp = ""
    if "PASS" in quick_code: next_gp = quick_code.replace("PASS", "").strip()

    # 3. MODE STATUS
    is_editing = "edit_row_idx" in st.session_state
    doc_type = st.radio("Form Type:", ["Manual Gate Pass", "Labour Charge", "Official Report"], horizontal=True)

    # 4. THE MAIN FORM
    with st.form("logistics_form", clear_on_submit=True):
        f_date = st.date_input("SELECT DATE:", value=datetime.now(timezone(timedelta(hours=4))))
        formatted_date = f_date.strftime("%d-%m-%Y")
        
        if doc_type == "Manual Gate Pass":
            c1, c2, c3 = st.columns(3)
            f_sl = c1.text_input("SL NO", value=next_sl).upper()
            f_bk = c2.text_input("BOOK NO").upper()
            f_gp = c3.text_input("GATE PASS NO", value=next_gp).upper()
            f_con = st.text_input("CONSIGNEE", value=smart_con).upper()
            f_bill = st.text_input("CUSTOMS BILL NO").upper()
            f_desc = st.text_area("DESCRIPTION").upper()
            c4, c5, c6 = st.columns(3)
            f_unit = c4.text_input("UNIT").upper()
            f_cash = c5.text_input("CASH RECEIPT NO").upper()
            f_amt = c6.number_input("AMOUNT", min_value=0.0, format="%.2f")
            f_rem = st.text_input("REMARKS").upper()
            payload = [f_sl, f_bk, f_gp, f_con, f_bill, f_desc, f_unit, f_cash, f_rem, str(f_amt)]
            sheet_target, check_id = "MANUAL PASS", f_gp
        
        elif doc_type == "Labour Charge":
            t_start = st.time_input("START TIME")
            t_end = st.time_input("FINISH TIME")
            payload = [t_start.strftime("%H:%M"), t_end.strftime("%H:%M"), st.text_input("RECEIPT BOOK").upper(),
                       st.text_input("VOUCHER").upper(), st.text_input("HOURS").upper(), st.text_input("LABOURS").upper(),
                       st.selectbox("FORKLIFT", ["YES", "NO"]), st.number_input("AMOUNT", min_value=0.0), st.text_input("FROM").upper(), st.text_input("REMARKS").upper()]
            sheet_target, check_id = "LABOUR CHARGE", payload[3]
        else:
            payload = [st.text_input("BOOK NO").upper(), st.text_input("GATE PASS NO").upper(), st.text_input("CONSIGNEE").upper(),
                       st.text_input("BILL NO").upper(), st.text_input("REMARKS").upper(), st.number_input("AMOUNT", min_value=0.0), st.text_area("REASON").upper()]
            sheet_target, check_id = "OFFICIAL REPORT", payload[1]

        # --- DYNAMIC ACTION BUTTONS ---
        st.divider()
        if is_editing:
            st.warning(f"🛠️ EDITING MODE: ROW {st.session_state.edit_row_idx}")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.form_submit_button("✅ SUBMIT EDIT", use_container_width=True):
                    if update_google_sheet(st.session_state.edit_row_idx, payload, sheet_target, custom_date=formatted_date):
                        st.success("✅ UPDATED")
                        del st.session_state.edit_row_idx
                        st.rerun()
            with btn_col2:
                if st.form_submit_button("❌ CANCEL", use_container_width=True):
                    del st.session_state.edit_row_idx
                    st.rerun()
        else:
            if st.form_submit_button("🚀 SYNC TO DATABASE", use_container_width=True):
                dup, _ = search_logs(check_id, sheet_target)
                if dup: st.error(f"⚠️ DUPLICATE! {check_id} exists."); st.stop()
                if save_to_google_sheets(st.session_state.current_worker, payload, sheet_target, custom_date=formatted_date):
                    st.success(f"✅ SYNCED FOR {formatted_date}")
                    st.rerun()

    # 5. RECALL SECTION
    with st.expander("🛠️ SEARCH & RECALL FOR CORRECTION"):
        recall_id = st.text_input("Enter ID to edit:")
        if st.button("🔍 FETCH DATA"):
            record, row_idx = search_logs(recall_id, "MANUAL PASS")
            if record:
                st.session_state.edit_row_idx = row_idx
                st.success(f"Loaded Row {row_idx}. Form updated above.")
                st.json(record)
                st.rerun()
            else:
                st.error("❌ Not found.")

