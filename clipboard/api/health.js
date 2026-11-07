// GET /api/health
const { storeKind } = require("./_store");

module.exports = async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.status(200).json({ ok: true, store: storeKind(), time: new Date().toISOString() });
};
