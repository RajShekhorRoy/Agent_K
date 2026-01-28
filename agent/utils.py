import os

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def list_files_recursive(root: str):
    out = []
    for base, _, files in os.walk(root):
        for f in files:
            p = os.path.join(base, f)
            out.append(os.path.relpath(p, root))
    out.sort()
    return out

def read_text_safely(path: str, max_chars: int = 12000) -> str:
    # Best-effort text read; you can expand for JSON/CSV parsing later.
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        txt = data.decode("utf-8", errors="replace")
    except Exception:
        txt = str(data)
    if len(txt) > max_chars:
        txt = txt[:max_chars] + "\n...[truncated]..."
    return txt
