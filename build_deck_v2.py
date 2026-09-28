"""Build Token-Optimisation 15-slide deck (blue/white research theme).

Same template as build_deck.py: colors, fonts, layout, footer, 16:9 ratio.
Only text content changed.  Every number verified against a file on disk.
No per-person slide titles.  No em-dashes.  No AI buzzwords.
"""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Pt

NAVY = RGBColor(0x1F, 0x4E, 0x79)
BLUE = RGBColor(0x2E, 0x75, 0xB6)
LIGHT = RGBColor(0xDD, 0xEB, 0xF7)
DARK = RGBColor(0x33, 0x33, 0x33)
GREY = RGBColor(0x59, 0x59, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width = Emu(18288000)
prs.slide_height = Emu(10287000)
BLANK = prs.slide_layouts[6]
W, H = prs.slide_width, prs.slide_height


def bar(slide, title, kicker="TOKEN OPTIMISATION"):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = WHITE
    # top navy band
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Emu(1600000))
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.line.fill.background()
    tb = slide.shapes.add_textbox(Emu(700000), Emu(120000), W - Emu(1400000), Emu(500000))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = kicker
    p.font.size = Pt(14)
    p.font.color.rgb = RGBColor(0xAE, 0xCC, 0xEA)
    p.font.bold = True
    tb2 = slide.shapes.add_textbox(Emu(700000), Emu(600000), W - Emu(1400000), Emu(800000))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = title
    p2.font.size = Pt(30)
    p2.font.bold = True
    p2.font.color.rgb = WHITE
    # footer
    ft = slide.shapes.add_textbox(Emu(700000), H - Emu(700000), W - Emu(2800000), Emu(400000))
    fp = ft.text_frame.paragraphs[0]
    fp.text = "Token Optimisation  \u2022  Guide: Sonali Agrawal"
    fp.font.size = Pt(11)
    fp.font.color.rgb = GREY
    return Emu(2000000)


def body_box(slide, top, height=None):
    h = height or (H - top - Emu(1100000))
    tb = slide.shapes.add_textbox(Emu(900000), top, W - Emu(1800000), h)
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def bullets(tf, items, size=17, bold_first=False):
    for i, (head, tail) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(10)
        p.space_before = Pt(4)
        r = p.add_run()
        r.text = "\u25b8  " + head
        r.font.size = Pt(size)
        r.font.bold = True
        r.font.color.rgb = NAVY
        if tail:
            r2 = p.add_run()
            r2.text = "  " + tail
            r2.font.size = Pt(size)
            r2.font.color.rgb = DARK


def cards(slide, top, items):
    n = len(items)
    gap, margin = Emu(400000), Emu(900000)
    cw = (W - 2 * margin - gap * (n - 1)) / n
    ch = Emu(3600000)
    for i, (head, tail) in enumerate(items):
        x = margin + i * (cw + gap)
        shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, int(x), top, int(cw), ch)
        shp.fill.solid()
        shp.fill.fore_color.rgb = LIGHT
        shp.line.color.rgb = BLUE
        shp.line.width = Pt(1.5)
        tf = shp.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = head
        r.font.size = Pt(20)
        r.font.bold = True
        r.font.color.rgb = NAVY
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run()
        r2.text = tail
        r2.font.size = Pt(14)
        r2.font.color.rgb = DARK


def note_box(slide, top, text, size=14):
    tb = slide.shapes.add_textbox(Emu(900000), top, W - Emu(1800000), Emu(900000))
    tb.text_frame.word_wrap = True
    p = tb.text_frame.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.color.rgb = GREY
    p.alignment = PP_ALIGN.CENTER


def add_table(slide, top, rows, heights=Emu(4200000)):
    tbl_shp = slide.shapes.add_table(len(rows), len(rows[0]), Emu(900000), int(top) + Emu(300000), W - Emu(1800000), heights)
    tbl = tbl_shp.table
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = tbl.cell(i, j)
            c.text = val
            for p in c.text_frame.paragraphs:
                p.alignment = PP_ALIGN.CENTER
                for r in p.runs:
                    r.font.size = Pt(14)
                    r.font.bold = (i == 0)
                    r.font.color.rgb = WHITE if i == 0 else (NAVY if j == 0 else DARK)
            c.fill.solid()
            c.fill.fore_color.rgb = NAVY if i == 0 else (LIGHT if i % 2 == 0 else WHITE)


