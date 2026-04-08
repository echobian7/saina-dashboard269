#!/usr/bin/env python3
"""
dashboard_update.py  ·  自动生成，请勿手动编辑配置部分
──────────────────────────────────────────────────────
从飞书拉取最新数据，更新看板 HTML。

用法：
    python dashboard_update.py          # 执行一次
    python dashboard_update.py --serve  # 执行后启动本地服务（端口 8765）
"""
import sys, os, json, re
from pathlib import Path
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR   = Path(__file__).parent
HTML_FILE    = SCRIPT_DIR / "dashboard.html"
DATA_FILE    = SCRIPT_DIR / "feishu_data_latest.json"
LOG_FILE     = SCRIPT_DIR / "dashboard_update.log"
PLACEHOLDER  = "__EMBEDDED_DATA_PLACEHOLDER__"

# ── 固化配置（由 build_dashboard.py 生成）──
APP_TOKEN    = "TltXbBA3JazbnXshdqqceO2ynqf"
TABLE_ID     = "tblxWvnRH7tiXwV0"
VIEW_ID      = "vewH7mlu5K"
TITLE        = "B7-19D客诉进度看板"
FIELD_MAP    = {"status": "状态", "level": "问题分级", "category": "问题归属", "severity": null, "content": "翻译", "no": "客诉id", "date": "填表时间", "retest": "供应商反馈/处理方案"}
DONE_VALUES  = ["\u5df2\u5173\u95ed"]
TOP_LEVEL    = "S"

import requests

def load_creds():
    cfg_path = Path.home() / ".config" / "feishu" / "config.env"
    cfg = {}
    if cfg_path.exists():
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    app_id     = cfg.get("FEISHU_APP_ID")     or os.environ.get("FEISHU_APP_ID")
    app_secret = cfg.get("FEISHU_APP_SECRET") or os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise ValueError("未找到飞书凭证，请检查 ~/.config/feishu/config.env")
    return app_id, app_secret

def get_token(app_id, app_secret):
    r = requests.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                      json={"app_id": app_id, "app_secret": app_secret}, timeout=15)
    d = r.json()
    if d.get("code") != 0: raise ValueError(f"Token 失败: {d}")
    return d["tenant_access_token"]

def extract(v):
    if v is None: return ""
    if isinstance(v, str): return v
    if isinstance(v, (int, float)): return v
    if isinstance(v, list):
        return "，".join(filter(None, [x.get("text") or x.get("name") or "" if isinstance(x, dict) else str(x) for x in v]))
    if isinstance(v, dict): return v.get("text") or v.get("value") or str(v)
    return str(v)

def get_records(token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    hdrs = {"Authorization": f"Bearer {token}"}
    all_recs, page_token = [], None
    while True:
        params = {"page_size": 100}
        if VIEW_ID: params["view_id"] = VIEW_ID
        if page_token: params["page_token"] = page_token
        d = requests.get(url, headers=hdrs, params=params, timeout=15).json()
        if d.get("code") != 0: raise ValueError(f"Records 失败: {d}")
        all_recs.extend(d["data"].get("items", []))
        if not d["data"].get("has_more"): break
        page_token = d["data"].get("page_token")
    return all_recs

def simplify(r):
    f = r.get("fields", {})
    out = {"record_id": r.get("record_id", ""), "fields": {}}
    for std, actual in FIELD_MAP.items():
        if actual:
            raw = f.get(actual)
            out["fields"][std] = raw if std == "date" and isinstance(raw, (int, float)) else extract(raw)
    return out

def embed(data):
    html = HTML_FILE.read_text(encoding="utf-8")
    js = json.dumps(data, ensure_ascii=False)
    if PLACEHOLDER in html:
        html = html.replace(PLACEHOLDER, js)
    else:
        html = re.sub(r"const EMBEDDED_DATA = (\{.*?\});", f"const EMBEDDED_DATA = {js};", html, flags=re.DOTALL)
    HTML_FILE.write_text(html, encoding="utf-8")

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] 开始更新…")
    try:
        app_id, app_secret = load_creds()
        token   = get_token(app_id, app_secret)
        records = get_records(token)
        data = {"updated_at": now, "title": TITLE, "field_map": FIELD_MAP,
                 "done_values": DONE_VALUES, "top_level": TOP_LEVEL,
                 "records": [simplify(r) for r in records]}
        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        embed(data)
        with LOG_FILE.open("a", encoding="utf-8") as lf:
            lf.write(f"[{now}] OK  records={len(records)}\n")
        print(f"  OK  {len(records)} 条记录  →  {HTML_FILE.name}")
    except Exception as e:
        print(f"  ERROR  {e}")
        with LOG_FILE.open("a", encoding="utf-8") as lf:
            lf.write(f"[{now}] ERROR  {e}\n")
        sys.exit(1)

def serve():
    import http.server, threading, webbrowser
    os.chdir(SCRIPT_DIR)
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
        def end_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*"); super().end_headers()
    httpd = http.server.HTTPServer(("", 8765), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = "http://localhost:8765/dashboard.html"
    print(f"  服务已启动: {url}")
    webbrowser.open(url)
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass

if __name__ == "__main__":
    main()
    if "--serve" in sys.argv: serve()
