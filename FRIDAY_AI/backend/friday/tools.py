"""Small, auditable local tools. Every path is confined to FRIDAY_WORKSPACE."""
from pathlib import Path
from .config import WORKSPACE

class ToolError(ValueError):
    pass

def safe_path(relative: str) -> Path:
    p = (WORKSPACE / relative).resolve()
    if p != WORKSPACE and WORKSPACE not in p.parents:
        raise ToolError("Path is outside FRIDAY's configured workspace.")
    return p

def list_files(directory: str = "."):
    p = safe_path(directory)
    if not p.exists() or not p.is_dir():
        raise ToolError("That workspace directory does not exist.")
    return [{"name": x.name, "type": "folder" if x.is_dir() else "file", "size": x.stat().st_size if x.is_file() else None}
            for x in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))[:200]]

def read_file(path: str):
    p = safe_path(path)
    if not p.is_file():
        raise ToolError("File not found in FRIDAY workspace.")
    if p.stat().st_size > 500_000:
        raise ToolError("File is too large to read (limit 500 KB).")
    return p.read_text(encoding="utf-8", errors="replace")

def write_file(path: str, content: str, approved: bool = False):
    p = safe_path(path)
    if not approved:
        return {"approval_required": True, "action": "write_file", "path": str(p.relative_to(WORKSPACE)), "message": "Writing a file requires user approval. Confirm this action in the FRIDAY interface and retry."}
    if p.exists():
        return {"approval_required": True, "action": "overwrite_file", "path": str(p.relative_to(WORKSPACE)), "message": "This path already exists; overwrite requires explicit approval."}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"created": str(p.relative_to(WORKSPACE)), "bytes": p.stat().st_size}

def make_folder(path: str, approved: bool = False):
    p = safe_path(path)
    if not approved:
        return {"approval_required": True, "action": "create_folder", "path": str(p.relative_to(WORKSPACE))}
    p.mkdir(parents=True, exist_ok=False)
    return {"created_folder": str(p.relative_to(WORKSPACE))}

TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "list_files", "description": "List files in FRIDAY's private workspace only.", "parameters": {"type": "object", "properties": {"directory": {"type": "string", "description": "Relative path, default ."}}, "required": []}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a UTF-8 text file from FRIDAY's private workspace only.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create a new text file in the private workspace. Never overwrite. Requires explicit approval from user.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "make_folder", "description": "Create a folder inside the private workspace. Requires explicit user approval.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
]

def run_tool(name: str, arguments: dict, approved: bool = False):
    if name == "list_files": return list_files(**arguments)
    if name == "read_file": return read_file(**arguments)
    if name == "write_file": return write_file(**arguments, approved=approved)
    if name == "make_folder": return make_folder(**arguments, approved=approved)
    raise ToolError(f"Unknown tool: {name}")
