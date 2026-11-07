// GET /api/clips?limit=20 -> [{ id, preview, len, createdAt }]
const { listClips, storeKind } = require("./_store");

module.exports = async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }
  if (req.method !== "GET") {
    res.status(405).json({ error: "Use GET." });
    return;
  }
  try {
    const url = new URL(req.url, "http://localhost");
    const items = await listClips(url.searchParams.get("limit") || 20);
    res.status(200).json({ items, store: storeKind() });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Internal error" });
  }
};
