import os

from Bio import SeqIO
from sphinx.util import requests


def download_mibig_gbk(mibig_id, output_dir):
    output_dir = output_dir + "/mibig/"
    base_id = mibig_id.split(".")[0]
    url = f"https://mibig.secondarymetabolites.org/repository/{mibig_id}/{base_id}.gbk"
    os.makedirs(output_dir, exist_ok=True)
    gbk_path = os.path.join(output_dir, f"{base_id}.gbk")
    biosynthetic_ecs = set()
    try:
        r = requests.get(url)
        if r.status_code != 200:
            print(f"Failed to download GenBank file for {mibig_id}")
            return False
        with open(gbk_path, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"Downloaded GBK to {gbk_path}")


        for record in SeqIO.parse(gbk_path, "genbank"):
            for feature in record.features:
                if feature.type == "CDS":
                    all_notes = []
                    for key in ["gene_functions", "gene_kind", "note", "function"]:
                        all_notes.extend(feature.qualifiers.get(key, []))
                    ec_numbers = feature.qualifiers.get("EC_number", [])
                    if any("biosynthetic" in note.lower() for note in all_notes):
                        biosynthetic_ecs.update(ec_numbers)
        return sorted(biosynthetic_ecs)
    except Exception as e:
        print(f"Error reading {gbk_path}: {e}")
        return []