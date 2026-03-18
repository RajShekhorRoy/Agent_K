#previously one bgc -> bio_fasta -> (MANUAL) eggnog ->all products and maps
#New anitsmash file -> extract all bgc for each contig-> for each  bgc -> bio_fasta -> (MANUAL) eggnog ->all products and maps
#output should be contig - bgc products maps
#dir should be like this too
import os
import sys
from pathlib import Path

import pandas as pd
import all_bcg_from_index,egnog_mapper,general_libs
from agent.utils import get_emapper
from get_biofasta_mibig import extract_proteins_with_biosynthetic_annotations


# input_file = "/home/rajroy/antismash_test_121625/consensus_cov/"
# output_dir = "/home/rajroy/test_random/"

# os.makedirs(map_dir,exist_ok=True)
def remove_space (_list):
    final_list = []
    for values in _list:
        final_list.append(values.strip())
    return final_list
if __name__ == '__main__':
    # [i for i, d in enumerate(all_bcg_from_index) if "BGC0000343" in d.get("BGC_ID")]

    # python
    # all_bgc_AS_map_agentic_version.py / home / rajroy / antismash_test_121625 / consensus_cov / / home / rajroy / PycharmProjects / Agent_K / outputs / BGC0000343_r_3_c_1 / BGC0000343
    input_file = sys.argv[1]+"/index.html"
    output_dir = sys.argv[2]
    choosen_bgc = sys.argv[3]
    # print(input_file,output_dir,choosen_bgc)
    # input_file = "/home/rajroy/antismash_test_121625/consensus_cov/"+"index.html"
    # output_dir = "/home/rajroy/test_random_new/BGC0000641/"
    # choosen_bgc ="BGC0000641"
    print(input_file, output_dir, choosen_bgc)


    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    choosen_bgc_list = choosen_bgc.split(",")
    choosen_bgc_list=remove_space(choosen_bgc_list)

    print(choosen_bgc)
    all_bcg_from_index_initial =  all_bcg_from_index.Mibig_extractor(input_file,output_dir)
    all_bcg_from_index=[]


    for values in choosen_bgc_list:
        index_now = int([i for i, d in enumerate(all_bcg_from_index_initial) if values in d.get("BGC_ID")][0])
        all_bcg_from_index.append(all_bcg_from_index_initial[index_now])

    #initialization of other files
    mibig_dir = output_dir + "mibig/"
    emapper_dir = output_dir + "emapper/"
    map_dir = output_dir + "/maps/"
    bio_syn_fasta = output_dir + "bio_syn_fasta/"
    desired_similarity = 0.0
    os.makedirs(mibig_dir, exist_ok=True)
    os.makedirs(bio_syn_fasta, exist_ok=True)
    os.makedirs(emapper_dir, exist_ok=True)


    #downloaded all the bcg
    for bcg in all_bcg_from_index:
        print(bcg['BGC_ID'])
        is_mibig_download= general_libs.download_mibig_gbk(bcg['BGC_ID'], output_dir)
        if bcg['Similarity'] >= desired_similarity:
            if is_mibig_download !=False:
                # bion_syn_name ="/{0}_r_{1}_c_{2}.fasta".format(bcg['BGC_ID'].split(".")[0],bcg['Region'].split(" ")[1],bcg['Contig'].split("_")[1])
                bion_syn_name ="/{0}.fasta".format(bcg['BGC_ID'].split(".")[0],bcg['Region'].split(" ")[1],bcg['Contig'].split("_")[1])
                fasta_file_name = bio_syn_fasta+    bion_syn_name
                bio_synthetic_fasta = extract_proteins_with_biosynthetic_annotations(mibig_dir+bcg['BGC_ID'].split(".")[0]+".gbk",fasta_file_name)
                emapper_name=     bion_syn_name.split(".")[0].replace("/","")

                # SCRIPT_DIR = Path(__file__).resolve().parent
                # script_path = egnog_mapper.text_file_reader(str(SCRIPT_DIR / "emapper.py"))

                emapper_file=get_emapper()
                # eggnogmapper_cmd = "[/home/rajroy/Downloads/tools/eggnog-mapper/emapper.py] -m diamond  --cpu 16 -i {0} --output_dir {1} --sensmode ultra-sensitive --override --cpu 21  -o {2} --tax_scope prokaryota_broad".format(fasta_file_name,emapper_dir,emapper_name)
                eggnogmapper_cmd ="python "+ emapper_file+" -m diamond  --cpu 16 -i {0} --output_dir {1} --sensmode ultra-sensitive --override --cpu 21  -o {2} --tax_scope prokaryota_broad".format(fasta_file_name,emapper_dir,emapper_name)
               # #uncomment it please
                print(eggnogmapper_cmd)
                emapp_file = emapper_dir + emapper_name + ".emapper.annotations"
                if not os.path.exists(emapp_file):
                    os.system(eggnogmapper_cmd)
                print(bcg['Region'] )


                maps,reactions,products=egnog_mapper.get_pathway_from_eggmapper_annot_conservative( _input =emapp_file, _output=output_dir)
                bcg['pathway']=maps
                bcg['reactions']=reactions
                bcg['products']=products

    df = pd.DataFrame(all_bcg_from_index)
    df.to_csv(output_dir + "/AnitSMASH_final_output.csv", index=False)