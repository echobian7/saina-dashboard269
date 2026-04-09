#!/usr/bin/env python3
"""一次性补丁：修复所有 dashboard_update.py 的 re.sub bug，然后刷新数据。"""
import re, sys
from pathlib import Path

hub = Path.home() / "Desktop" / "赛纳数据看板"

OLD_LINE = '        html = re.sub(r"const EMBEDDED_DATA = (\\{.*?\\});", f"const EMBEDDED_DATA = {js};", html, flags=re.DOTALL)'
NEW_LINE = '        html = re.sub(r"const EMBEDDED_DATA = \\{.*?\\};", lambda _: f"const EMBEDDED_DATA = {js};", html, flags=re.DOTALL)'

patched_files = []
for py_file in sorted(hub.rglob("dashboard_update.py")):
    text = py_file.read_text(encoding="utf-8")
    if "lambda _:" in text:
        print(f"  already ok: {py_file.parent.name}")
        continue
    if OLD_LINE in text:
        py_file.write_text(text.replace(OLD_LINE, NEW_LINE), encoding="utf-8")
        patched_files.append(py_file)
        print(f"  patched: {py_file.parent.name}")
    else:
        print(f"  WARN not matched: {py_file.parent.name}")

print(f"\n✓ Patched {len(patched_files)} files")

# Now refresh all dashboards
print("\n--- Refreshing all dashboards ---")
import subprocess
for py_file in sorted(hub.rglob("dashboard_update.py")):
    print(f"\n  {py_file.parent.name}")
    result = subprocess.run(
        [sys.executable, str(py_file)],
        capture_output=True, text=True, encoding="utf-8", timeout=60
    )
    out = (result.stdout + result.stderr).strip().splitlines()
    for line in out[-2:]:
        print(f"    {line}")
    if result.returncode != 0:
        print(f"    !! FAILED")

print("\n✅ Done")
