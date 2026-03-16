import os
import json
import ast
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from agent.frontend_asset import STICKY_HEADER, button_style
from agent.prompts import get_system_prompt
from agent.state import AgentState
from agent.tools import ToolRunner
from agent.llm_ollama import OllamaChatLLM
from agent.utils import ensure_dir, handle_details_view, parse_state_value
from agent.persistence import (
    save_session,
    load_session,
    chat_output_dir,
    list_sessions,
    delete_session,
    session_exists,
)

st.markdown(button_style, unsafe_allow_html=True)
st.set_page_config(page_title="BGC Agent (Qwen + antiSMASH)", layout="wide")

CSS = """
.stChatMessage:has([data-testid="stChatMessageAvatarUser"]) {
    display: flex;
    flex-direction: row-reverse;
    align-items: end;
}

[data-testid="stChatMessageAvatarUser"] + [data-testid="stChatMessageContent"] * {
    text-align: right;
}
"""
st.html(f"<style>{CSS}</style>")

st.markdown(STICKY_HEADER, unsafe_allow_html=True)
header = st.container()
header.title("Agent K")
header.write("""<div class='fixed-header'/>""", unsafe_allow_html=True)

NON_EDITABLE_STATE_FIELDS = {"notes", "artifacts", "code_to_exec"}



def sync_state_editor_from_state(state: AgentState):
    state_dict = state.model_dump()
    for k, v in state_dict.items():
        if k in NON_EDITABLE_STATE_FIELDS:
            continue
        st.session_state[f"edit_{k}"] = (
            json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        )


def load_selected_session(base_output_dir: str, chat_name: str):
    loaded = load_session(chat_output_dir(base_output_dir, chat_name))

    if loaded and "state" in loaded:
        st.session_state.state = AgentState(**loaded["state"])
    else:
        st.session_state.state = AgentState(
            output_dir=chat_output_dir(base_output_dir, chat_name)
        )

    if loaded and "messages" in loaded:
        st.session_state.messages = loaded["messages"]
    else:
        st.session_state.messages = []

    sync_state_editor_from_state(st.session_state.state)


# -------------------------
# Base output dir
# -------------------------
base_output_dir = os.path.abspath("./output")
ensure_dir(base_output_dir)

# -------------------------
# Session state init
# -------------------------
if "current_chat_name" not in st.session_state:
    existing_sessions = list_sessions(base_output_dir)
    st.session_state.current_chat_name = (
        existing_sessions[0] if existing_sessions else "New_Chat"
    )
    if st.session_state.current_chat_name != None:
        TITLE = st.session_state.current_chat_name
        st.session_state.refresh_state_editor = True
        # header.title("Agent K {0}".format())


if "pending_delete_chat" not in st.session_state:
    st.session_state.pending_delete_chat = None

if "refresh_state_editor" not in st.session_state:
    st.session_state.refresh_state_editor = False

# -------------------------
# Session init
# -------------------------
if "state" not in st.session_state or "messages" not in st.session_state:
    load_selected_session(base_output_dir, st.session_state.current_chat_name)

# Keep output_dir aligned with the selected chat
current_output_dir = chat_output_dir(
    base_output_dir, st.session_state.current_chat_name
)
if st.session_state.state.output_dir != current_output_dir:
    st.session_state.state = st.session_state.state.model_copy(
        update={"output_dir": current_output_dir}
    )
    st.session_state.refresh_state_editor = True

# Refresh editor values before widgets are rendered
if st.session_state.refresh_state_editor:
    sync_state_editor_from_state(st.session_state.state)
    st.session_state.refresh_state_editor = False

