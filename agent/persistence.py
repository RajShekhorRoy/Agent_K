import json
import os
import shutil
import re
from typing import Any, Dict, List, Optional
from agent.state import AgentState

SESSION_FILENAME = "session.json"
SESSIONS_DIRNAME = "sessions"


def session_path(output_dir: str) -> str:
    return os.path.join(output_dir, SESSION_FILENAME)


def sessions_root(base_output_dir: str) -> str:
    return os.path.join(base_output_dir, SESSIONS_DIRNAME)


def sanitize_chat_name(chat_name: str) -> str:
    """
    Make the chat name safe to use as a folder name.
    """
    chat_name = chat_name.strip()
    chat_name = re.sub(r"[<>:\"/\\\\|?*]", "_", chat_name)
    chat_name = re.sub(r"\s+", "_", chat_name)
    return chat_name or "new_chat"


def chat_output_dir(base_output_dir: str, chat_name: str) -> str:
    safe_name = sanitize_chat_name(chat_name)
    return os.path.join(sessions_root(base_output_dir), safe_name)


def save_session(output_dir: str, state: AgentState, messages: List[Dict[str, str]]) -> None:
    os.makedirs(output_dir, exist_ok=True)
    payload = {
        "state": state.model_dump(),
        "messages": messages,
    }
    tmp = session_path(output_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, session_path(output_dir))


def load_session(output_dir: str) -> Optional[Dict[str, Any]]:
    path = session_path(output_dir)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload


def list_sessions(base_output_dir: str) -> List[str]:
    root = sessions_root(base_output_dir)
    if not os.path.exists(root):
        return []

    session_names = []
    for name in os.listdir(root):
        full_path = os.path.join(root, name)
        if os.path.isdir(full_path) and os.path.exists(session_path(full_path)):
            session_names.append(name)

    return sorted(session_names)


def delete_session(base_output_dir: str, chat_name: str) -> None:
    path = chat_output_dir(base_output_dir, chat_name)
    if os.path.exists(path):
        shutil.rmtree(path)


def session_exists(base_output_dir: str, chat_name: str) -> bool:
    return os.path.exists(chat_output_dir(base_output_dir, chat_name))