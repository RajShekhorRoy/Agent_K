import json
import re
import requests

# def fetch_mibig_products(mibig_id):
#     #https://mibig.secondarymetabolites.org/repository/BGC0002689.2/BGC0002689.json
#     #https://mibig.secondarymetabolites.org/repository/BGC0002689.2/BGC0002689.gbk
#     ##example
#     url = "https://mibig.secondarymetabolites.org/repository/{0}/{1}.gbk".format(mibig_id,str(mibig_id.split(".")[0]))
#     try:
#         r = requests.get(url)
#         if r.status_code != 200:
#             print(f"Failed to retrieve MIBiG entry: {mibig_id}")
#             return [], []
#         mibig_data = r.json()
#         products = [compound.get("compound") for compound in mibig_data.get("compounds", []) if "compound" in compound]
#
#         ec_numbers = set()
#         for prot in mibig_data.get("proteins", []):
#             if "ec_number" in prot:
#                 ec_numbers.update(prot["ec_number"])
#
#         return products, sorted(ec_numbers)
#     except Exception as e:
#         print(f"Error fetching MIBiG info for {mibig_id}: {e}")
#         return [], []

import os
import requests
from Bio import SeqIO

def download_mibig_gbk_and_extract_ec(mibig_id, output_dir):
    base_id = mibig_id.split(".")[0]
    url = f"https://mibig.secondarymetabolites.org/repository/{mibig_id}/{base_id}.gbk"
    os.makedirs(output_dir, exist_ok=True)
    gbk_path = os.path.join(output_dir, f"{base_id}.gbk")

    try:
        r = requests.get(url)
        if r.status_code != 200:
            print(f"Failed to download GenBank file for {mibig_id}")
            return []
        with open(gbk_path, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"Downloaded GBK to {gbk_path}")

        from Bio import SeqIO
        ec_numbers = set()
        for record in SeqIO.parse(gbk_path, "genbank"):
            for feature in record.features:
                if feature.type == "CDS" and "EC_number" in feature.qualifiers:
                    ec_numbers.update(feature.qualifiers["EC_number"])

        return sorted(ec_numbers)

    except Exception as e:
        print(f"Error processing {mibig_id}: {e}")
        return []

# Example usage:
# mibig_id = "BGC0002689.2"
# output_folder = "./mibig_gbk"
# ec_list = download_mibig_gbk_and_extract_ec(mibig_id, output_folder)
# print(f"EC numbers for {mibig_id}: {ec_list}")
# Example usage:
mibig_id = "BGC0002689.2"
output_folder = "./mibig_gbk"
products = download_mibig_gbk_and_extract_ec(mibig_id,output_folder)
print(f"Products for {mibig_id}: {products}")
# https://mibig.secondarymetabolites.org/repository/BGC0002689.2/BGC0002689.zip