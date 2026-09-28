import asyncio, aiohttp, json

async def main():
    async with aiohttp.ClientSession() as session:
        payload = {"model": "qwen2.5:latest", "prompt": "Hi bolo.",
                   "stream": False, "options": {"num_predict": 16}}
        try:
            async with session.post("http://localhost:11434/api/generate", json=payload,
                                    timeout=aiohttp.ClientTimeout(total=120), proxy=None) as r:
                print("status:", r.status)
                data = await r.json()
                print("resp:", (data.get("response") or "")[:200])
        except Exception as e:
            print(f"ERROR {type(e).__name__}: {e}")

asyncio.run(main())
