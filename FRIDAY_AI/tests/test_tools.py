import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from friday import tools

def test_paths_are_confined(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "WORKSPACE", tmp_path.resolve())
    assert tools.safe_path("notes/a.txt") == (tmp_path / "notes/a.txt").resolve()
    try:
        tools.safe_path("../../outside.txt")
    except tools.ToolError:
        pass
    else:
        raise AssertionError("Path traversal should be rejected")

def test_write_requires_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "WORKSPACE", tmp_path.resolve())
    blocked = tools.write_file("new.txt", "hello")
    assert blocked["approval_required"] is True
    assert not (tmp_path / "new.txt").exists()
    made = tools.write_file("new.txt", "hello", approved=True)
    assert made["created"] == "new.txt"
    assert (tmp_path / "new.txt").read_text() == "hello"

def test_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "WORKSPACE", tmp_path.resolve())
    (tmp_path / "keep.txt").write_text("original")
    result = tools.write_file("keep.txt", "replacement", approved=True)
    assert result["approval_required"] is True
    assert (tmp_path / "keep.txt").read_text() == "original"
