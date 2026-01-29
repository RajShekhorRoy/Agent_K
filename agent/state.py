from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class AgentState(BaseModel):
    genbank_path: Optional[str] = None
    output_dir: str
    pathway_dir:Optional[str] = None
    antismash_dir:Optional[str] = None

    antismash_done: bool = False
    pathway_done: bool = False

    bgc_id: Optional[str] = None  # use snake_case

    # store discovered artifacts
    artifacts: Dict[str, Any] = Field(default_factory=dict)

    # lightweight memory (optional)
    notes: List[str] = Field(default_factory=list)
