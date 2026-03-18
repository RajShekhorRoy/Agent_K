import csv
import sys

from collections import Counter
from typing import List

import requests

def text_file_reader(_file):
    file = open(_file, "r")
    output_array = []
    if file.mode == 'r':
        output_array = file.read().splitlines()
    file.close()

    return output_array

# output_path = "../output/"
def remove_011_012_013(input_list):
    # Convert all elements to strings and filter out those that start with '011', '012', or '013'
    return [item for item in input_list if not str(item).startswith(('01100','01110','01120','01200'',1210','01212','01230','01232'',1250','01240','01220','01310','01320'))]

class QueryResult:
    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __repr__(self):
        return f"<QueryResult query={self.query} preferred_name={self.Preferred_name} EC={self.EC} KEGG_Pathway={self.KEGG_Pathway}>"
def most_common_pathways(ec_pathway_list):
    # Flatten all pathway lists into one
    all_pathways = []
    for pathways in ec_pathway_list:
        all_pathways.append(pathways)
    all_pathways = remove_011_012_013(all_pathways)
    # Count occurrences
    counter = Counter(all_pathways)
    if not counter:
        return [], 0

    # Find the max count
    max_count = max(counter.values())
    most_common = [path for path, count in counter.items() if count == max_count]

    return most_common, max_count

def get_products_for_reaction(reaction_id):
    """Get product compound IDs for a given KEGG reaction."""
    url = f'http://rest.kegg.jp/get/rn:{reaction_id}'
    r = requests.get(url)
    products = []
    if r.status_code == 200:
        lines = r.text.strip().split('\n')
        in_equation = False
        for line in lines:
            if line.startswith('EQUATION'):
                eq = line.split('EQUATION')[1].strip()
            elif line.startswith(' '):
                if 'EQUATION' in line:
                    eq = line.split('EQUATION')[1].strip()
            else:
                continue
        # Example eq: "C00001 + C00002 <=> C00003 + C00004"
        if '=>' in eq:
            reactants, products_txt = eq.split('=>')
        elif '<=>' in eq:
            reactants, products_txt = eq.split('<=>')
        else:
            products_txt = ''
        if products_txt:
            # This part extracts compound ids (Cxxxxx) from products
            for p in products_txt.strip().split('+'):
                c_id = p.strip().split(' ')[-1]  # In case of stoichiometry numbers
                if c_id.startswith('C') and len(c_id) == 6:
                    products.append(c_id)
    return products

def parse_emapper_output(file_path: str) -> List[QueryResult]:
    results = []
    with open(file_path, 'r') as file:
        reader = None
        for line in file:
            if line.startswith("##"):
                continue  # Ignore comments
            if line.startswith("#"):
                # Header line
                headers = line.strip().lstrip("#").split('\t')
                reader = csv.DictReader(file, fieldnames=headers, delimiter='\t')
                continue
            if reader:
                row = line.strip().split('\t')
                if len(row) == len(headers):
                    result = QueryResult(**dict(zip(headers, row)))
                    results.append(result)
    return results
def get_compound_name(compound_id):
    """Get compound name given KEGG compound ID."""
    url = f'http://rest.kegg.jp/get/cpd:{compound_id}'
    r = requests.get(url)
    if r.status_code == 200:
        lines = r.text.strip().split('\n')
        for line in lines:
            if line.startswith('NAME'):
                return line.split('NAME')[1].strip().split(';')[0]
    return compound_id
def get_processed_map_name(_result):
    str_result = str(_result)
    no_str_arr =[]

    for values in str_result.split(","):
        no_str_arr.append(values[-5:])


    return  list(set(no_str_arr))
kegg_id = text_file_reader("/home/rajroy/PycharmProjects/metabolites/kegg_map_ids.txt")
reaction_list = []
all_maps = []
# Example usage
def get_pathway_from_eggmapper_annot(_input,_output):

    parsed_results = parse_emapper_output(_input)
    products_name =[]
    for result in parsed_results:
        print(result)
        str_result = str(result.KEGG_Reaction)
        if len(str_result) > 0:
            for values in str_result.split(","):
                if values.isalnum():
                    reaction_list.append(values)
                else:
                    print("This {0} is invalid".format(values))
        process_path = get_processed_map_name(result.KEGG_Pathway)
        if len(process_path) > 0:
            new_array = process_path
            for values in new_array:
                if values.isalnum():
                    if values[-5:] in kegg_id:
                        all_maps.append(values[-5:])
                else:
                    print("{0} is invalid".format(values))

    print(reaction_list)

    print("Product list")
    print_str = ""
    for reaction in reaction_list:
        print_str = print_str + "\nProducts for Reaction:{0} are :".format(reaction)
        products = get_products_for_reaction(reaction)
        for product in products:
            # print(product)
            name_of_product = get_compound_name(product)
            products_name.append(name_of_product)
            print_str = print_str + name_of_product + ","
    print(print_str)

    common_paths, count = most_common_pathways(all_maps)
    print(common_paths, count)
    for path in common_paths:
        url = "https://rest.kegg.jp/get/map{0}/image2x".format(path.replace("ec", ""))
        res = requests.get(url)
        try_attempts =0
        while try_attempts<5:
            if res.status_code == 200:
                try_attempts =100
                with open(_output + str(path) + ".png", "wb") as f:
                    f.write(res.content)
                print("Saved!", len(res.content), "bytes")
            else:
                try_attempts=try_attempts+1
                print("Failed tried 5 times, map not found:", res.status_code)

    return common_paths,reaction_list,products_name
if __name__ == "__main__":
    # file_path = "/home/rajroy/Downloads/tools/eggnog-mapper/BGC0000343_out.out.emapper.annotations"  # Replace with your actual file
    # file_path = "/home/rajroy/PycharmProjects/metabolites/intermediate/BGC0000888_contig1/BGC0000888_contig1.emapper.annotations"  # Replace with your actual file
    file_path = sys.argv[1]
    output="/home/rajroy/"
    output=sys.argv[2]
    maps = get_pathway_from_eggmapper_annot(file_path,output)
    print(maps)
