import urllib.request, urllib.error, json, os
key = os.environ["GEMINI_API_KEY"]

def call(model, with_json):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": "Say hi."}]}]}
    if with_json:
        payload["generationConfig"] = {"response_mime_type": "application/json", "temperature": 0.0}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        return "OK: " + d["candidates"][0]["content"]["parts"][0]["text"][:80].replace("\n", " ")
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: " + e.read().decode()[:200].replace("\n", " ")

print("3.8-flash plain:", call("gemini-3.8-flash", False))
print("3.8-flash json :", call("gemini-3.8-flash", True))
print("3.5-flash json :", call("gemini-3.5-flash", True))
print("gemma-4-31b json:", call("gemma-4-31b-it", True))
