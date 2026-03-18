import csv
import sys
import itertools
import time
from collections import Counter
from typing import List
import os
import requests
from eggnog_query_class import map_emapper_to_eggnog
import csv

def text_file_reader(_file):
    file = open(_file, "r")
    output_array = []
    if file.mode == 'r':
        output_array = file.read().splitlines()
    file.close()

    return output_array

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# kegg_id = text_file_reader(SCRIPT_DIR"/kegg_map_ids.txt")
kegg_id =text_file_reader( str(SCRIPT_DIR / "kegg_map_ids.txt"))



def fetch_kegg_reaction_definition(reaction_id):
    """
    Fetch the KEGG reaction 'DEFINITION' field.
    """
    url = f"https://rest.kegg.jp/get/{reaction_id}"
    r = requests.get(url, timeout=15)
    if not r.ok:
        return None
    for line in r.text.splitlines():
        if line.startswith("DEFINITION"):
            return line.replace("DEFINITION", "").strip()
    return None

def export_eggnog_to_csv(objects, fields, filename):
    """
    Export a list of EggnogQueryClass objects to CSV with selected fields.
    :param objects: list of EggnogQueryClass instances
    :param fields: list of field names to export
    :param filename: output CSV file path
    """
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fields)  # Header

        for obj in objects:
            row = []
            for field in fields:
                value = getattr(obj, field, "")
                # Flatten lists to comma-separated strings
                if isinstance(value, list):
                    value = ", ".join(map(str, value))
                row.append(value)
            writer.writerow(row)


def download_kegg_reaction_images(reaction_ids, out_dir="kegg_reactions", pause=0.01):
    """
    Download KEGG reaction mechanism images (GIFs) for a list of reaction IDs.
    Example ID: 'R07644' -> https://www.kegg.jp/Fig/reaction/R07644.gif
    """
    os.makedirs(out_dir, exist_ok=True)
    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "image/*,*/*;q=0.8",
    })
    saved_info = []
    saved, failed = [], []
    for rid in reaction_ids:
        rid = rid.strip()
        if not rid:
            continue
        url = f"https://www.kegg.jp/Fig/reaction/{rid}.gif"
        out_path = os.path.join(out_dir, f"{rid}.gif")
        try:
            r = sess.get(url, timeout=20)
            if r.ok and r.headers.get("Content-Type", "").startswith("image/"):
                with open(out_path, "wb") as f:
                    f.write(r.content)
                saved.append(out_path)
                # polite pause to avoid hammering their server
                time.sleep(pause)
            else:
                failed.append((rid, r.status_code, r.headers.get("Content-Type", "")))
        except requests.RequestException as e:
            failed.append((rid, str(e), ""))

        definition = fetch_kegg_reaction_definition(rid)

        saved_info.append({
            "Reaction_ID": rid,
            "Definition": definition if definition else "",
        })
        time.sleep(pause)

    csv_file = out_dir + "/kegg_reactions.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Reaction_ID", "Definition"])
        writer.writeheader()
        writer.writerows(saved_info)

    return saved_info


# output_path = "../output/"
def remove_011_012_013(input_list):
    # Convert all elements to strings and filter out those that start with '011', '012', or '013'
    return [item for item in input_list if not str(item).startswith(('01100', '01110', '01120', '01200'',1210', '01212',
                                                                     '01230', '01232'',1250', '01240', '01220', '01310',
                                                                     '01320'))]


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
    time.sleep(0.09)
    return compound_id


def remove_duplicate(_arr):
    return list(set(_arr))


def get_processed_map_name(_result):
    str_result = str(_result)
    no_str_arr = []

    for values in str_result.split(","):
        no_str_arr.append(values[-5:])

    return list(set(no_str_arr))


def download_kegg_map(_map_ids, _output_path):
    for map_id in _map_ids:
        url = "https://rest.kegg.jp/get/map{0}/image2x".format(map_id.replace("ec", ""))
        res = requests.get(url)
        try_attempts = 0
        while try_attempts < 5:
            if res.status_code == 200:
                try_attempts = 100
                with open(_output_path + str(map_id) + ".png", "wb") as f:
                    f.write(res.content)
                print("Saved!", len(res.content), "bytes")
            else:
                try_attempts = try_attempts + 1
                print("Failed tried 5 times, map not found:", res.status_code)

    return None


# Example usage
def get_pathway_from_eggmapper_annot(_input, _output):
    reaction_list = []
    all_maps = []

    ##reorder find common paths and then
    parsed_results = parse_emapper_output(_input)
    products_name = []

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
        try_attempts = 0
        while try_attempts < 5:
            if res.status_code == 200:
                try_attempts = 100
                with open(_output + str(path) + ".png", "wb") as f:
                    f.write(res.content)
                print("Saved!", len(res.content), "bytes")
            else:
                try_attempts = try_attempts + 1
                print("Failed tried 5 times, map not found:", res.status_code)

    return common_paths, reaction_list, products_name


def write2File(_filename, _cont):
    with open(_filename, "w") as f:
        f.writelines(_cont)
        f.close()

def list2query_string(_list):
    query_str = ""
    for values in _list:
        query_str = query_str + "{0}/".format(values)

    return query_str
