import os, json

base = r"C:\Users\Administrator\Desktop\赛纳数据看板"

dirs = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]

for d in dirs:
    html_path = os.path.join(base, d, "dashboard.html")
    if not os.path.exists(html_path):
        continue

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    marker = "const EMBEDDED_DATA = "
    idx = content.find(marker)
    if idx == -1:
        print(f"SKIP (no EMBEDDED_DATA): {d}")
        continue

    json_start = idx + len(marker)
    rest = content[json_start:]

    end_marker = "};\n  const {"
    end_idx = rest.find(end_marker)
    if end_idx == -1:
        end_marker = "};\r\n  const {"
        end_idx = rest.find(end_marker)
    if end_idx == -1:
        print(f"SKIP (can't find end): {d}")
        continue

    json_str = rest[:end_idx + 1]  # include closing }

    try:
        data = json.loads(json_str)
        print(f"OK (valid JSON): {d}")
        continue
    except json.JSONDecodeError as e:
        print(f"FIX needed: {d} - {e}")

    # Fix literal newlines inside JSON string values
    result = []
    in_string = False
    i = 0
    s = json_str
    while i < len(s):
        c = s[i]
        if in_string:
            if c == '\\':
                result.append(c)
                i += 1
                if i < len(s):
                    result.append(s[i])
            elif c == '"':
                result.append(c)
                in_string = False
            elif c == '\n':
                result.append('\\n')
            elif c == '\r':
                result.append('\\r')
            else:
                result.append(c)
        else:
            if c == '"':
                in_string = True
                result.append(c)
            else:
                result.append(c)
        i += 1

    fixed_json_str = ''.join(result)

    try:
        data = json.loads(fixed_json_str)
        print(f"FIXED: {d} ({len(data.get('records', []))} records)")
    except json.JSONDecodeError as e:
        print(f"STILL BROKEN: {d} - {e}")
        continue

    serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_content = content[:idx] + marker + serialized + content[json_start + end_idx + 1:]

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

print("Done.")
