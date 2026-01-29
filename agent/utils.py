import json
import os
import re

import pandas as pd
from bs4 import BeautifulSoup


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def list_files_recursive(root: str):
    out = []
    for base, _, files in os.walk(root):
        for f in files:
            p = os.path.join(base, f)
            out.append(os.path.relpath(p, root))
    out.sort()
    return out

def read_text_safely(path: str, max_chars: int = 12000) -> str:
    # Best-effort text read; you can expand for JSON/CSV parsing later.
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        txt = data.decode("utf-8", errors="replace")
    except Exception:
        txt = str(data)
    if len(txt) > max_chars:
        txt = txt[:max_chars] + "\n...[truncated]..."
    return txt


from datetime import datetime

LOG_FILE = "debug.log"

def log_to_file(message: str):
    with open(LOG_FILE, "a") as f:
        print(os.path.abspath(LOG_FILE))
        f.write(f"\n[{datetime.now()}]\n")
        f.write(message)
        f.write("\n" + "="*80 + "\n")
def remove_duplicates_on_key(dict_list):
    """
    Removes duplicate entries based on (Contig, Region, BGC_ID).
    Keeps the first occurrence and drops any additional duplicates.
    Similarity is ignored for duplication check.
    """
    seen = set()
    result = []
    for d in dict_list:
        key = (d.get("Contig"), d.get("Region"), d.get("BGC_ID"))
        if key not in seen:
            seen.add(key)
            result.append(d)
    return result


def display_antismash_bgc(_input_file, _output_file):
    if not _input_file:
        return {"ok": False, "error": "antismash_dir not set in state"}

    with open(_input_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    # Extract BGC hits with similarity
    mibig_hits = []
    for region in soup.find_all("div", class_="page"):
        region_id = region.get("id")
        if region_id and region_id.startswith("r"):
            heading = region.find("div", class_="heading")
            if heading and " - " in heading.text:
                parts = heading.text.strip().split(" - ")
                contig = parts[0].strip()
                region_name = parts[1].strip()

                # Look inside MIBiG comparison table
                comparison = region.find("div", class_="comparison-MIBiG")
                if comparison:
                    for row in comparison.find_all("tr", class_="cc-heat-row"):
                        accession = row.get("data-accession", "").split(":")[0]
                        cells = row.find_all("td")
                        similarity = None

                        for cell in cells:
                            try:
                                val = float(cell.text.strip())
                                similarity = val
                                break
                            except:
                                continue

                        if accession:
                            mibig_hits.append({
                                "Contig": contig,
                                "Region": region_name,
                                "BGC_ID": accession,
                                "Similarity": similarity
                            })

    # df = pd.DataFrame(mibig_hits)
    removed_dict = remove_duplicates_on_key(mibig_hits)
    df = pd.DataFrame(removed_dict)
    # df = pd.DataFrame.from_dict(removed_dict, orient="records")
    df.to_json(_output_file + "/mibig_hits_with_similarity.json", index=False)
    json_str = df.to_json(orient="records")
    return   json_str,_output_file + "/mibig_hits_with_similarity.json"

def parse_plan_json(text: str):
    # 1. Remove markdown code fences if present
    text = text.strip()

    # Remove ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text)
        text = re.sub(r"```$", "", text)
        text = text.strip()

    # 2. Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Fallback: extract first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in planner output:\n{text}")

    return json.loads(match.group(0))

def to_chat_multiline(s: str) -> str:
    # if the string contains literal backslash-n, fix it
    s = s.replace("\\n", "\n")

    # optional: if it begins/ends with quotes, strip them
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]

    # make sure chat renderer preserves newlines and spacing
    return f"```text\n{s}\n```"

def json_to_markdown_table(input_data) -> str:
    """
    Accepts:
      - dict
      - list[dict]
      - {"rows": list[dict]}
      - JSON string of any of the above

    Returns:
      - Markdown table string
    """

    # Step 1: Normalize input
    if isinstance(input_data, str):
        input_data = json.loads(input_data)

    if isinstance(input_data, dict) and "rows" in input_data:
        rows = input_data["rows"]
    elif isinstance(input_data, dict):
        rows = [input_data]
    elif isinstance(input_data, list):
        rows = input_data
    else:
        return f"```text \n{input_data}\n```"

    if not rows:
        return "_No data available_"

    # Step 2: Auto-extract column headers
    columns = list(rows[0].keys())

    # Step 3: Build markdown table
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"

    body = []
    for row in rows:
        body.append(
            "| " + " | ".join(str(row.get(col, "")) for col in columns) + " |"
        )

    return to_chat_multiline( "\n".join([header, separator] + body))