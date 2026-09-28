import urllib.request, urllib.error, json, os
key = os.environ["GEMINI_API_KEY"]
for model in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite", "gemma-4-31b-it"]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": "hi"}]}]}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        print(model, "OK:", str(d)[:150])
    except urllib.error.HTTPError as e:
        print(model, "HTTP", e.code, e.read().decode()[:400])
