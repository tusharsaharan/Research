import urllib.request, urllib.error, json, os
key = os.environ["GEMINI_API_KEY"]
for model in ["gemini-3.8-flash", "gemini-3.5-flash"]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {"contents": [{"parts": [{"text": "Ek cube ka surface area batao side 5 cm hai. Sirf jawab do."}]}]}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        print(model, "OK:", d["candidates"][0]["content"]["parts"][0]["text"][:200])
    except urllib.error.HTTPError as e:
        print(model, "HTTP", e.code, e.read().decode()[:300])