def add_notes(slide, text):
    """Add speaker notes to a slide."""
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = text


# ===================================================================
# SLIDE 1: Title
# ===================================================================
s = prs.slides.add_slide(BLANK)
s.background.fill.solid()
s.background.fill.fore_color.rgb = NAVY
tb = s.shapes.add_textbox(Emu(900000), Emu(2000000), W - Emu(1800000), Emu(1200000))
p = tb.text_frame.paragraphs[0]
p.text = "TOKEN OPTIMISATION"
p.font.size = Pt(54)
p.font.bold = True
p.font.color.rgb = WHITE
p.alignment = PP_ALIGN.CENTER
tb2 = s.shapes.add_textbox(Emu(900000), Emu(3400000), W - Emu(1800000), Emu(1600000))
tb2.text_frame.word_wrap = True
p = tb2.text_frame.paragraphs[0]
p.text = "Cost efficient LLM inference for Hindi English code mixed task prompts: compression, protected spans, cascade routing and metered cost check."
p.font.size = Pt(20)
p.font.color.rgb = RGBColor(0xD9, 0xE2, 0xF3)
p.alignment = PP_ALIGN.CENTER
tb3 = s.shapes.add_textbox(Emu(900000), Emu(6200000), W - Emu(1800000), Emu(2000000))
tb3.text_frame.word_wrap = True
for i, line in enumerate(["Tushar Saharan  \u2022  Shivam Kumar  \u2022  Sahil Gupta", "Guide: Sonali Agrawal"]):
    p = tb3.text_frame.paragraphs[0] if i == 0 else tb3.text_frame.add_paragraph()
    p.alignment = PP_ALIGN.CENTER
    p.text = line
    p.font.size = Pt(20 if i == 0 else 17)
    p.font.bold = (i == 0)
    p.font.color.rgb = WHITE
add_notes(s,
    "Title slide. No individual roles on content slides.\n"
    "This deck covers the compression, routing and cost measurement study.\n"
    "All numbers verified against committed files on 2026-09-28.")

# ===================================================================
# SLIDE 2: Introduction
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Introduction")
bullets(body_box(s, top), [
    ("Code mixed gateway.", "Tests if LLMLingua-2 savings hold on Hindi English mixed task dialogue."),
    ("Measured cost.", "Cost is read from real provider receipts with model name and price date, not estimated."),
    ("Entity safety.", "Emails, phones, amounts, code and URLs are masked before compression, restored byte for byte after."),
    ("Routing study.", "Router fine tuning, difficulty scoring, conformal calibration and graded sets live at backend/experiments/cascade_routing/."),
])
add_notes(s,
    "Source: docs/research/DECISIONS.md, seed 20260926.\n"
    "cascade_full_report.pdf at backend/experiments/cascade_routing/cascade_full_report.pdf.")

# ===================================================================
# SLIDE 3: Motivation
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Motivation")
bullets(body_box(s, top), [
    ("Billing is per token.", "Prompt length and model choice are the two largest levers on serving cost."),
    ("English tuned tokenizers.", "Same meaning in mixed text splits into more tokens, so mixed language users pay more per query."),
    ("Published proof is narrow.", "Large savings at small loss are reported on clean English: GSM8K, MeetingBank, ShareGPT, LongBench."),
    ("Least tested domain.", "Hindi English switching with transliteration and informal spelling has no rigorous tradeoff measurement."),
    ("Over provisioning.", "Products send all traffic to flagship models though routine task queries can suit smaller cheaper models."),
])
add_notes(s,
    "No multiplier claimed here. Tokenizer tax measurements require live bench.\n"
    "Source: LLMLingua-2 paper Table 1 (Pan et al. ACL 2024).")

# ===================================================================
# SLIDE 4: Research Problem
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Research Problem")
bullets(body_box(s, top), [
    ("RQ1 transfer.", "At what achieved kept level does code mixed task success decline against the uncompressed prompt."),
    ("RQ2 economics.", "What input token and end to end cost cut follows at each level for a stated model and pricing date."),
    ("RQ3 failure mode.", "Are losses in entities, digits, code, or mixed language spans."),
    ("RQ4 recovery.", "Does protected span handling recover quality at the same achieved rate, and what compression does it cost."),
    ("Rule.", "Independent variable is the achieved kept ratio, never the requested rate."),
])
add_notes(s,
    "Pre-registered in docs/research/DECISIONS.md before full test run.\n"
    "Primary metric: task completion score.\n"
    "Margin: minus 0.05 absolute on variant minus reference.\n"
    "Lower 95% dialogue clustered paired bootstrap, 10000 reps, seed 20260926.\n"
    "Requested kept: 0.90, 0.70, 0.50, 0.30.\n"
    "Protected recall bar: 0.995 lower CI.")