def get_highlighted_map_links(_eggnog_object, _dir):
    mapping_string = ""
    mapping_file = _dir + "/product_mapped.txt"
    unique_pathway = list(set(x for inner in [d.KEGG_Pathway for d in _eggnog_object] for x in inner))
    query_dict ={}
    for data in _eggnog_object:
        for map in data.KEGG_Pathway:
            if map in unique_pathway:
                try:
                    query_dict[map] = query_dict[map]+ data.query_string
                    query_dict[map] =list2query_string( [x for x in list(set(query_dict[map].split("/"))) if x != ""])
                except KeyError:
                    query_dict[map] = data.query_string



    for data in _eggnog_object:

        for maps in data.KEGG_Pathway:
            if maps in query_dict:
                url = "https://www.kegg.jp/kegg-bin/show_pathway?map{0}/{1}/image1x".format(maps.replace("ec", ""),
                                                                                        query_dict[maps])
                mapping_string = mapping_string + "{} : {}".format(data.query, url) + "\n"

    write2File(mapping_file, mapping_string)
    return None

def get_highlighted_map_links_productwise(_eggnog_object, _dir):
    mapping_string = ""
    mapping_file = _dir + "/product_mapped.txt"
    for data in _eggnog_object:
        for maps in data.KEGG_Pathway:
            url = "https://www.kegg.jp/kegg-bin/show_pathway?map{0}/{1}/image1x".format(maps.replace("ec", ""),
                                                                                        data.query_string)
            mapping_string = mapping_string + "{} : {}".format(data.query, url) + "\n"

    write2File(mapping_file, mapping_string)
    return None

def generate_datils_from_eggmapper(_eggnog_data, _dir):
    for _data in _eggnog_data:
        query_dir = _dir + "/" + _data.query
        reaction_dir = query_dir + "/reactions/"
        map_dir = query_dir + "/maps/"

        if not os.path.exists(query_dir): os.makedirs(query_dir)
        if not os.path.exists(reaction_dir): os.makedirs(reaction_dir)
        if not os.path.exists(map_dir): os.makedirs(map_dir)

        download_kegg_map(_data.KEGG_Pathway, map_dir)
        download_kegg_reaction_images(_data.KEGG_Reaction, out_dir=reaction_dir)
        query_string = ""
        for reaction in _data.KEGG_Reaction:
            products = get_products_for_reaction(reaction)
            query_string = query_string + "{0}/".format(reaction)
            _data.product_id.extend(products)
            for product in products:
                # print(product)
                query_string = query_string + "{0}/".format(product)
                name_of_product = get_compound_name(product)
                _data.product_name.append(name_of_product)
            _data.query_string = query_string
        # print(_data)
        # get_highlighted_map_links(_eggnog_data, _dir)
    get_highlighted_map_links(_eggnog_data, _dir)

    return _eggnog_data


def eggnogg_mapper_processing(_parsed):
    for value in _parsed:
        clean_path = []
        process_path = value.KEGG_Pathway
        if len(process_path) > 0:
            new_array = process_path
            for values in new_array:
                if values.isalnum():
                    if values[-5:] in kegg_id:
                        clean_path.append(values[-5:])
                else:
                    print("{0} is invalid".format(values))
            value.KEGG_Pathway = remove_duplicate(remove_011_012_013(clean_path))

    return _parsed


# Example usage
def get_pathway_from_eggmapper_annot_conservative(_input, _output):
    reaction_list = []
    all_maps = []

    bcg_details_dir = _output + "/details/" + os.path.basename(_input).split(".")[0]
    if not os.path.exists(bcg_details_dir): os.makedirs(bcg_details_dir)
    query_dict = {}
    ##reorder find common paths and then
    parsed_results = parse_emapper_output(_input)
    products_name_list = []
    mapped = map_emapper_to_eggnog(parsed_results)
    clean_data = eggnogg_mapper_processing(mapped)
    clean_data = generate_datils_from_eggmapper(clean_data, bcg_details_dir)

    all_maps = [x.KEGG_Pathway for x in clean_data]
    all_maps = list(itertools.chain.from_iterable(all_maps))
    common_paths, count = most_common_pathways(all_maps)
    print(common_paths, count)
    for path in common_paths:
        found_index = [path in x.KEGG_Pathway for x in clean_data]
        indexes = [i for i, val in enumerate(found_index) if val]

        for value in indexes:
            focus_query = clean_data[value]
            print_str = ""
            reaction_list.extend(focus_query.KEGG_Reaction)
            products_name_list.extend(focus_query.product_name)
    export_eggnog_to_csv(
        clean_data,
        fields=["query", "KEGG_Pathway", "KEGG_Reaction", "product_name"],
        filename=bcg_details_dir+"/details.csv"
    )
    return common_paths, remove_duplicate(reaction_list), remove_duplicate(products_name_list)

#
# if __name__ == "__main__":
#     # file_path = "/home/rajroy/Downloads/tools/eggnog-mapper/BGC0000343_out.out.emapper.annotations"  # Replace with your actual file
#     file_path = "/home/rajroy/output_file_test/emapper/BGC0000384_r_1_c_1.emapper.annotations"  # Replace with your actual file
#     # file_path = sys.argv[1]
#     output = "/home/rajroy/output_file_test/"
#     # output=sys.argv[2]
#     maps = get_pathway_from_eggmapper_annot_conservative(file_path, output)
#     print(maps)
