"""Minimal opt-in Windows launcher companion. Not exposed as a web endpoint.
Only launches an app discovered in Start Menu shortcuts or a short built-in allowlist.
"""
import argparse, os, sys
from pathlib import Path

KNOWN = {"notepad": ["notepad.exe"], "calculator": ["calc.exe"], "paint": ["mspaint.exe"], "explorer": ["explorer.exe"], "powershell": ["powershell.exe"]}

def discover():
    found = {}
    roots = [Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs", Path(os.environ.get("ProgramData", "C:\\ProgramData")) / r"Microsoft\Windows\Start Menu\Programs"]
    for root in roots:
        if root.is_dir():
            for item in root.rglob("*.lnk"):
                found.setdefault(item.stem.casefold(), item)
    return found

def main():
    if sys.platform != "win32":
        print("FRIDAY Windows companion runs on Windows only."); return 2
    parser = argparse.ArgumentParser(description="FRIDAY's approval-gated Windows app launcher")
    parser.add_argument("action", choices=["list", "launch"])
    parser.add_argument("app", nargs="?")
    args = parser.parse_args()
    apps = discover()
    for name in KNOWN: apps.setdefault(name, KNOWN[name][0])
    if args.action == "list":
        for name in sorted(apps): print(name)
        return 0
    if not args.app:
        parser.error("launch requires an app name")
    key = args.app.casefold().strip()
    target = apps.get(key)
    if not target:
        print("Not found in Start Menu or the built-in safe list. Use `list` to discover apps."); return 1
    print(f"FRIDAY wants to launch: {key} ({target})")
    if input("Type LAUNCH to approve this action: ").strip() != "LAUNCH":
        print("Cancelled."); return 1
    try:
        if isinstance(target, Path): os.startfile(str(target))
        else: os.startfile(target)
        print(f"Launch request sent for {key}."); return 0
    except OSError as e:
        print(f"Could not launch {key}: {e}"); return 1

if __name__ == "__main__": raise SystemExit(main())