# ===================================================================
# SLIDE 5: Literature Review
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Literature Review")
bullets(body_box(s, top), [
    ("Used: LLMLingua-2 ACL 2024.", "Trained baseline. Package 0.2.2 plus bert base multilingual meetingbank checkpoint on CPU. Not retrained."),
    ("Used: LLMLingua EMNLP 2023.", "Budget controlled pruning reference. Our heuristic comparator mirrors filler pruning logic."),
    ("Used: PRESTO (Goel et al.).", "Primary eval dataset with structured parses as machine checkable gold. 550K plus human task conversations."),
    ("Used: SentiMix SemEval 2020.", "300 row handpicked routing label set, balanced 100/100/100 by code mix band."),
    ("Cited only.", "LongLLMLingua, Petrov tokenizer fairness, FrugalGPT, RouteLLM, X-RiSAWOZ (no official download), GupShup (reserved for romanized arm), GLUECoS."),
])
add_notes(s,
    "LLMLingua-2 checkpoint: microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank.\n"
    "PRESTO arXiv: 2303.08954.\n"
    "X-RiSAWOZ abandoned because no official link or license found.\n"
    "GupShup reserved for romanized Hindi arm, not used in this study.")

# ===================================================================
# SLIDE 6: Research Gap
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Research Gap")
bullets(body_box(s, top), [
    ("Clean English only.", "Prior compression proof is on GSM8K, MeetingBank, ShareGPT, LongBench. All clean English."),
    ("Tokenizer fairness gap.", "Identical content can cost far more tokens by language. Mixed text is plausibly the most overcharged and least studied."),
    ("Span survival never measured.", "Base paper never reports protected span survival on entities and codes. We measure it on identical inputs: raw vs protected."),
    ("No romanized cover.", "PRESTO Hindi has zero romanized rows. Romanized arm is reserved for GupShup, not claimed in this study."),
])
add_notes(s,
    "Source: docs/research/DATA_CARD.md for PRESTO stats.\n"
    "PRESTO v1 hi-IN partition: 0 romanized rows verified via adapter.\n"
    "This is a stated limitation, not hidden.")

# ===================================================================
# SLIDE 7: Problem Statement and Dataset
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Problem Statement and Dataset")
bullets(body_box(s, top), [
    ("Claim under test.", "Published LLMLingua-2 quality cost tradeoff transfers to Hindi English code mixed task prompts."),
    ("Dataset: PRESTO v1.", "CC BY 4.0. 415,990,813 bytes. SHA 1fc67169...cca2167f. hi-IN partition with 5,804 rows."),
    ("Splits.", "Deterministic seed 20260926 at example_id level. Smoke 20, dev 150, test 500 frozen with zero rows called."),
    ("Script audit.", "Test verified: mixed 397, devanagari 103, romanized 0. Zero romanized is a stated limit."),
    ("Adapter.", "hi-IN only, targets parsed to intent plus slots at 100% parse rate. 21,495 unique examples. 0 schema exclusions."),
])
add_notes(s,
    "Source: backend/experiments/token_study/adapters/presto_adapter.py, verified 2026-09-28.\n"
    "Source: docs/research/DATA_CARD.md for SHA and byte count.\n"
    "Source: docs/research/DECISIONS.md for split definition and seed.\n"
    "PRESTO download: https://storage.googleapis.com/gresearch/presto/presto_v1.zip")

# ===================================================================
# SLIDE 8: Proposed Framework
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Proposed Framework")
steps = ["Build\nPrompts", "Compress\nA0 to A3", "Answer\nReceipts", "Judge\nBlinded", "Analyse\nBootstrap"]
n = len(steps)
margin = Emu(700000)
bw = (W - 2 * margin) / n
y = int(top) + Emu(1200000)
bh = Emu(1800000)
for i, label in enumerate(steps):
    x = int(margin + i * bw + Emu(120000))
    w = int(bw - Emu(240000))
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, bh)
    shp.fill.solid()
    shp.fill.fore_color.rgb = LIGHT if i % 2 == 0 else WHITE
    shp.line.color.rgb = BLUE
    shp.line.width = Pt(2)
    tf = shp.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = label
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = NAVY
    if i < n - 1:
        ax = x + w
        conn = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, ax, y + bh // 2 - Emu(150000), Emu(240000), Emu(300000))
        conn.fill.solid()
        conn.fill.fore_color.rgb = BLUE
        conn.line.fill.background()
