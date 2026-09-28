import asyncio, aiohttp, os

async def main():
    key = os.environ["GEMINI_API_KEY"]
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key=" + key
    print("proxy env:", os.environ.get("HTTPS_PROXY"), "| no_proxy:", os.environ.get("NO_PROXY"))
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"contents": [{"parts": [{"text": "Say hi."}]}]},
                                timeout=aiohttp.ClientTimeout(total=90)) as r:
            print("status:", r.status)
            d = await r.json()
            print("resp:", d["candidates"][0]["content"]["parts"][0]["text"][:100])

asyncio.run(main())
