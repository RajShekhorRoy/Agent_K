import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
st.set_page_config(layout="wide")
from agent.state import AgentState
from agent.tools import ToolRunner
from agent.llm_ollama import OllamaChatLLM
from agent.utils import ensure_dir
from agent.persistence import save_session, load_session

st.set_page_config(page_title="BGC Agent (Qwen + antiSMASH)", layout="centered")

st.title("BGC Agent")
st.caption("Local, free LLM via Ollama + Qwen2.5. Runs your scripts and chats about outputs.")


# -------------------------
# Sidebar: settings first
# -------------------------
with st.sidebar:
    st.header("Settings")
    model = st.text_input("Ollama model", value="qwen2.5:7b-instruct")
    ollama_url = st.text_input("Ollama URL", value="http://127.0.0.1:11434")
    default_out = st.text_input("Default output dir", value=os.path.abspath("./outputs"))

# Make sure default_out exists (so load/save has somewhere to go)
ensure_dir(default_out)

# -------------------------
# Session init (MUST happen before any use of st.session_state.state/messages)
# -------------------------
loaded = None
if ("state" not in st.session_state) or ("messages" not in st.session_state):
    loaded = load_session(default_out)

# Initialize state safely
if "state" not in st.session_state:
    if loaded and "state" in loaded:
        st.session_state.state = AgentState(**loaded["state"])
    else:
        st.session_state.state = AgentState(output_dir=default_out)

# Initialize messages safely
if "messages" not in st.session_state:
    if loaded and "messages" in loaded:
        st.session_state.messages = loaded["messages"]
    else:
        st.session_state.messages = []

# If user changes default_out in sidebar, optionally “switch” the output dir
# (This keeps things consistent without forcing a full reset.)
# Comment this out if you don't want sidebar changes to alter active state.
if st.session_state.state.output_dir != os.path.abspath(default_out):
    st.session_state.state.output_dir = os.path.abspath(default_out)
    ensure_dir(st.session_state.state.output_dir)

# -------------------------
# Sidebar: live state view (NOW safe)
# -------------------------
with st.sidebar:
    st.markdown("---")
    st.header("Agent State (live)")
    st.json(st.session_state.state.model_dump())

    with st.expander("Artifacts", expanded=False):
        st.json(st.session_state.state.artifacts)

    with st.expander("Notes", expanded=False):
        st.write(st.session_state.state.notes)

# -------------------------
# LLM + tools
# -------------------------
llm = OllamaChatLLM(base_url=ollama_url, model=model)
tools = ToolRunner()
# components.iframe("https://www.kegg.jp/kegg-bin/show_pathway?map01053/R07644/C00022/C00020/C00013/C05821/C00885/R01717/R03037/C04171//image1x", width=1000,height=1000)
# st.html("https://www.kegg.jp/kegg-bin/show_pathway?map01053/R07644/C00022/C00020/C00013/C05821/C00885/R01717/R03037/C04171//image1x")

# components.iframe(
#     src="https://www.kegg.jp/kegg-bin/show_pathway?map01053/R07644/C00022/C00020/C00013/C05821/C00885/R01717/R03037/C04171//image1x",
#     height=800,          # adjust or compute dynamically
#     scrolling=True
# )

# -------------------------
# Render chat history
# -------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_text = st.chat_input("Type a message...")

def add_msg(role, content):
    st.session_state.messages.append({"role": role, "content": content})

if user_text:
    add_msg("user", user_text)
    with st.chat_message("user"):
        st.markdown(user_text)

    state = st.session_state.state

    system = (
        "You are a helpful bioinformatics pipeline assistant.\n"
        "You can ask for missing info (genbank path, anitsmash dir, pathway dir, analysis dir), and you can run tools.\n"
        " pathway dir and analysis dir referes to the same directory."
        "Be concise. When you run tools, explain what you ran and where outputs are.\n"
        "If user asks about outputs, inspect files and summarize.\n"
    )

    agent_reply, new_state,special_condition = tools.agent_turn(
        llm=llm,
        system_prompt=system,
        user_prompt=user_text,
        state=state,
        chat_history=st.session_state.messages,
)
    st.session_state.state = new_state
    if special_condition != None:
       if special_condition == "TABLE":
           df = pd.DataFrame(json.loads(agent_reply))
           add_msg("assistant", agent_reply )
    else:
        add_msg("assistant", agent_reply)



    # add_msg("assistant", agent_reply)

    # Persist after each turn (messages + full state including artifacts)
    ensure_dir(st.session_state.state.output_dir)
    if special_condition  == "TABLE":
        st.session_state.messages.pop()
        st.session_state.messages.append({'role': 'assistant', 'content': 'Table previewed here'})
        save_session(st.session_state.state.output_dir, st.session_state.state, st.session_state.messages  )
    else:
        save_session(st.session_state.state.output_dir, st.session_state.state, st.session_state.messages)

    with st.chat_message("assistant"):
        if special_condition == "TABLE":
            st.table(df)
        else:
            st.markdown(agent_reply)