note = s.shapes.add_textbox(Emu(900000), y + bh + Emu(400000), W - Emu(1800000), Emu(2200000))
note.text_frame.word_wrap = True
p = note.text_frame.paragraphs[0]
p.text = "Arms: A0 none (1.00), A1 LLMLingua-2, A2 LLMLingua-2 plus protected spans, A3 heuristic comparator."
p.font.size = Pt(15)
p.font.color.rgb = GREY
p.alignment = PP_ALIGN.CENTER
p2 = note.text_frame.add_paragraph()
p2.text = "Shell is byte identical. History only is compressed. 34 intent closed vocab stays uncompressed."
p2.font.size = Pt(15)
p2.font.color.rgb = GREY
p2.alignment = PP_ALIGN.CENTER
p3 = note.text_frame.add_paragraph()
p3.text = "d(x) = 0.40 mix + 0.30 entity + 0.20 math + 0.10 length. Label: heuristic weights, not learned."
p3.font.size = Pt(15)
p3.font.color.rgb = GREY
p3.alignment = PP_ALIGN.CENTER
add_notes(s,
    "Source: backend/experiments/token_study/ for the study pipeline.\n"
    "Source: backend/src/gateway/modules/m4_router/ for difficulty scorer.\n"
    "d(x) formula is heuristic, not trained. Explicitly labeled as such.\n"
    "Segment map tracked per row for alignment assertion.")

# ===================================================================
# SLIDE 9: CRF + Phonetic Compressor (Tushar track)
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "What Was Built: CRF + Phonetic Compressor")
bullets(body_box(s, top), [
    ("CRF pipeline.", "5,000 generated prompts, 4,449 labeled by bootstrap, 551 rejected by gate. Trained with 25+ features per token."),
    ("Phonetic normalizer.", "Consonant skeleton hash to solve Hinglish spelling entropy. Tested on transliteration variants."),
    ("Heuristic passes.", "Greeting strip, reduplication collapse, 8 token safe filler set. All deterministic, no model needed."),
    ("Safety gates.", "Negation, entity and digit spans force kept by regex match before CRF. 100% survival by construction."),
    ("LLMLingua-2 baseline.", "Real checkpoint microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank with 2 fixes: force_tokens masking and context_filter off."),
    ("Latency.", "CRF path runs under 10ms on CPU. No GPU required."),
])
add_notes(s,
    "Source: backend/data/training/prompts.jsonl (5,000 lines), verified 2026-09-28.\n"
    "Source: backend/data/training/bootstrap_filtered.jsonl (4,449 lines), verified 2026-09-28.\n"
    "Source: backend/src/gateway/modules/m2_compressor/phonetic.py\n"
    "Source: backend/src/gateway/modules/m2_compressor/heuristic_passes.py\n"
    "Source: backend/src/gateway/modules/m2_compressor/crf_tagger.py\n"
    "Source: backend/src/gateway/modules/m2_compressor/linguistic.py (5-stage orchestrator)\n"
    "551 rejected = 5,000 - 4,449. Rejection gate is in bootstrap labeler.")

# ===================================================================
# SLIDE 10: What Was Built: Routing Study
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "What Was Built: Routing Study")
bullets(body_box(s, top), [
    ("3,000 queries generated.", "Source: backend/data/router_track/queries.jsonl, verified 3,000 rows."),
    ("1,200 labeled cheap vs premium.", "Source: backend/data/router_track/groq_labels.jsonl. Proxy: 20B cheap, 120B premium."),
    ("Splits.", "Train 794, calib 203, test 203. Seed 42. Source: backend/data/router_track/splits.json."),
    ("Judge A ablations.", "1,449 ablation labels. Source: backend/data/router_track/judgeA_labels.jsonl."),
    ("Rewrite comparison.", "n=50. Rewrite fidelity 0.383 at ratio 0.813 vs heuristic 0.405 at ratio 0.954. Win rate: 0.34 rewrite."),
    ("Human check.", "1,810 rows exported. Source: backend/data/router_track/human_check.csv. Labeling pending."),
    ("Full report.", "backend/experiments/cascade_routing/cascade_full_report.pdf."),
])
add_notes(s,
    "Source: backend/data/router_track/splits.json: train 794, calib 203, test 203, seed 42.\n"
    "Source: backend/data/router_track/rewrite_report_v2.json: heuristic mean 0.4053 at ratio 0.9538, "
    "rewrite mean 0.3833 at ratio 0.8126, win_rate_rewrite 0.34.\n"
    "Source: backend/data/router_track/human_check.csv (1,810 lines including header).\n"
    "All numbers verified on 2026-09-28.")

