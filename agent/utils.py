import ast
import json
import os
import re
import tomllib
import pandas as pd
from bs4 import BeautifulSoup


def parse_state_value(text: str):
    text = text.strip()

    if text == "":
        return ""

    lower = text.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null":
        return None

    try:
        return json.loads(text)
    except Exception:
        pass

    try:
        return ast.literal_eval(text)
    except Exception:
        pass

    return text

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


def display_antismash_bgc(_input_file, _output_file,_similarity=0):
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
                            if similarity >_similarity:
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
    return  df,_output_file + "/mibig_hits_with_similarity.json"

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


import pandas as pd

CELL_WIDTH = 25


def format_cell(value, width=CELL_WIDTH):
    text = str(value)
    if len(text) > width:
        return text[:width]
    return text.ljust(width)


def df_to_fixed_width_table(df: pd.DataFrame, width=CELL_WIDTH) -> str:
    lines = []

    # Header
    header = "".join(format_cell(col, width) for col in df.columns)
    separator = "-" * (width * len(df.columns))

    lines.append(header)
    lines.append(separator)

    # Rows
    for _, row in df.iterrows():
        line = "".join(format_cell(val, width) for val in row)
        lines.append(line)

    return "\n".join(lines)



def kegg_pathway_frequency(input_file, col="KEGG_Pathway"):
    """
    Compute frequency of unique KEGG pathways.

    Parameters
    ----------
    df : pandas.DataFrame
        Input dataframe
    col : str
        Column containing KEGG pathway IDs (comma-separated)

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns: KEGG_Pathway, frequency
    """
    df = pd.read_csv(input_file)
    freq_df = (
        df[col]
        .dropna()
        .astype(str)
        .str.split(",")
        .explode()
        .str.strip()
        .value_counts()
        .reset_index()
    )

    freq_df.columns = ["KEGG_Pathway", "frequency"]

    freq_df.sort_values(
        by="frequency",
        ascending=False
    ).reset_index(drop=True)


    return df_to_fixed_width_table(freq_df)

import pandas as pd

def get_products_by_pathway(input_file, pathway_id,
                            pathway_col="KEGG_Pathway",
                            product_col="product_name"):
    df = pd.read_csv(input_file)

    # ✅ keep same length/index as df
    s = df[pathway_col].fillna("").astype(str)

    mask = (
        s.str.split(",")
         .apply(lambda xs: pathway_id in [p.strip() for p in xs])
    )

    products = (
        df.loc[mask, product_col]
          .fillna("")
          .astype(str)
          .tolist()
    )

    final_array = []
    for product in products:
        for inner in product.split(","):   # ✅ split on comma, not ", "
            inner = inner.strip()
            if inner:
                final_array.append(inner)

    # unique, keep order
    final_array = list(dict.fromkeys(final_array))
    return {"products": final_array}


def get_kegg_links_by_pathway(filepath, pathway_id=""):
    links = set()

    with open(filepath, "r") as f:
        for line in f:
            if f"map{pathway_id}" in line:
                try:
                    link = line.split(" : ", 1)[1].strip()
                    links.add(link)
                except IndexError:
                    continue

    return {"link":list(links)[0]}

def handle_details_view (_details)->str:
    products = _details["product"]
    pathway = _details["pathway"]

    content = f"""Possible products : {products} 
    {pathway}
    """

    return  content

# get_products_by_pathway("/home/rajroy/PycharmProjects/Agent_K/outputs/BGC0001184/details/BGC0001184/details.csv","00270")


def get_antismash_run_cmd (_input,_output):
    _as_exec = get_antismash_exec()
    print(_as_exec)
    # return "sudo ~/bin/run_antismash /home/rajroy/PycharmProjects/metabolites/input/consensus_cov.gbff /home/rajroy/antismash_test_121625/  --cb-general   --cb-knownclusters   --cb-subclusters   --asf   --pfam2go   --cc-mibig   --taxon bacteria  --cpu 16"
    return "{0} {1} {2}  --cb-general   --cb-knownclusters   --cb-subclusters   --asf   --pfam2go   --cc-mibig   --taxon bacteria  --cpu 16".format(_as_exec,_input,_output)


def get_toml():

    print(os.path.abspath(".streamlit/config.toml"))
    with open(".streamlit/config.toml", "rb") as f:
        cfg = tomllib.load(f)
    return cfg


def get_antismash_exec():
    cfg= get_toml()
    antismash_exec =  cfg["tools"]["anitsmash_exec_mac"]
    return antismash_exec


def get_emapper():
    cfg= get_toml()
    emapper_exec =  cfg["tools"]["emapper_mac"]
    return emapper_exec