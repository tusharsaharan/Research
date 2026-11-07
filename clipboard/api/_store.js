// Shared storage helpers for Vercel serverless functions.
// Strategy:
//  - If KV_REST_API_URL (+ TOKEN) or UPSTASH_REDIS_REST_URL (+ TOKEN) is set,
//    use Upstash REST pipeline -> persistent + shared across instances.
//  - Otherwise fall back to in-memory (works locally / demo, resets on cold start).

const MAX_KEEP = 100;
const EXPIRE_SECONDS = 30 * 24 * 3600; // 30 days for KV entries

function kvConfig() {
  const base =
    process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL || "";
  const token =
    process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN || "";
  if (base && token) {
    return { base: base.replace(/\/$/, ""), token };
  }
  return null;
}

async function kvPipeline(cmds) {
  const { base, token } = kvConfig();
  const res = await fetch(`${base}/pipeline`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(cmds),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`KV pipeline failed: ${res.status} ${t}`);
  }
  return res.json();
}

async function kvGet(key) {
  const out = await kvPipeline([["GET", key]]);
  return out?.[0]?.result ?? null;
}

async function kvSet(key, val, exSeconds) {
  const cmd = exSeconds
    ? ["SET", key, val, "EX", String(exSeconds)]
    : ["SET", key, val];
  await kvPipeline([cmd]);
}

// ---- In-memory fallback (per-instance) ----
function mem() {
  if (!globalThis.__CLIPS__) globalThis.__CLIPS__ = new Map();
  if (!globalThis.__CLIP_ORDER__) globalThis.__CLIP_ORDER__ = [];
  return {
    map: globalThis.__CLIPS__,
    order: globalThis.__CLIP_ORDER__,
  };
}

function makeId() {
  return (
    Date.now().toString(36) +
    Math.random().toString(36).slice(2, 6).replace(/[^a-z0-9]/gi, "x")
  );
}

async function saveClip(text) {
  const id = makeId();
  const record = { id, text, createdAt: new Date().toISOString(), len: text.length };
  const kv = kvConfig();
  if (kv) {
    await kvSet(`clip:${id}`, JSON.stringify(record), EXPIRE_SECONDS);
    let arr = [];
    try {
      const cur = await kvGet("clip:index");
      arr = cur ? JSON.parse(cur) : [];
      if (!Array.isArray(arr)) arr = [];
    } catch {
      arr = [];
    }
    arr.unshift(id);
    await kvSet("clip:index", JSON.stringify(arr.slice(0, MAX_KEEP)), EXPIRE_SECONDS);
    await kvSet("clip:latest", id, EXPIRE_SECONDS);
  } else {
    const { map, order } = mem();
    map.set(id, record);
    order.unshift(id);
    while (order.length > MAX_KEEP) {
      const drop = order.pop();
      map.delete(drop);
    }
  }
  return record;
}

async function getClip(id) {
  const kv = kvConfig();
  if (kv) {
    const raw = await kvGet(`clip:${id}`);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
  return mem().map.get(id) || null;
}

async function getLatest() {
  const kv = kvConfig();
  if (kv) {
    const latestId = await kvGet("clip:latest");
    if (!latestId) return null;
    return getClip(latestId);
  }
  const { map, order } = mem();
  if (!order.length) return null;
  return map.get(order[0]) || null;
}

async function listClips(limit = 20) {
  limit = Math.min(Math.max(parseInt(limit, 10) || 20, 1), 100);
  const kv = kvConfig();
  if (kv) {
    let ids = [];
    try {
      const cur = await kvGet("clip:index");
      ids = cur ? JSON.parse(cur) : [];
      if (!Array.isArray(ids)) ids = [];
    } catch {
      ids = [];
    }
    ids = ids.slice(0, limit);
    if (!ids.length) return [];
    const out = await kvPipeline(ids.map((id) => ["GET", `clip:${id}`]));
    return out
      .map((r, i) => {
        try {
          const rec = r?.result ? JSON.parse(r.result) : null;
          if (!rec) return null;
          return {
            id: rec.id,
            preview: String(rec.text).slice(0, 200),
            len: rec.len ?? String(rec.text).length,
            createdAt: rec.createdAt,
          };
        } catch {
          return { id: ids[i], preview: "", len: 0, createdAt: null };
        }
      })
      .filter(Boolean);
  }
  const { map, order } = mem();
  return order.slice(0, limit).map((id) => {
    const rec = map.get(id);
    return {
      id: rec.id,
      preview: String(rec.text).slice(0, 200),
      len: rec.len,
      createdAt: rec.createdAt,
    };
  });
}

function storeKind() {
  return kvConfig() ? "vercel-kv" : "memory";
}

module.exports = { saveClip, getClip, getLatest, listClips, storeKind, makeId };