# -------------------------
# Sidebar: settings + session manager
# -------------------------
with st.sidebar:
    st.header("Settings")
    model = st.text_input("Ollama model", value="qwen2.5:7b-instruct")
    ollama_url = st.text_input("Ollama URL", value="http://127.0.0.1:11434")

    st.markdown("---")
    st.header("Sessions")

    existing_sessions = list_sessions(base_output_dir)

    new_chat_name = st.text_input("New chat name", value="", key="new_chat_name")

    if st.button("Create New Chat", use_container_width=True,type="primary",icon="➕"):
        chat_name = new_chat_name.strip()

        if not chat_name:
            st.error("Please enter a chat name.")
        elif session_exists(base_output_dir, chat_name):
            st.error(f"A chat named '{chat_name}' already exists.")
        else:
            st.session_state.current_chat_name = chat_name
            st.session_state.pending_delete_chat = None
            st.session_state.state = AgentState(
                output_dir=chat_output_dir(base_output_dir, chat_name)
            )
            st.session_state.messages = []
            sync_state_editor_from_state(st.session_state.state)

            save_session(
                st.session_state.state.output_dir,
                st.session_state.state,
                st.session_state.messages,
            )
            st.rerun()

    existing_sessions = list_sessions(base_output_dir)

    if existing_sessions:
        selected_index = (
            existing_sessions.index(st.session_state.current_chat_name)
            if st.session_state.current_chat_name in existing_sessions
            else 0
        )

        selected_chat = st.selectbox(
            "Saved chats",
            options=existing_sessions,
            index=selected_index,
            key="saved_chats_selectbox",
        )

        if selected_chat != st.session_state.current_chat_name:
            st.session_state.current_chat_name = selected_chat
            st.session_state.pending_delete_chat = None
            load_selected_session(base_output_dir, selected_chat)

            st.rerun()

        if st.button("Delete Chat", use_container_width=True,type="secondary",icon="🗑"):
            st.session_state.pending_delete_chat = st.session_state.current_chat_name
            st.rerun()

        if st.session_state.pending_delete_chat == st.session_state.current_chat_name:
            st.warning(
                f"Are you sure you want to delete '{st.session_state.current_chat_name}'?"
            )
            col1, col2 = st.columns(2)

            with col1:
                if st.button("Confirm Delete", use_container_width=True, icon="🛑",type="tertiary"):
                    delete_session(base_output_dir, st.session_state.current_chat_name)

                    remaining = list_sessions(base_output_dir)
                    if remaining:
                        st.session_state.current_chat_name = remaining[0]
                        load_selected_session(
                            base_output_dir,
                            st.session_state.current_chat_name,
                        )
                    else:
                        st.session_state.current_chat_name = "New_Chat"
                        st.session_state.state = AgentState(
                            output_dir=chat_output_dir(base_output_dir, "New_Chat")
                        )
                        st.session_state.messages = []
                        sync_state_editor_from_state(st.session_state.state)

                    st.session_state.pending_delete_chat = None
                    st.rerun()

            with col2:
                if st.button("Cancel", use_container_width=True,type="tertiary"):
                    st.session_state.pending_delete_chat = None
                    st.rerun()

# -------------------------
# Sidebar: live state view
# -------------------------
with st.sidebar:
    st.markdown("---")
    st.header("Agent State (editable)")

    state = st.session_state.state
    state_dict = state.model_dump()

    with st.expander("Variables", expanded=False):
        for k, v in state_dict.items():
            if k in NON_EDITABLE_STATE_FIELDS:
                continue

            if f"edit_{k}" not in st.session_state:
                st.session_state[f"edit_{k}"] = (
                    json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                )

            st.text_input(
                k,
                key=f"edit_{k}",
            )

        if st.button("Apply Changes", key="apply_state_changes",type="primary"):
            updates = {}
            for k in state_dict.keys():
                if k in NON_EDITABLE_STATE_FIELDS:
                    continue
                updates[k] = parse_state_value(st.session_state[f"edit_{k}"])

            st.session_state.state = state.model_copy(update=updates)
            sync_state_editor_from_state(st.session_state.state)

            save_session(
                st.session_state.state.output_dir,
                st.session_state.state,
                st.session_state.messages,
            )
            st.success("Applied.")
            st.rerun()

    # with st.expander("Artifacts", expanded=False):
    #     st.json(st.session_state.state.artifacts)
    #
    # with st.expander("Notes", expanded=False):
    #     st.write(st.session_state.state.notes)

# -------------------------
# LLM + tools
# -------------------------
llm = OllamaChatLLM(base_url=ollama_url, model=model)
tools = ToolRunner()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if "condition" in msg:
            if msg["condition"] == "TABLE":
                st.code(msg["content"])
            elif msg["condition"] == "DETAILS":
                st.markdown(msg["content"].splitlines()[0])
                components.iframe(
                    msg["content"].splitlines()[1],
                    width="100%",
                    height=1000,
                    scrolling=True,
                )
            else:
                st.markdown(msg["content"])
        else:
            st.markdown(msg["content"])

user_text = st.chat_input("Type a message...")


def add_msg(role, content, condition=""):
    st.session_state.messages.append(
        {"role": role, "content": content, "condition": condition}
    )


if user_text:
    add_msg("user", user_text)
    with st.chat_message("user"):
        st.markdown(user_text)

    state = st.session_state.state

    system = get_system_prompt()

    agent_reply, new_state, special_condition = tools.agent_turn(
        llm=llm,
        system_prompt=system,
        user_prompt=user_text,
        state=state,
        chat_history=st.session_state.messages,
    )
    st.session_state.state = new_state
    st.session_state.refresh_state_editor = True

    if special_condition is not None:
        if special_condition == "TABLE":
            add_msg("assistant", agent_reply, special_condition)
        elif special_condition == "DETAILS":
            str_message = handle_details_view(agent_reply.get("Details"))
            add_msg("assistant", str_message, special_condition)
    else:
        add_msg("assistant", agent_reply)

    ensure_dir(st.session_state.state.output_dir)
    save_session(
        st.session_state.state.output_dir,
        st.session_state.state,
        st.session_state.messages,
    )

    with st.chat_message("assistant"):
        if special_condition == "TABLE":
            st.code(agent_reply)
        elif special_condition == "DETAILS":
            st.markdown(agent_reply["Details"]["product"])
            components.iframe(
                agent_reply["Details"]["pathway"],
                width="100%",
                height=1000,
                scrolling=True,
            )
        else:
            st.markdown(agent_reply)

    st.rerun()