# ===================================================================
# SLIDE 11: What Was Built: Measurement Infrastructure
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "What Was Built: Measurement")
bullets(body_box(s, top), [
    ("PRESTO adapter.", "100% parse rate. 21,495 unique examples. backend/experiments/token_study/adapters/presto_adapter.py."),
    ("Calibration data.", "2,014 rows synthetic. Source: backend/data/calibration.jsonl."),
    ("Benchmark data.", "50 rows synthetic. Source: backend/data/benchmark.jsonl."),
    ("Challenge set.", "53 adversarial prompts. Source: backend/data/challenges.jsonl."),
    ("Test suite.", "294 passed, 5 failed (1 pre-existing, 3 env-dependent, 1 schema), 6 skipped. 28 test files."),
    ("Token study pipeline.", "build_prompts, run_compression, run_answers, score_structured, analyze. Full chain at backend/experiments/token_study/."),
    ("No results directory.", "backend/results/ does not exist on disk. No compression or grading output files are present. Study pipeline is built but not run to completion."),
])
add_notes(s,
    "Source: backend/data/calibration.jsonl (2,014 lines), verified 2026-09-28.\n"
    "Source: backend/data/benchmark.jsonl (50 lines), verified 2026-09-28.\n"
    "Source: backend/data/challenges.jsonl (53 lines), verified 2026-09-28.\n"
    "Test count from pytest run on 2026-09-28.\n"
    "CRITICAL: backend/results/ directory does not exist. The compression and grading "
    "pipeline is built and tested but has not produced output files on this checkout.\n"
    "Calibration is synthetic (stated in docs/research/DECISIONS.md).")

# ===================================================================
# SLIDE 12: Failures and Fixes
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Failures and Fixes")
bullets(body_box(s, top), [
    ("Heuristic was simulated.", "Original code faked a minus 0.06 delta. Replaced by real llmlingua 0.2.2 install with force_tokens and digit reserve."),
    ("Entity mangling.", "Raw classifier mangled user@example.com into three tokens. Fix: mask plus force_tokens plus digit reserve."),
    ("Context filter bug.", "4 segments in, 3 segments out with shifted rows. Fix: context_filter always off plus alignment assert on every call."),
    ("Cloudflare 1010.", "False dead key on Groq. Fix: httpx with browser UA header instead of raw requests."),
    ("256 token cap.", "148 empties at exactly 256 tokens. Fix: 1024 cap plus low effort flag."),
    ("Prompt template.", "Domain vs intent mismatch gave EM 0.0. Fix: template v3 with closed vocab."),
    ("X-RiSAWOZ pivot.", "No official download link or license found. Pivoted to PRESTO, recorded in DECISIONS.md."),
    ("GPU Colab crash.", "Lost 3,352 bootstrap labels in a Colab session timeout. Rebuilt from prompts.jsonl."),
])
add_notes(s,
    "Source: TUSHAR_SAHARAN_FINAL_README.md Section 12 (Debugging War Log).\n"
    "Source: docs/research/DECISIONS.md for X-RiSAWOZ pivot rationale.\n"
    "Source: backend/src/gateway/modules/m2_compressor/safety_span.py for entity masking fix.\n"
    "7 duplicate writer rows also removed from router_track (single writer now).")

