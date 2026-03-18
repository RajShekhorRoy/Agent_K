import sys

from bs4 import BeautifulSoup
import pandas as pd
from collections import Counter
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

def Mibig_extractor(_input_file,_output_file):

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
    removed_dict =remove_duplicates_on_key(mibig_hits)
    df = pd.DataFrame(removed_dict)
    # df = pd.DataFrame.from_dict(removed_dict, orient="records")
    df.to_csv(_output_file + "/mibig_hits_with_similarity.csv", index=False)
    return removed_dict
# Load the antiSMASH index.html file


# # Save to CSV or view
#
# if __name__ == '__main__':
#     # _input_file = "/home/rajroy/antismash_results_mibig/consensus_cov/index.html",
#     # output_dir = "/home/rajroy/output_file/"
#     _input_file =sys.argv[1]
#     _output_file = sys.argv[2]
#     df = pd.DataFrame(Mibig_extractor(_input_file,_output_file))
#
# #download done proceed on the next part