import requests
from collections import Counter

def get_kegg_pathways_from_ec(ec_number):
    """
    Given an EC number (e.g., "1.3.1.28"), query KEGG and return all associated pathway IDs.
    """
    try:
        response = requests.get(f"https://rest.kegg.jp/get/ec:{ec_number}")
        if not response.ok:
            print(f"Failed to fetch KEGG entry for EC: {ec_number}")
            return []

        pathways = []
        in_pathway_section = False
        for line in response.text.strip().split("\n"):
            if line.startswith("PATHWAY"):
                in_pathway_section = True
                parts = line.split()
                if len(parts) >= 2:
                    pathways.append(parts[1])
            elif in_pathway_section and line.startswith("            "):
                parts = line.strip().split()
                if len(parts) >= 1:
                    pathways.append(parts[0])
            else:
                in_pathway_section = False

        return pathways
    except Exception as e:
        print(f"Error querying KEGG for EC {ec_number}: {e}")
        return []

# Example usage
ecs = ['1.-.-.-', '1.14.19.3', '1.15.1.1', '1.3.1.28', '5.4.4.2']
for ec in ecs:
    kegg_paths = get_kegg_pathways_from_ec(ec)
    print(f"KEGG Pathways for EC {ec}: {kegg_paths}")
