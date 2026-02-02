import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from agent.state import AgentState
from agent.tools import ToolRunner
from agent.llm_ollama import OllamaChatLLM
from agent.utils import ensure_dir, handle_details_view
from agent.persistence import save_session, load_session

st.set_page_config(page_title="BGC Agent (Qwen + antiSMASH)", layout="centered")

# st.title("BGC Agent")
# st.caption("Local, free LLM via Ollama + Qwen2.5. Runs your scripts and chats about outputs.")

CSS = """
.stChatMessage:has([data-testid="stChatMessageAvatarUser"]) {
    display: flex;
    flex-direction: row-reverse;
    align-itmes: end;
}

[data-testid="stChatMessageAvatarUser"] + [data-testid="stChatMessageContent"] * {
    text-align: right;
}
"""
st.html(f"<style>{CSS}</style>")

# sticky header
st.markdown(
    """
<style>
    div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
        position: sticky;
        top: 2.875rem;
        color: #02665D;
        background-color: white;
        z-index: 999;
        overflow: hidden;
        max-width: 100vw;
        box-sizing: border-box;
    }
    .fixed-header {
        border-bottom: 1px solid black;
    }
</style>
    """,
    unsafe_allow_html=True
)
header = st.container()
header.title("Agent K")
header.write("""<div class='fixed-header'/>""", unsafe_allow_html=True)



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
# table_str = """
# Name      Age   City
# Alice     30    NY
# Bob       25    LA
# Charlie   35    SF
# """
#
# st.text(table_str)

for msg in st.session_state.messages:
    st.set_page_config(layout="wide")
    with st.chat_message(msg["role"]):
        if  "condition" in msg :
            if msg["condition"] == "TABLE":
                st.code(msg["content"])
            elif msg["condition"] == "DETAILS":
                st.markdown(msg["content"].splitlines()[0])
                components.iframe(msg["content"].splitlines()[1], width="100%", height=1000,scrolling=True)
            else:
                st.markdown(msg["content"])


        else:
            st.markdown(msg["content"])

user_text = st.chat_input("Type a message...")

def add_msg(role, content,condition=""):
    st.session_state.messages.append({"role": role, "content": content, "condition": condition})

if user_text:
    st.set_page_config(layout="wide")

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
           # df = pd.DataFrame(json.loads(agent_reply))
           add_msg("assistant", agent_reply ,special_condition)
       elif special_condition == "DETAILS" :
           str_message = handle_details_view(agent_reply.get("Details"))
           add_msg("assistant", str_message ,special_condition)

    else:
        add_msg("assistant", agent_reply)



    # add_msg("assistant", agent_reply)

    # Persist after each turn (messages + full state including artifacts)
    ensure_dir(st.session_state.state.output_dir)

    save_session(st.session_state.state.output_dir, st.session_state.state, st.session_state.messages  )


    with st.chat_message("assistant"):
        if special_condition == "TABLE":
            st.code(agent_reply)
        elif special_condition == "DETAILS" :
            st.markdown(agent_reply['Details']['product'])
            components.iframe(agent_reply['Details']['pathway'], width="100%",height=1000,scrolling=True)
        else:
            st.markdown(agent_reply)
