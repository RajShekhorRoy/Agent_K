import re
import sys

import path,os



def extract_proteins_with_biosynthetic_annotations(genbank_file, output_fasta):
    fasta_entries = []

    with open(genbank_file, "r") as file:
        content = file.read()

    # Line-wise parse to identify all CDS blocks
    lines = content.splitlines()
    current_block = []
    recording = False
    cds_blocks = []

    for line in lines:
        if line.startswith("     CDS             "):
            if current_block:
                cds_blocks.append("\n".join(current_block))
                current_block = []
            recording = True
            current_block.append(line)
        elif recording and line.startswith("                     "):
            current_block.append(line)
        elif recording:
            cds_blocks.append("\n".join(current_block))
            current_block = []
            recording = False

    if current_block:
        cds_blocks.append("\n".join(current_block))

    # Extract protein sequences from CDS blocks with biosynthetic annotations
    for block in cds_blocks:
        # Normalize multi-line qualifiers
        normalized = re.sub(r'\n\s{21}', ' ', block)

      ##  Check for "biosynthetic" in gene_kind or gene_functions
        biosynthetic = (
            re.search(r'/gene_kind="[^"]*biosynthetic[^"]*"', normalized, re.IGNORECASE) or
            re.search(r'/gene_functions="[^"]*biosynthetic[^"]*"', normalized, re.IGNORECASE)
        )
        # biosynthetic = (
        #         re.search(r'/gene_kind="[\s\S]*?biosynthetic[\s\S]*?"', normalized, re.IGNORECASE) or
        #         re.search(r'/gene_functions="[\s\S]*?biosynthetic[\s\S]*?"', normalized, re.IGNORECASE)
        # )

        if not biosynthetic:
            continue

        # Get product name
        product_match = re.search(r'/product="([^"]+)"', normalized)
        product = product_match.group(1).strip() if product_match else "unknown_product"

        # Get translation (protein sequence)
        translation_match = re.search(r'/translation="([^"]+)"', normalized, re.DOTALL)
        if not translation_match:
            continue

        translation = translation_match.group(1).replace(" ", "").replace("\n", "")
        fasta_entries.append(f">{product}\n{translation}\n")

    final_str = ""
    for values in fasta_entries:
        final_str += values.replace(" ","_")

    # Write FASTA file
    with open(output_fasta, "w") as f:


        f.writelines(final_str)

    print(f"✅ Extracted {len(fasta_entries)} biosynthetic protein sequences to: {output_fasta}")

# Example usage

# # Example usage
# if __name__ == "__main__":
#     # inp_file = "../mibig_files/BGC0002689_contig4.gbk"
#     inp_file = sys.argv[1]
#     output_dir = sys.argv[2]
#     output_file =output_dir+"/"+os.path.basename(inp_file).split(".")[0]+".fasta"
#     # extract_proteins_with_biosynthetic_annotations("/home/rajroy/Downloads/BGC0000343.gbk", "../intermediate/biosynthesis_sequences.fasta")
#     extract_proteins_with_biosynthetic_annotations(inp_file, output_file)
#
#
