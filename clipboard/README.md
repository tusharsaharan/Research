# public-clip — shared clipboard (Vercel-ready)

Anyone can **put text** (web UI or command line), anyone with internet can **extract** it.
Zero dependencies, zero build step. Static page + 3 serverless functions.

## Quick deploy to Vercel (2 min)

**Option A — Vercel dashboard (easiest):**
1. Push this `clipboard/` folder to GitHub (or import the whole repo and set Root Directory to `clipboard`).
2. Go to https://vercel.com/new → import the repo → set **Root Directory = `clipboard`** → Deploy.
3. Done. You get `https://your-app.vercel.app`.

**Option B — CLI:**
```bash
cd clipboard
npx vercel
```

No env vars required. It works immediately with in-memory storage.

## Make storage persistent (recommended, free)

On Vercel, serverless instances don't share memory, so pastes can vanish after cold starts.
Fix in 1 click:

1. Vercel dashboard → your project → **Storage** → **Create Database** → **KV** → Connect.
2. Redeploy. The code auto-detects `KV_REST_API_URL` / `KV_REST_API_TOKEN`
   (or `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN`) and switches to shared storage.
3. Check `/api/health` → `"store":"vercel-kv"` means persistent ✓.

Local dev with KV: copy `.env.example` to `.env` and fill in the values.

## CLI usage (replace BASE with your Vercel URL)

```bash
BASE=https://your-app.vercel.app

# 1. Publish JSON
curl -s -X POST $BASE/api/clip \
  -H "Content-Type: application/json" \
  -d '{"text":"hello world"}'

# 2. Publish piped stdin (any command output)
echo "hello from pipe" | curl -s -X POST $BASE/api/clip \
  -H "Content-Type: text/plain" --data-binary @-

# 3. Fetch latest paste (JSON)
curl -s $BASE/api/clip

# 4. Fetch by id (JSON)
curl -s "$BASE/api/clip?id=PASTE_ID"

# 5. Fetch raw text only (for scripts)
curl -s "$BASE/api/clip?id=PASTE_ID&format=text"

# 6. List recent
curl -s $BASE/api/clips?limit=20
```

PowerShell:
```powershell
$BASE = "https://your-app.vercel.app"
Invoke-RestMethod -Uri "$BASE/api/clip" -Method Post `
  -ContentType "application/json" -Body '{"text":"hello from powershell"}'
Invoke-RestMethod -Uri "$BASE/api/clip"
```

## API reference

| Method | Path | Description |
|---|---|---|
| POST | `/api/clip` | Body `{"text":"..."}` (JSON) or raw text. Returns `{id, url, apiUrl, len, createdAt}` |
| GET | `/api/clip` | Latest paste (JSON) |
| GET | `/api/clip?id=X` | Paste by id (JSON) |
| GET | `/api/clip?id=X&format=text` | Raw text only |
| GET | `/api/clips?limit=20` | Recent pastes (id, preview, len, createdAt) |
| GET | `/api/health` | `{ok, store: "vercel-kv"|"memory"}` |

Limits: 100 KB per paste, last 100 kept, KV entries expire after 30 days. CORS open (`*`).

## Files

```
clipboard/
  public/index.html  — terminal-style web UI (no build)
  api/clip.js        — POST create / GET read
  api/clips.js       — GET recent list
  api/health.js      — health + storage kind
  api/_store.js      — KV-or-memory storage layer
  vercel.json        — Vercel config
  package.json       — minimal (no deps)
```
