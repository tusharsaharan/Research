import urllib.request, urllib.error, json, os
key = os.environ.get("GEMINI_API_KEY", "")
print("key_len:", len(key))
# 1. list models
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=50"
try:
    d = json.loads(urllib.request.urlopen(url, timeout=30).read().decode())
    for m in d.get("models", []):
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" in methods:
            print(m["name"])
except urllib.error.HTTPError as e:
    print("LIST HTTP", e.code, e.read().decode()[:500])
