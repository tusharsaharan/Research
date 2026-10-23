import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "bench"))
import conformal_cascade as cc  # noqa: E402


def _row(i, lang, samples, gold="1", pc=1):
    g = {"item_id": f"x{i}", "lang": lang, "split": "cert", "task": "mcq", "premium_correct": pc,
         "cost_premium_usd": 1.0, "cost_cheap_usd": 0.0}
    return g, {"samples": [f"#### {s}" for s in samples]}


def test_cc_synthetic():
    grades, answers = [], {}
    for i in range(20):
        lang = "english" if i % 2 == 0 else "hinglish"
        g, a = _row(i, lang, ["A"] * 16 if i % 5 else ["A"] * 8 + ["B"] * 8)
        grades.append(g)
        answers[f"x{i}|{lang}"] = a
    items = {f"x{i}": {"gold": "A"} for i in range(20)}
    rows = cc.build_rows(grades, answers, items)
    assert len(rows) == 20 and rows[0]["mode"] == "A"
    q = cc.qhat(rows, 0.2)
    assert q == 0.0 or q == 0.5
    assert cc.accept(rows[1], 0.0) and not cc.accept(rows[0], 0.5)
    rep = cc.run(rows, 5, [0.1], 1)
    assert {r["method"] for r in rep["results"]} == {"cc_marginal", "cc_perlang"}
    assert cc.qhat(rows[:2], 0.01) == float("inf")
