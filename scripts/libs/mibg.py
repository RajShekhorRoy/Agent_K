from Bio import SeqIO

def extract_ko_terms_from_gbk(gbk_file):
    ko_terms = []
    for record in SeqIO.parse(gbk_file, "genbank"):
        for feature in record.features:
            if feature.type == "CDS":
                if "db_xref" in feature.qualifiers:
                    for ref in feature.qualifiers["db_xref"]:
                        if ref.startswith("KO:"):
                            ko_terms.append(ref.split(":")[1])
    return list(set(ko_terms))  # unique KO terms

# Example
gbk_path = "/home/rajroy/Downloads/BGC0002689.gbk"
ko_ids = extract_ko_terms_from_gbk(gbk_path)
print("KO terms found:", ko_ids)
