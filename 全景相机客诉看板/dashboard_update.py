#!/usr/bin/env python3
"""
dashboard_update.py
──────────────────
1. 从飞书 Bitable 拉取最新数据
2. 写入 feishu_data_latest.json（供浏览器刷新用）
3. 把数据嵌入 dashboard.html（直接双击可用）

用法：
    python dashboard_update.py          # 手动执行一次
    python dashboard_update.py --serve  # 同时启动本地 HTTP 服务（端口 8765）

定时执行（每天 09:00）：
    Windows 任务计划程序 → 每天 09:00 → 运行此脚本
"""

import sys, os, json, re
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

# ── 路径 ──────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
HTML_TMPL    = SCRIPT_DIR / "dashboard.html"
DATA_OUTPUT  = SCRIPT_DIR / "feishu_data_latest.json"
LOG_FILE     = SCRIPT_DIR / "dashboard_update.log"

# ── 飞书配置 ──────────────────────────────────────────
def load_config():
    config_path = Path.home() / ".config" / "feishu" / "config.env"
    cfg = {}
    if config_path.exists():
        for line in config_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                cfg[k.strip()] = v.strip()
    app_id     = cfg.get('FEISHU_APP_ID')     or os.environ.get('FEISHU_APP_ID')
    app_secret = cfg.get('FEISHU_APP_SECRET') or os.environ.get('FEISHU_APP_SECRET')
    if not app_id or not app_secret:
        raise ValueError("未找到飞书凭证，请检查 ~/.config/feishu/config.env")
    return app_id, app_secret

APP_TOKEN = 'UU6kb8aXUavOxVsPtzUccWfUnKe'
TABLE_ID  = 'tblgJWv4cDlQkbHS'
VIEW_ID   = 'vew5iEGcje'

# ── API ───────────────────────────────────────────────
import requests

def get_token(app_id, app_secret):
    url  = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': app_id, 'app_secret': app_secret}, timeout=15)
    d    = resp.json()
    if d.get('code') != 0:
        raise ValueError(f"Token 获取失败: {d}")
    return d['tenant_access_token']

def get_fields(token):
    url  = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields'
    hdrs = {'Authorization': f'Bearer {token}'}
    resp = requests.get(url, headers=hdrs, timeout=15)
    d    = resp.json()
    if d.get('code') != 0:
        raise ValueError(f"Fields 获取失败: {d}")
    return d['data'].get('items', [])

def get_all_records(token):
    url  = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records'
    hdrs = {'Authorization': f'Bearer {token}'}
    all_records, page_token = [], None
    while True:
        params = {'page_size': 100, 'view_id': VIEW_ID}
        if page_token:
            params['page_token'] = page_token
        resp = requests.get(url, headers=hdrs, params=params, timeout=15)
        d    = resp.json()
        if d.get('code') != 0:
            raise ValueError(f"Records 获取失败: {d}")
        items = d['data'].get('items', [])
        all_records.extend(items)
        if not d['data'].get('has_more'):
            break
        page_token = d['data'].get('page_token')
    return all_records

def extract(v):
    if v is None: return ''
    if isinstance(v, str):  return v
    if isinstance(v, (int, float)): return v
    if isinstance(v, list):
        parts = []
        for x in v:
            if isinstance(x, dict): parts.append(x.get('text') or x.get('name') or '')
            else: parts.append(str(x))
        return '，'.join(filter(None, parts))
    if isinstance(v, dict): return v.get('text') or v.get('value') or str(v)
    return str(v)

# ── Embed data into HTML ──────────────────────────────
PLACEHOLDER = '__EMBEDDED_DATA_PLACEHOLDER__'

def embed_data_into_html(raw_data):
    html = HTML_TMPL.read_text(encoding='utf-8')
    json_str = json.dumps(raw_data, ensure_ascii=False)
    if PLACEHOLDER in html:
        html = html.replace(PLACEHOLDER, json_str)
    else:
        # already embedded — replace the old JSON
        pattern = r'const EMBEDDED_DATA = (\{.*?\});'
        html = re.sub(pattern, f'const EMBEDDED_DATA = {json_str};', html, flags=re.DOTALL)
    HTML_TMPL.write_text(html, encoding='utf-8')
    print(f"  ✓ dashboard.html 已更新（嵌入 {len(raw_data['records'])} 条记录）")

# ── Simplified record for embedding ──────────────────
def simplify_record(r):
    f = r.get('fields', {})
    return {
        'record_id': r.get('record_id', ''),
        'fields': {
            '问题编号':    extract(f.get('问题编号')),
            '归类':        extract(f.get('归类')),
            '问题内容':    extract(f.get('问题内容')),
            '问题描述及诉求': extract(f.get('问题描述及诉求')),
            '严重程度':    extract(f.get('严重程度')),
            '问题分级':    extract(f.get('问题分级')),
            '赛纳-提交日期': f.get('赛纳-提交日期'),  # keep ms timestamp
            '状态':        extract(f.get('状态')),
            '赛纳复测结果': extract(f.get('赛纳复测结果')),
            '赛纳复测备注': extract(f.get('赛纳复测备注')),
            '看到反馈':    extract(f.get('看到反馈')),
            '看到-预计解决日期': f.get('看到-预计解决日期'),
            '看到-实际完成日期': f.get('看到-实际完成日期'),
        }
    }

# ── Main ─────────────────────────────────────────────
def main():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{now}] 开始更新看板数据…")

    try:
        app_id, app_secret = load_config()
        print("  ✓ 凭证加载成功")

        token = get_token(app_id, app_secret)
        print("  ✓ Token 获取成功")

        fields  = get_fields(token)
        records = get_all_records(token)
        print(f"  ✓ 获取到 {len(records)} 条记录，{len(fields)} 个字段")

        # Save full raw data
        full_raw = {
            'updated_at': now,
            'fields':  fields,
            'records': [simplify_record(r) for r in records]
        }
        DATA_OUTPUT.write_text(json.dumps(full_raw, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"  ✓ feishu_data_latest.json 已更新")

        # Embed into HTML
        embed_data_into_html(full_raw)

        # Log success
        with LOG_FILE.open('a', encoding='utf-8') as lf:
            lf.write(f"[{now}] OK  records={len(records)}\n")

        print(f"\n✅ 看板更新完成！打开 dashboard.html 查看")

    except Exception as e:
        msg = f"[{now}] ERROR  {e}"
        print(f"\n❌ 更新失败: {e}")
        with LOG_FILE.open('a', encoding='utf-8') as lf:
            lf.write(msg + '\n')
        sys.exit(1)


def serve():
    """启动本地 HTTP 服务，让浏览器能 fetch feishu_data_latest.json"""
    import http.server, threading, webbrowser
    os.chdir(SCRIPT_DIR)
    PORT = 8765
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass  # silence logs
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            super().end_headers()
    httpd = http.server.HTTPServer(('', PORT), Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    url = f'http://localhost:{PORT}/dashboard.html'
    print(f"\n🌐 本地服务已启动: {url}")
    webbrowser.open(url)
    print("   按 Ctrl+C 停止服务\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == '__main__':
    main()
    if '--serve' in sys.argv:
        serve()
