#!/usr/bin/env python3
"""
update_all.py — 批量运行所有看板的飞书数据更新脚本
用于 GitHub Actions 和本地手动更新

用法：
    python update_all.py
"""
import subprocess, sys
from pathlib import Path

base = Path(__file__).parent
scripts = sorted(base.glob("*/dashboard_update.py"))

if not scripts:
    print("未找到任何 dashboard_update.py，请检查目录结构")
    sys.exit(1)

print(f"共找到 {len(scripts)} 个看板更新脚本\n")
failed = []

for script in scripts:
    folder = script.parent.name
    print(f"▶ {folder}")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(script.parent),
        text=True
    )
    if result.returncode != 0:
        failed.append(folder)
        print(f"  ✗ 失败")
    else:
        print(f"  ✓ 成功")

print()
if failed:
    print(f"失败的看板 ({len(failed)} 个): {', '.join(failed)}")
    sys.exit(1)
else:
    print(f"全部 {len(scripts)} 个看板更新成功 ✓")
