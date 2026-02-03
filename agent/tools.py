import csv
import os
import json
import shlex
import subprocess
import time
from typing import Dict, Any, List, Tuple, Optional



from agent.state import AgentState
from agent.utils import ensure_dir, list_files_recursive, read_text_safely, display_antismash_bgc, log_to_file, \
    parse_plan_json, df_to_fixed_width_table, kegg_pathway_frequency, get_products_by_pathway, get_kegg_links_by_pathway
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
    def tool_set_paths (
        self,
        state: AgentState,
        genbank_path: Optional[str],
        antismash_dir: Optional[str],
        pathway_dir: Optional[str],
        output_dir: Optional[str],
    ) -> AgentState:
        if genbank_path:
            state.genbank_path = os.path.abspath(genbank_path)
        if antismash_dir:
            state.antismash_dir = os.path.abspath(antismash_dir)
            ensure_dir(state.antismash_dir)
            if os.path.exists(os.path.join(state.antismash_dir, "index.html")):
                print(os.path.join(state.antismash_dir, "index.html"))
                state.antismash_done = True
        if pathway_dir:
            state.pathway_dir = os.path.abspath(pathway_dir)
            ensure_dir(state.pathway_dir)
        if output_dir:
            state.output_dir = os.path.abspath(output_dir)
            ensure_dir(state.output_dir)
        return state

    def set_bgc_id(self,
                state: AgentState,
                bgc_id: str)-> AgentState:
        if bgc_id:
            state.bgc_id = bgc_id.split(".")[0]
        return state

    ####main function call
    ##currently unavailable
    def tool_run_antismash(self, state: AgentState) -> Dict[str, Any]:
        if not state.genbank_path:
            return {"ok": False, "error": "genbank_path is not set"}
        ensure_dir(state.antismash_dir)

        cmd = "bash scripts/run_antismash.sh {gb} {out}".format(
            gb=shlex.quote(state.genbank_path),
            out=shlex.quote(state.antismash_dir),
        )
        res = self.run_cmd(cmd)
        if res.get("ok"):
            state.antismash_done = True
        return res

