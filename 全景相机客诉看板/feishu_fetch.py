#!/usr/bin/env python3
"""
飞书多维表格数据获取工具
用法: python feishu_fetch.py --app_token APP_TOKEN --table TABLE_ID [--view VIEW_ID]
凭证自动从 ~/.config/feishu/config.env 读取
"""

import os
import json
import argparse
import requests
from pathlib import Path


def load_config():
    config_path = Path.home() / ".config" / "feishu" / "config.env"
    config = {}
    if config_path.exists():
        for line in config_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    app_id = config.get("FEISHU_APP_ID") or os.environ.get("FEISHU_APP_ID")
    app_secret = config.get("FEISHU_APP_SECRET") or os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise ValueError("未找到飞书凭证，请检查 ~/.config/feishu/config.env")
    return app_id, app_secret


def get_tenant_access_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret})
    data = resp.json()
    if data.get("code") != 0:
        raise ValueError(f"获取 Token 失败: {data}")
    return data["tenant_access_token"]


def get_table_fields(token, app_token, table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    data = resp.json()
    if data.get("code") != 0:
        raise ValueError(f"获取字段失败: {data}")
    return data["data"]["items"]


def get_all_records(token, app_token, table_id, view_id=None):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    all_records = []
    page_token = None

    while True:
        params = {"page_size": 100}
        if view_id:
            params["view_id"] = view_id
        if page_token:
            params["page_token"] = page_token

        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()

        if data.get("code") != 0:
            raise ValueError(f"获取记录失败: {data}")

        records = data["data"].get("items", [])
        all_records.extend(records)

        if not data["data"].get("has_more"):
            break
        page_token = data["data"].get("page_token")

    return all_records


def extract_cell_value(cell):
    if cell is None:
        return ""
    if isinstance(cell, str):
        return cell
    if isinstance(cell, (int, float)):
        return cell
    if isinstance(cell, list):
        parts = []
        for item in cell:
            if isinstance(item, dict):
                parts.append(item.get("text", item.get("name", str(item))))
            else:
                parts.append(str(item))
        return "，".join(parts)
    if isinstance(cell, dict):
        return cell.get("text", cell.get("value", str(cell)))
    return str(cell)


def records_to_table(fields, records):
    field_names = [f["field_name"] for f in fields]
    rows = []
    for record in records:
        row = {}
        for name in field_names:
            raw = record.get("fields", {}).get(name)
            row[name] = extract_cell_value(raw)
        rows.append(row)
    return field_names, rows


def print_summary(field_names, rows):
    print(f"\n共获取 {len(rows)} 条记录，{len(field_names)} 个字段")
    print(f"字段列表: {', '.join(field_names)}\n")


def save_to_json(field_names, rows, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"fields": field_names, "rows": rows}, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {output_path}")


def main():
    parser = argparse.ArgumentParser(description="飞书多维表格数据获取工具")
    parser.add_argument("--app_token", required=True, help="多维表格 App Token（URL 中 /base/ 后面的部分）")
    parser.add_argument("--table", required=True, help="Table ID（如 tblgJWv4cDlQkbHS）")
    parser.add_argument("--view", help="View ID（可选，如 vew5iEGcje）")
    parser.add_argument("--output", default="feishu_data.json", help="输出文件路径（默认 feishu_data.json）")
    args = parser.parse_args()

    print("正在读取凭证...")
    app_id, app_secret = load_config()

    print("正在获取访问令牌...")
    token = get_tenant_access_token(app_id, app_secret)

    print("正在获取字段信息...")
    fields = get_table_fields(token, args.app_token, args.table)

    print("正在拉取全量记录...")
    records = get_all_records(token, args.app_token, args.table, args.view)

    field_names, rows = records_to_table(fields, records)
    print_summary(field_names, rows)
    save_to_json(field_names, rows, args.output)

    return field_names, rows


if __name__ == "__main__":
    main()
