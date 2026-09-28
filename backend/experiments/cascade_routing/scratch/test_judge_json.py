import urllib.request, json, os
key = os.environ["GEMINI_API_KEY"]
model = "gemini-3.8-flash"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
payload = {
    "system_instruction": {"parts": [{"text": "Return STRICT JSON only: {\"acceptable\": 1} or {\"acceptable\": 0}"}]},
    "contents": [{"parts": [{"text": "PROMPT: Is text ki summary batao.\n\nBASELINE: Ye summary hai.\n\nCANDIDATE: Ye summary hai."}]}],
    "generationConfig": {"response_mime_type": "application/json", "temperature": 0.0},
}
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
txt = d["candidates"][0]["content"]["parts"][0]["text"]
print(repr(txt))
print("parsed:", json.loads(txt))