####main function call
    def tool_run_pathway(self, state: AgentState) ->  Any:


        _input_dir = state.antismash_dir+"/"
        _output_dir = state.output_dir+"/"+str(state.bgc_id)+"/"
        # ensure_dir(state.pathway_dir)
        ensure_dir(_output_dir)
        cmd = "python /home/rajroy/PycharmProjects/metabolites/all_bgc_AS_map_agentic_version.py {0} {1} {2}".format(_input_dir,_output_dir,str(state.bgc_id.split("_")[0] )       )
        res = os.system(cmd)
        if res==0:
            state.pathway_done = True
            return   "Analysis done and saved in here "+ _output_dir
        else:
            return "Failed to run pathway"

    def joint_similarity_output(self, _mibig,_frequency):


        return

    def get_pathway(self, state: AgentState) ->Any:

        details_dir = state.output_dir + "/" + str(state.bgc_id) + "/details/"+str(state.bgc_id)+"/details.csv"
        mibig_similarity = state.output_dir + "/" + str(state.bgc_id) + "/mibig_hits_with_similarity.csv"

        # product_file = state.output_dir + "/" + str(state.bgc_id) + "/details/product_mapped.txt"
        if not os.path.exists(details_dir):
            return {"ok": False, "error": "details_dir not found{0}".format(details_dir)}

        if not os.path.exists(mibig_similarity):
            return {"ok": False, "error": "Antismash details not found not found{0}".format(mibig_similarity)}


        mibig_similarity_values = csv.reader(mibig_similarity)

        pathway_values = kegg_pathway_frequency(details_dir)
        #normalized values

        #insert similarity

        #score


        return {"ok": True, "pathway_values": pathway_values}

    def show_pathway_details(self, state: AgentState,pathway_id) ->Any:
        details_dir = state.output_dir + "/" + str(state.bgc_id) + "/details/" + str(state.bgc_id) + "/details.csv"
        map_file = state.output_dir + "/" + str(state.bgc_id) + "/details/"+ str(state.bgc_id) +"/product_mapped.txt"
        possible_products = get_products_by_pathway(details_dir, pathway_id)
        product_str = "Possible products are :"
        for values in possible_products['products']:
            product_str += str(values)+", "

        mapped_link = get_kegg_links_by_pathway(map_file, pathway_id)['link']
        return {"ok": True, "Details": {"product": product_str, "pathway": mapped_link}}

    def tool_list_outputs(self, state: AgentState) -> Dict[str, Any]:
        ensure_dir(state.output_dir)
        files = list_files_recursive(state.output_dir)
        return {"ok": True, "output_dir": state.output_dir, "files": files[:500]}

    def tool_read_antisamsh_bgc(self, state):

        input_dir =     str (state.antismash_dir) + "/index.html"
        output_dir =  str(state.output_dir)+"/"
        ensure_dir(output_dir)

        if not input_dir:
            return {"ok": False, "error": "antismash_dir not set in state"}

        json_data, file_path = display_antismash_bgc(input_dir, output_dir,state.similarity)

        return {"ok": True, "json_data": json_data, "file_path": file_path}

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
    ) -> Tuple[Any, AgentState,Any]:

        special_condition = None

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
            plan = parse_plan_json(plan_text)
        except Exception:
            return plan_text, state, special_condition

        action = plan.get("action", "just_chat")
        args = plan.get("args", {})
        print("PLAN JSON:", plan)

        tool_logs: List[Dict[str, Any]] = []
        print(action)

        if action == "set_paths":
            state = self.tool_set_paths(
                state,
                genbank_path=args.get("genbank_path"),
                antismash_dir=args.get("antismash_dir"),
                pathway_dir=args.get("pathway_dir"),
                output_dir=args.get("output_dir"),
            )
        elif action == "run_antismash":
            tool_logs.append(self.tool_run_antismash(state))
            return "Feature not available yet", state, special_condition
        elif action=="set_bgc_id":
            state = self.set_bgc_id(
                state,
                bgc_id=args.get("bgc_id"))
            return "{0} is set as priority".format(args.get("bgc_id")), state,special_condition
        elif action == "run_pathway":
            if args.get("bgc_id") != None:
                state = self.set_bgc_id(state, bgc_id=args.get("bgc_id"))
            if state.bgc_id != None and state.antismash_dir != None:

                tool_logs.append(self.tool_run_pathway(state))

                pathway_freq, special_condition = self.get_pathways(state)

                return pathway_freq , state,special_condition
            else:
                return "bgc_id or antismash_dir not set", state ,special_condition
        # elif action == "list_outputs":
        #     tool_logs.append(self.tool_list_outputs(state))
        # elif action == "read_file":
        #     tool_logs.append(self.tool_read_file(state, args.get("path", "")))
        elif action == "show_pathway_details":
            if args.get("pathway_id") != None:
                pathway_details = self.show_pathway_details(state,args.get("pathway_id"))
                special_condition = "DETAILS"
                return  pathway_details, state,special_condition
            else:
                special_condition = None
                return "Choose the pathway please", state, special_condition
        elif action == "antismash_done":
            state.antismash_done = True
        elif action == "display_bgc_antismash":
            log_to_file("display_bgc_antismash running")

            try:
                state =self.get_similarity(args, state)

                if args.get("antismash_dir") != None:
                    state.antismash_dir = args.get("antismash_dir")
                    state.antismash_done = True

                response_data = self.tool_read_antisamsh_bgc(state)
                res= tool_logs.append(response_data)
                special_condition = "TABLE"
                return  df_to_fixed_width_table (response_data['json_data']), state,special_condition
            except:
                log_to_file("error here")
                return json.dumps("error", indent=2), state, special_condition

        elif action == "get_pathway":
            state = self.set_bgc_id( state, bgc_id=args.get("bgc_id"))

            pathway_freq, special_condition = self.get_pathways(state)
            return pathway_freq, state, special_condition
        # elif action == "multi":
        #     for step in args.get("steps", []):
        #         name = step.get("tool")
        #         a = step.get("args", {})
        #         if name == "set_paths":
        #             state = self.tool_set_paths(state, a.get("genbank_path"), a.get("output_dir"))
        #         elif name == "run_antismash":
        #             tool_logs.append(self.tool_run_antismash(state))
        #         elif name == "run_pathway":
        #             tool_logs.append(self.tool_run_pathway(state))
        #         elif name == "list_outputs":
        #             tool_logs.append(self.tool_list_outputs(state))
        #         elif name == "read_file":
        #             tool_logs.append(self.tool_read_file(state, a.get("path", "")))
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
        return final, state, special_condition

    def get_similarity(self, args, state: AgentState):
        if args.get("similarity") != None:
            similarity = float(args.get("similarity"))
            if similarity > 1:
                similarity = similarity / 100.0
                state.similarity = similarity
            else:
                state.similarity = similarity

        else:
            state.similarity = 0
        return state

    def get_pathways(self, state: AgentState) -> tuple[Any, str]:
        map_file = state.output_dir + "/" + str(state.bgc_id) + "/details/" + str(
            state.bgc_id) + "/product_mapped.txt"
        if not os.path.exists(map_file):
            self.tool_run_pathway(state)

        pathway_freq = self.get_pathway(state)['pathway_values']
        special_condition = "TABLE"
        return pathway_freq, special_condition
