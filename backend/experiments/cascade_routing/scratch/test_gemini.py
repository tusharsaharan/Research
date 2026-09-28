import urllib.request, json, os
key = os.environ["GEMINI_API_KEY"]
model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
payload = {"contents": [{"parts": [{"text": "Ek cube ka surface area batao side 5 cm hai. Sirf jawab do."}]}]}
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
print(d["candidates"][0]["content"]["parts"][0]["text"][:400])
print("GEMINI OK")
