import json
from agent.state import AgentState
from typing import List, Dict, Any

def build_planner_prompt(state: AgentState) -> str:
    """
    The LLM must output JSON ONLY.
    """
    schema = {
        "action": "one of: set_paths | run_antismash | run_pathway | list_outputs | read_file | multi | just_chat",
        "args": {
            "genbank_path": "optional string",
            "antismash_dir": "optional string",
            "pathway_dir": "optional string"    },
        "notes": "short explanation",
    }

    state_view = {
        "genbank_path": state.genbank_path,
        "antismash_done": state.antismash_done,
        "pathway_done": state.pathway_done,
    }

    return (
        "You are the planner. Decide the next action.\n"
        "Return STRICT JSON ONLY. No markdown.\n\n"
        f"Current state:\n{json.dumps(state_view, indent=2)}\n\n"
        "Rules:\n"
        "- If user provides/mentions genbank path or antismash dir or pathway dir or analysis dir, choose set_paths.\n"
        "- If user asks to run antiSMASH, choose run_antismash.\n"
        "- If user asks pathway/product analysis, choose run_pathway.\n"
        "- If user asks what outputs exist, choose list_outputs.\n"
        "- If user asks about a specific result file, choose read_file with a relative path.\n"
        "- If multiple are needed, use action=multi with args.steps.\n\n"
        f"JSON schema:\n{json.dumps(schema, indent=2)}\n"
    )

def build_summarizer_prompt(state: AgentState, tool_logs: List[Dict[str, Any]]) -> str:
    state_view = {
        "genbank_path": state.genbank_path,
        "antismash_done": state.antismash_done,
        "pathway_done": state.pathway_done,
    }
    return (
        "You are the final responder.\n"
        "Use tool logs (if any) to answer the user.\n"
        "Be concise and practical.\n\n"
        f"State:\n{json.dumps(state_view, indent=2)}\n\n"
        f"Tool logs:\n{json.dumps(tool_logs, indent=2)}\n\n"
        "If tools failed, explain likely cause and what the user should change.\n"
        "If user asks about BGCs/products/reactions and outputs are available, suggest which files to inspect.\n"
    )
