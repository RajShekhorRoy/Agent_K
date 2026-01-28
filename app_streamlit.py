import os
import subprocess
from pathlib import Path
# venv_python = Path(".venv/bin/activate")  # Windows: venv/Scripts/python.exe
# subprocess.run([venv_python, "other_script.py"])

import streamlit as st
from agent.state import AgentState
from agent.tools import ToolRunner
from agent.llm_ollama import OllamaChatLLM
from agent.utils import ensure_dir
from agent.persistence import save_session, load_session

st.set_page_config(page_title="BGC Agent (Qwen + antiSMASH)", layout="centered")

st.title("BGC Agent")
st.caption("Local, free LLM via Ollama + Qwen2.5. Runs your scripts and chats about outputs.")

# Sidebar config
with st.sidebar:
    st.header("Settings")
    model = st.text_input("Ollama model", value="qwen2.5:7b-instruct")
    ollama_url = st.text_input("Ollama URL", value="http://127.0.0.1:11434")
    default_out = st.text_input("Default output dir", value=os.path.abspath("./outputs"))
    st.markdown("---")
    # st.write("Scripts used:")
    # st.code("scripts/run_antismash.sh\nscripts/run_pathway_analysis.sh")

ensure_dir(default_out)

# Initialize state
if "state" not in st.session_state:
    st.session_state.state = AgentState(output_dir=default_out)

if "messages" not in st.session_state:
    st.session_state.messages = []

# LLM + tools
llm = OllamaChatLLM(base_url=ollama_url, model=model)
tools = ToolRunner()

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_text = st.chat_input("Type a message...")

def add_msg(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

if user_text:
    add_msg("user", user_text)
    with st.chat_message("user"):
        st.markdown(user_text)

    # Agent step
    state: AgentState = st.session_state.state

    # System guidance for the agent
    system = (
        "You are a helpful bioinformatics pipeline assistant.\n"
        "You can ask for missing info (genbank path, output dir), and you can run tools.\n"
        "Be concise. When you run tools, explain what you ran and where outputs are.\n"
        "If user asks about outputs, inspect files and summarize.\n"
    )

    # Let agent decide: respond directly or call tool(s)
    agent_reply, new_state = tools.agent_turn(
        llm=llm,
        system_prompt=system,
        user_prompt=user_text,
        state=state,
        chat_history=st.session_state.messages,
    )

    st.session_state.state = new_state

    add_msg("assistant", agent_reply)
    with st.chat_message("assistant"):
        st.markdown(agent_reply)
