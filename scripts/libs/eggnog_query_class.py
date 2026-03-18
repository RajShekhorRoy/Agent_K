import re
from typing import List, Union

# --- your target class as given ---
class EggnogQueryClass:
    def __init__(self):
        self.BRITE = ""
        self.BiGG_Reaction = ""
        self.CAZy = ""
        self.COG_category = ""
        self.Description = ""
        self.EC = []
        self.GOs = []
        self.KEGG_Module = ""
        self.KEGG_Pathway = []
        self.KEGG_Reaction = []
        self.KEGG_TC = []
        self.KEGG_ko = []
        self.KEGG_rclass = []
        self.PFAMs = []
        self.Preferred_name = []
        self.eggNOG_OGs = []
        self.evalue = []
        self.max_annot_lvl = []
        self.query = ""
        self.score = ""
        self.seed_ortholog = []
        self.product_id = []
        self.product_name = []
        self.query_string =""

# --- helpers ---
_EMPTY = {"", "-", "NA", "N/A", "None", None}

def _as_dict(row: Union[dict, object]) -> dict:
    return row if isinstance(row, dict) else vars(row)

def _get(d: dict, key: str, default: str = "") -> str:
    v = d.get(key, "")
    return "" if v in _EMPTY else str(v)

def _split_list(v: str) -> List[str]:
    """Split on ',', ';' or whitespace; drop empties and dashes."""
    if v in _EMPTY:
        return []
    parts = re.split(r"[,\s;]+", v.strip())
    return [p for p in parts if p and p not in _EMPTY]

# --- the mapper ---
def map_emapper_row_to_eggnog(row: Union[dict, object]) -> EggnogQueryClass:
    d = _as_dict(row)
    out = EggnogQueryClass()

    # 1) strings (singletons)
    out.BRITE          = _get(d, "BRITE")
    out.BiGG_Reaction  = _get(d, "BiGG_Reaction")
    out.CAZy           = _get(d, "CAZy")
    out.COG_category   = _get(d, "COG_category")
    out.Description    = _get(d, "Description")
    out.KEGG_Module    = _get(d, "KEGG_Module")
    out.KEGG_TC        = _get(d, "KEGG_TC")
    out.query          = _get(d, "query")
    out.score          = _get(d, "score")

    # 2) lists
    out.EC             = _split_list(_get(d, "EC"))
    out.GOs            = _split_list(_get(d, "GOs"))
    out.KEGG_Pathway   = _split_list(_get(d, "KEGG_Pathway"))
    out.KEGG_Reaction  = _split_list(_get(d, "KEGG_Reaction"))
    out.KEGG_ko        = _split_list(_get(d, "KEGG_ko"))
    out.KEGG_rclass    = _split_list(_get(d, "KEGG_rclass"))
    out.PFAMs          = _split_list(_get(d, "PFAMs"))
    out.Preferred_name = _split_list(_get(d, "Preferred_name"))
    out.eggNOG_OGs     = _split_list(_get(d, "eggNOG_OGs"))
    out.evalue         = _split_list(_get(d, "evalue"))
    out.max_annot_lvl  = _split_list(_get(d, "max_annot_lvl"))
    out.seed_ortholog  = _split_list(_get(d, "seed_ortholog"))

    return out

def map_emapper_to_eggnog(rows: List[Union[dict, object]]) -> List[EggnogQueryClass]:
    return [map_emapper_row_to_eggnog(r) for r in rows]