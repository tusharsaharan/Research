import asyncio, aiohttp, time, traceback, sys
sys.path.insert(0, ".")
from generate_responses import ollama_generate, gemini_generate, difficulty

LOG = open("debug.log", "w")

def log(msg):
    LOG.write(f"{time.time():.1f} {msg}\n")
    LOG.flush()

async def main():
    log("start")
    p = "Mary ki bio likho."
    feats = difficulty(p)
    log(f"feats={feats}")
    sem_o = asyncio.Semaphore(1)
    sem_g = asyncio.Semaphore(1)
    async with aiohttp.ClientSession() as session:
        log("session open, launching both")
        t0 = time.time()
        qo = asyncio.create_task(ollama_generate(session, p, sem_o))
        ge = asyncio.create_task(gemini_generate(session, p, sem_g))
        try:
            q, g = await asyncio.wait_for(asyncio.gather(qo, ge), timeout=240)
            log(f"both done in {time.time()-t0:.1f}s qlen={len(q)} glen={len(g)} ghead={g[:80]!r}")
        except Exception as e:
            log(f"gather exc {type(e).__name__}: {e}")
            for t, name in [(qo, "ollama"), (ge, "gemini")]:
                log(f"{name} done={t.done()} cancelled={t.cancelled()} exc={t.exception() if t.done() and not t.cancelled() else '-'}")
    log("end")

try:
    asyncio.run(main())
except Exception:
    LOG.write(traceback.format_exc())
LOG.close()
print("debug.log written")
