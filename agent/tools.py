import os
import json
import shlex
import subprocess
from typing import Dict, Any, List, Tuple, Optional

from agent.state import AgentState
from agent.utils import ensure_dir, list_files_recursive, read_text_safely
from agent.prompts import build_planner_prompt, build_summarizer_prompt


class ToolRunner:
    def run_cmd(self, cmd: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        parts = shlex.split(cmd)
        try:
            p = subprocess.run(
                parts,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            return {
                "ok": p.returncode == 0,
                "returncode": p.returncode,
                "stdout": p.stdout[-8000:],
                "stderr": p.stderr[-8000:],
                "cmd": cmd,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "cmd": cmd}

    # ---- Domain tools ----
    def tool_set_paths(
        self,
        state: AgentState,
        genbank_path: Optional[str],
        output_dir: Optional[str],
    ) -> AgentState:
        if genbank_path:
            state.genbank_path = os.path.abspath(genbank_path)
        if output_dir:
            state.output_dir = os.path.abspath(output_dir)
            ensure_dir(state.output_dir)
        return state

    def tool_run_antismash(self, state: AgentState) -> Dict[str, Any]:
        if not state.genbank_path:
            return {"ok": False, "error": "genbank_path is not set"}
        ensure_dir(state.output_dir)

        cmd = "bash scripts/run_antismash.sh {gb} {out}".format(
            gb=shlex.quote(state.genbank_path),
            out=shlex.quote(state.output_dir),
        )
        res = self.run_cmd(cmd)
        if res.get("ok"):
            state.antismash_done = True
        return res

    def tool_run_pathway(self, state: AgentState) -> Dict[str, Any]:
        if not state.genbank_path:
            return {"ok": False, "error": "genbank_path is not set"}
        ensure_dir(state.output_dir)

        cmd = "bash scripts/run_pathway_analysis.sh {gb} {out}".format(
            gb=shlex.quote(state.genbank_path),
            out=shlex.quote(state.output_dir),
        )
        res = self.run_cmd(cmd)
        if res.get("ok"):
            state.pathway_done = True
        return res

    def tool_list_outputs(self, state: AgentState) -> Dict[str, Any]:
        ensure_dir(state.output_dir)
        files = list_files_recursive(state.output_dir)
        return {"ok": True, "output_dir": state.output_dir, "files": files[:500]}

    def tool_read_file(self, state: AgentState, rel_path: str) -> Dict[str, Any]:
        abs_path = rel_path
        if not os.path.isabs(rel_path):
            abs_path = os.path.join(state.output_dir, rel_path)

        if not os.path.exists(abs_path):
            return {"ok": False, "error": "File not found: {p}".format(p=abs_path)}

        content = read_text_safely(abs_path, max_chars=12000)
        return {"ok": True, "path": abs_path, "content": content}

    # ---- Agent turn ----
    def agent_turn(
        self,
        llm,
        system_prompt: str,
        user_prompt: str,
        state: AgentState,
        chat_history: List[Dict[str, str]],
    ) -> Tuple[str, AgentState]:

        planner_messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": build_planner_prompt(state)},
        ]

        for m in chat_history[-12:]:
            planner_messages.append({"role": m["role"], "content": m["content"]})
        planner_messages.append({"role": "user", "content": user_prompt})

        plan_text = llm.chat(planner_messages, temperature=0.1)

        plan = None
        try:
            plan = json.loads(plan_text)
        except Exception:
            return plan_text, state

        action = plan.get("action", "just_chat")
        args = plan.get("args", {})

        tool_logs: List[Dict[str, Any]] = []

        if action == "set_paths":
            state = self.tool_set_paths(
                state,
                genbank_path=args.get("genbank_path"),
                output_dir=args.get("output_dir"),
            )
        elif action == "run_antismash":
            tool_logs.append(self.tool_run_antismash(state))
        elif action == "run_pathway":
            tool_logs.append(self.tool_run_pathway(state))
        elif action == "list_outputs":
            tool_logs.append(self.tool_list_outputs(state))
        elif action == "read_file":
            tool_logs.append(self.tool_read_file(state, args.get("path", "")))
        elif action == "multi":
            for step in args.get("steps", []):
                name = step.get("tool")
                a = step.get("args", {})
                if name == "set_paths":
                    state = self.tool_set_paths(state, a.get("genbank_path"), a.get("output_dir"))
                elif name == "run_antismash":
                    tool_logs.append(self.tool_run_antismash(state))
                elif name == "run_pathway":
                    tool_logs.append(self.tool_run_pathway(state))
                elif name == "list_outputs":
                    tool_logs.append(self.tool_list_outputs(state))
                elif name == "read_file":
                    tool_logs.append(self.tool_read_file(state, a.get("path", "")))
        else:
            pass

        summarizer_messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": build_summarizer_prompt(state, tool_logs)},
        ]
        for m in chat_history[-12:]:
            summarizer_messages.append({"role": m["role"], "content": m["content"]})
        summarizer_messages.append({"role": "user", "content": user_prompt})

        final = llm.chat(summarizer_messages, temperature=0.2)
        return final, state
