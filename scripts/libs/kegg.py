import requests
import time


def get_reactions_for_ec(ec_number):
    """Get KEGG reaction IDs for a given enzyme EC number."""
    url = f'http://rest.kegg.jp/link/reaction/ec:{ec_number}'
    r = requests.get(url)
    reactions = []
    if r.status_code == 200:
        for line in r.text.strip().split('\n'):
            fields = line.split('\t')
            print(fields)
            if len(fields) == 2:
                reaction_id = fields[1].split(':')[1]
                reactions.append(reaction_id)
    return reactions

def get_reactions_for_ec(ec_number):
    """Get KEGG reaction IDs for a given enzyme EC number."""
    url = f'http://rest.kegg.jp/link/reaction/ec:{ec_number}'
    r = requests.get(url)
    reactions = []
    if r.status_code == 200:
        for line in r.text.strip().split('\n'):
            fields = line.split('\t')
            if len(fields) == 2:
                reaction_id = fields[1].split(':')[1]
                reactions.append(reaction_id)
    return reactions


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


def main(ec_numbers):
    all_products = set()
    for ec in ec_numbers:
        print(f"\nProcessing EC: {ec}")
        reactions = get_reactions_for_ec(ec)
        print(f"  Found {len(reactions)} reactions")
        for rn in reactions:
            print(rn)
            products = get_products_for_reaction(rn)
            time.sleep(0.2)  # Be nice to the server
            all_products.update(products)
    print(f"\nFound {len(all_products)} unique product metabolites.")
    # Optionally get names
    print("Product Compounds:")
    for cid in all_products:
        name = get_compound_name(cid)
        print(f"{cid}: {name}")


if __name__ == "__main__":
    # Example input EC numbers
    # ec_list = ["1.3.1.28","5.4.4.2","1.15.1.1","1.14.19.3", ]
    ec_list = ["1.14.19.3"]
    main(ec_list)