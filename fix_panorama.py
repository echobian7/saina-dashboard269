import os, json

html_path = r"C:\Users\Administrator\Desktop\赛纳数据看板\全景相机客诉看板\dashboard.html"

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

marker = "const EMBEDDED_DATA = "
idx = content.find(marker)
json_start = idx + len(marker)
rest = content[json_start:]

# For this file the next line after JSON is "  const records = EMBEDDED_DATA"
end_marker = "};\n  const records = EMBEDDED_DATA"
end_idx = rest.find(end_marker)
if end_idx == -1:
    end_marker = "};\r\n  const records = EMBEDDED_DATA"
    end_idx = rest.find(end_marker)

print(f"end_idx: {end_idx}")
json_str = rest[:end_idx + 1]

try:
    data = json.loads(json_str)
    print(f"OK (valid JSON): {len(data.get('records',[]))} records")
    exit(0)
except json.JSONDecodeError as e:
    print(f"FIX needed: {e}")

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
    print(f"FIXED: {len(data.get('records', []))} records")
except json.JSONDecodeError as e:
    print(f"STILL BROKEN: {e}")
    exit(1)

serialized = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
new_content = content[:idx] + marker + serialized + content[json_start + end_idx + 1:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Saved.")