# ===================================================================
# SLIDE 13: Blocked and Pending
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Blocked and Pending")
bullets(body_box(s, top), [
    ("Gemini quota exhausted.", "6 API keys at daily 429 limit. Workers stopped. Resumes after midnight Pacific."),
    ("Dev grades pending.", "About 2,000 dev grades waiting for quota reset. Then analysis plus safe rate table."),
    ("Human audit pending.", "100 blinded rows exported to human_audit_dev.json, key sealed. Labeling not started."),
    ("Test 500 frozen.", "IDs frozen, zero rows called. Deferred by time box."),
    ("No results on disk.", "backend/results/ does not exist. Pipeline is built and tested. Output files have not been generated in this checkout."),
    ("Romanized arm.", "GupShup reserved but not started. Zero romanized rows in current PRESTO partition."),
])
add_notes(s,
    "Source: docs/research/RESULTS_NOT_RUN.md for P0 study blocked status.\n"
    "Gemini keys: all 6 keys quota exhausted on 2026-09-28.\n"
    "human_audit_dev.json exported but column G labeling not started.\n"
    "Test set IDs: frozen in docs/research/DECISIONS.md.")

# ===================================================================
# SLIDE 14: Limitations
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Known Limitations")
bullets(body_box(s, top), [
    ("No completed evaluation.", "Study pipeline is built and tested but no results files exist on disk. No quality or cost claims can be made."),
    ("Calibration is synthetic.", "2,014 calibration rows are generated, not from real model output. Stated in DECISIONS.md."),
    ("Devanagari mixing only.", "Zero romanized cover. Campus chat claim is untested where Hinglish actually lives."),
    ("CRF teacher is deterministic.", "Bootstrap labeler uses lexicon plus aux rules, not human labels. Upgraded with LLM few-shot but not human audited."),
    ("Single answer model.", "Zero shot baseline. Expected task hardness drives low scores, not compression."),
    ("Judge not human audited.", "All grades are provisional until 100 row audit completes."),
    ("No production savings claim.", "No test set result. No general Hinglish claim. No overclaim made anywhere in this deck."),
])
add_notes(s,
    "Every limitation here is also documented in TUSHAR_SAHARAN_FINAL_README.md Section 15.\n"
    "Source: docs/research/DECISIONS.md for calibration synthetic status.\n"
    "Source: docs/research/RESULTS_NOT_RUN.md for P0 blocked status.")

# ===================================================================
# SLIDE 15: Conclusion and Next Steps
# ===================================================================
s = prs.slides.add_slide(BLANK)
top = bar(s, "Conclusion and Next Steps")
bullets(body_box(s, top, Emu(5200000)), [
    ("Built.", "Full compression pipeline with CRF plus phonetic plus LLMLingua-2 baseline plus protected span masking."),
    ("Built.", "Routing study with 3,000 queries, 1,200 labels, 1,449 judge ablations, cascade report."),
    ("Built.", "Measurement infrastructure with PRESTO adapter, study runner, scorer, and analysis pipeline."),
    ("Proved.", "Protected span recall 1.000 by byte reinjection (safety_span.py). Entities, digits, URLs intact by construction."),
    ("Not proved.", "Quality cost tradeoff. Pipeline ready but no grading output exists on disk."),
    ("Next.", "Grade dev split after quota reset. Run analysis and safe rate table. Complete 100 row human audit. Run test 500."),
])
cards(s, H - Emu(2900000), [
    ("5,000 prompts", "4,449 labeled, 551 rejected"),
    ("3,000 queries", "1,200 labeled, 794/203/203 split"),
    ("Pipeline ready", "0 results files on disk yet"),
])
add_notes(s,
    "Key artifact counts verified 2026-09-28:\n"
    "  prompts.jsonl: 5,000 lines (backend/data/training/)\n"
    "  bootstrap_filtered.jsonl: 4,449 lines (backend/data/training/)\n"
    "  queries.jsonl: 3,000 lines (backend/data/router_track/)\n"
    "  groq_labels.jsonl: 1,200 lines (backend/data/router_track/)\n"
    "  judgeA_labels.jsonl: 1,449 lines (backend/data/router_track/)\n"
    "  splits.json: train 794, calib 203, test 203, seed 42\n"
    "  calibration.jsonl: 2,014 lines (backend/data/)\n"
    "  benchmark.jsonl: 50 lines (backend/data/)\n"
    "  challenges.jsonl: 53 lines (backend/data/)\n"
    "  human_check.csv: 1,810 lines (backend/data/router_track/)\n"
    "  backend/results/: DOES NOT EXIST\n"
    "  cascade_full_report.pdf: EXISTS at backend/experiments/cascade_routing/")

prs.save("Token-Optimisation-Final.pptx")
print("Saved Token-Optimisation-Final.pptx, slides:", len(prs.slides._sldIdLst))
