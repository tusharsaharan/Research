// POST /api/clip  -> { text } creates a paste, returns { id, url, ... }
// GET  /api/clip          -> latest paste (JSON)  | ?format=text -> raw text
// GET  /api/clip?id=XXXX  -> that paste (JSON)    | ?format=text -> raw text
//
// CLI examples:
//   curl -X POST $BASE/api/clip -H "Content-Type: application/json" -d '{"text":"hello"}'
//   echo "hello" | curl -X POST $BASE/api/clip -H "Content-Type: text/plain" --data-binary @-
//   curl $BASE/api/clip
//   curl "$BASE/api/clip?id=XXXX"
//   curl "$BASE/api/clip?id=XXXX&format=text"

const { saveClip, getClip, getLatest, storeKind } = require("./_store");

const MAX_LEN = 100000; // ~100KB per paste

function cors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    if (req.body !== undefined && req.body !== null) {
      if (typeof req.body === "string") return resolve(req.body);
      if (Buffer.isBuffer(req.body)) return resolve(req.body.toString("utf8"));
      if (typeof req.body === "object") return resolve(JSON.stringify(req.body));
    }
    let data = "";
    req.on("data", (c) => {
      data += c;
      if (data.length > MAX_LEN + 1024) {
        // stop abusive uploads early
        try {
          req.destroy();
        } catch {}
      }
    });
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

function baseUrl(req) {
  const proto = req.headers["x-forwarded-proto"] || "https";
  const host = req.headers["x-forwarded-host"] || req.headers.host || "";
  return host ? `${proto}://${host}` : "";
}

module.exports = async (req, res) => {
  cors(res);
  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }

  try {
    // ---------- CREATE ----------
    if (req.method === "POST") {
      const raw = await readBody(req);
      const ctype = String(req.headers["content-type"] || "");
      let text = "";

      if (ctype.includes("application/json")) {
        try {
          const parsed = JSON.parse(raw || "{}");
          text = typeof parsed.text === "string" ? parsed.text : String(parsed.text ?? "");
        } catch {
          res.status(400).json({ error: "Invalid JSON. Send {\"text\":\"...\"}" });
          return;
        }
      } else {
        // text/plain or piped binary -> treat whole body as text
        text = raw;
      }

      text = (text || "").replace(/\r\n/g, "\n");
      if (!text.trim()) {
        res.status(400).json({ error: "Empty text. Send {\"text\":\"...\"} or raw text body." });
        return;
      }
      if (text.length > MAX_LEN) {
        res.status(413).json({ error: `Text too large (max ${MAX_LEN} chars).` });
        return;
      }

      const rec = await saveClip(text);
      const base = baseUrl(req);
      res.status(201).json({
        id: rec.id,
        text: rec.text,
        len: rec.len,
        createdAt: rec.createdAt,
        url: base ? `${base}/?id=${rec.id}` : `/?id=${rec.id}`,
        apiUrl: base ? `${base}/api/clip?id=${rec.id}` : `/api/clip?id=${rec.id}`,
        store: storeKind(),
      });
      return;
    }

    // ---------- READ ----------
    if (req.method === "GET") {
      const url = new URL(req.url, "http://localhost");
      const id = url.searchParams.get("id");
      const format = url.searchParams.get("format");

      const rec = id ? await getClip(id) : await getLatest();
      if (!rec) {
        if (format === "text") {
          res.status(404).send(id ? "not found" : "empty — no pastes yet");
          return;
        }
        res.status(404).json({
          error: id ? `No paste with id "${id}"` : "No pastes yet. POST /api/clip to create one.",
          store: storeKind(),
        });
        return;
      }

      if (format === "text") {
        res.setHeader("Content-Type", "text/plain; charset=utf-8");
        res.status(200).send(rec.text);
        return;
      }

      res.status(200).json({ ...rec, store: storeKind() });
      return;
    }

    res.status(405).json({ error: "Method not allowed. Use GET or POST." });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Internal error", detail: String(err && err.message || err) });
  }
};
