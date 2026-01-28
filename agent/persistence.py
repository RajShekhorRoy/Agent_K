import json
import os
from typing import Any, Dict, List, Optional
from agent.state import AgentState

SESSION_FILENAME = "session.json"

def session_path(output_dir: str) -> str:
    return os.path.join(output_dir, SESSION_FILENAME)

def save_session(output_dir: str, state: AgentState, messages: List[Dict[str, str]]) -> None:
    os.makedirs(output_dir, exist_ok=True)
    payload = {
        "state": state.model_dump(),   # pydantic v2
        "messages": messages,
    }
    tmp = session_path(output_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, session_path(output_dir))  # atomic replace

def load_session(output_dir: str) -> Optional[Dict[str, Any]]:
    path = session_path(output_dir)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload
