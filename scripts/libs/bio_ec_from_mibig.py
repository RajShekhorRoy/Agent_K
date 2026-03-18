from Bio import SeqIO

def extract_biosynthetic_ec_numbers_from_gbk(gbk_file):
    biosynthetic_ecs = set()
    try:
        for record in SeqIO.parse(gbk_file, "genbank"):
            for feature in record.features:
                if feature.type == "CDS":
                    all_notes = []
                    for key in ["gene_functions", "gene_kind", "note", "function"]:
                        all_notes.extend(feature.qualifiers.get(key, []))
                    ec_numbers = feature.qualifiers.get("EC_number", [])
                    if any("biosynthetic"   in note.lower() for note in all_notes):
                        biosynthetic_ecs.update(ec_numbers)
        return sorted(biosynthetic_ecs)
    except Exception as e:
        print(f"Error reading {gbk_file}: {e}")
        return []

# Example usage:
if __name__ == "__main__":
    gbk_path = "../mibig_files/BGC0002689_contig4.gbk"  # Replace with actual path
    biosynthetic_ecs = extract_biosynthetic_ec_numbers_from_gbk(gbk_path)
    print(f"Biosynthetic EC numbers from GBK: {biosynthetic_ecs}")

