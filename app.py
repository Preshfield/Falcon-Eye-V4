import streamlit as st
import os, io, json
from datetime import datetime, timedelta, timezone
from streamlit_gsheets import GSheetsConnection
from gtts import gTTS
import PyPDF2
from streamlit_mic_recorder import speech_to_text
from streamlit_pdf_viewer import pdf_viewer
import openai
import pandas as pd

# 1. LOAD EXTERNAL CSS
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(page_title="Falcon Eye Gate4", layout="wide", page_icon="🦅")
local_css("css/style.css")

# ====================== GOOGLE SHEETS CONNECTION ======================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_user_memory(username):
    try:
        # Pulls from the 'Memory' tab of your sheet
        df = conn.read(worksheet="Memory", ttl=0)
        user_df = df[df['Worker'] == username]
        return user_df[['role', 'content']].to_dict('records')
    except:
        return []

def commit_memory_to_sheet(username, role, content):
    try:
        df = conn.read(worksheet="Memory", ttl=0)
        new_row = pd.DataFrame([{"Worker": username, "role": role, "content": content}])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="Memory", data=updated_df)
    except Exception as e:
        st.error(f"Memory Sync Error: {e}")

def save_log_to_sheet(worker, log_entry):
    try:
        df = conn.read(worksheet="Logs", ttl=0)
        timestamp = datetime.now(timezone(timedelta(hours=4))).strftime("%Y-%m-%d %H:%M:%S")
        new_log = pd.DataFrame([{"Timestamp": timestamp, "Worker": worker, "Log_Entry": log_entry}])
        updated_logs = pd.concat([df, new_log], ignore_index=True)
        conn.update(worksheet="Logs", data=updated_logs)
    except Exception as e:
        st.error(f"Log Sync Error: {e}")

# ====================== SYSTEM ENGINES ======================
def digest_manual():
    if os.path.exists("gate_manual.pdf"):
        try:
            with open("gate_manual.pdf", "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "".join([page.extract_text() for page in reader.pages])
        except: return ""
    return ""

def falcon_query(prompt: str, mode: str, username: str) -> str:
    manual_context = digest_manual()
    client = openai.OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

    if mode == "Gate 4 Protocol":
        sys_rules = f"You are a Gate Security AI. Use ONLY this manual: {manual_context}. Be firm and precise."
    elif mode == "Driver Instruction":
        sys_rules = "Short, clear safety instructions for truck drivers. Professional translator."
    else:
        sys_rules = "Real-Time Intelligence Engine. Date: April 20, 2026. UAE Law Focus."

    # BUILD PERMANENT CONTEXT
    user_history = get_user_memory(username)
    conversation = [{"role": "system", "content": sys_rules}]
    for msg in user_history[-10:]: # Last 10 exchanges for speed
        conversation.append(msg)
    conversation.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(model="deepseek-chat", messages=conversation)
        resp = completion.choices[0].message.content
        
        # PERSIST TO GOOGLE SHEETS
        commit_memory_to_sheet(username, "user", prompt)
        commit_memory_to_sheet(username, "assistant", resp)
        return resp
    except Exception as e:
        return f"ENGINE ERROR: {e}"

# ====================== AUTHENTICATION ======================
WORKER_DB = {"Precious": "Falcon01", "Bambi": "Nancy", "Mr_Ali": "Ali"}

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🦅 FALCON EYE | LOGIN")
    user_id = st.selectbox("USER:", list(WORKER_DB.keys()))
    pwd = st.text_input("PASSWORD:", type="password")
    if st.button("SIGN IN"):
        if pwd == WORKER_DB[user_id]:
            st.session_state.auth = True
            st.session_state.current_worker = user_id
            st.rerun()
    st.stop()

# ====================== DASHBOARD UI ======================
if st.button("🔒 LOGOUT"):
    st.session_state.auth = False
    st.rerun()

dubai_time = datetime.now(timezone(timedelta(hours=4))).strftime("%H:%M")
st.markdown(f'<div class="custom-header"><b>Active Station:</b> {st.session_state.current_worker} | {dubai_time} GST</div>', unsafe_allow_html=True)

t1, t2, t3, t4 = st.tabs(["🛰️ INTELLIGENCE", "📖 PROTOCOLS", "📝 LOGS", "🔍 AUDIT"])

with t1:
    st.subheader("🔍 Knowledge Scan")
    k_mode = st.radio("Scope:", ["Gate 4 Protocol", "Global Knowledge"], horizontal=True)
    k_query = st.text_input("Search protocols...", key="k_scan")
    if k_query: st.info(falcon_query(k_query, k_mode, st.session_state.current_worker))

    st.divider()
    st.subheader("🚛 Driver Intercom")
    # THE COMPLETE TRANSLATOR ARRAY
    all_langs = {"Arabic": "ar", "Urdu": "ur", "Bengali": "bn", "Hindi": "hi", "Tagalog": "tl", "Pashto": "ps", "Malayalam": "ml", "Punjabi": "pa", "English": "en"}
    d_lang = st.selectbox("Driver Language:", list(all_langs.keys()))
    d_reply = st.chat_input("Enter command for driver...")
    if d_reply:
        trans = falcon_query(f"Translate to {d_lang}: {d_reply}", "Driver Instruction", st.session_state.current_worker)
        st.success(f"**Replied:** {trans}")
        tts = gTTS(text=trans, lang=all_langs[d_lang])
        stream = io.BytesIO()
        tts.write_to_fp(stream)
        st.audio(stream.getvalue(), format="audio/mpeg", autoplay=True)

with t2:
    if os.path.exists("gate_manual.pdf"):
        pdf_viewer("gate_manual.pdf", height=700)

with t3:
    st.subheader("📋 Security Mission Logs")
    notes = st.text_area("Observations:", placeholder="Enter vehicle plate or event...")
    if st.button("🚀 ARCHIVE LOG TO CLOUD"):
        if notes:
            report = falcon_query(f"Format this log: {notes} | Officer: {st.session_state.current_worker}", "Gate 4 Protocol", st.session_state.current_worker)
            st.code(report)
            save_log_to_sheet(st.session_state.current_worker, report)
            st.success("✅ Log Permanently Archived in Google Database.")

with t4:
    st.subheader("🔎 Accountability Audit")
    search_q = st.text_input("Audit Search (Plate, Name, Keyword):")
    if search_q:
        logs_df = conn.read(worksheet="Logs", ttl=0)
        results = logs_df[logs_df['Log_Entry'].str.contains(search_q, case=False, na=False)]
        if not results.empty:
            st.write(f"Found {len(results)} matches:")
            for _, row in results.iterrows():
                st.warning(f"**{row['Timestamp']}** | {row['Worker']}\n\n{row['Log_Entry']}")
        else:
            st.error("No records found in the vault.")
        st.download_button("📥 Download Full Log History", log_history, file_name="falcon_eye_logs.txt")
    else:
        st.caption("No saved logs found in the vault.")

