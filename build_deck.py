"""Build Token-Optimisation review deck (blue/white research theme)."""

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
    fp.text = "Token Optimisation  •  Guide: Sonali Agrawal"
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
        r.text = "▸  " + head
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


# ---- 1 title ----
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
for i, line in enumerate(["Tushar Saharan  •  Shivam Kumar  •  Sahil Gupta", "Guide: Sonali Agrawal"]):
    p = tb3.text_frame.paragraphs[0] if i == 0 else tb3.text_frame.add_paragraph()
    p.alignment = PP_ALIGN.CENTER
    p.text = line
    p.font.size = Pt(20 if i == 0 else 17)
    p.font.bold = (i == 0)
    p.font.color.rgb = WHITE

# ---- 2 introduction ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Introduction")
bullets(body_box(s, top), [
    ("Code mixed gateway.", "Tests if LLMLingua-2 savings hold on Hindi English mixed task dialogue."),
    ("Measured cost.", "Cost is read from real provider receipts with model name and price date."),
    ("Entity safety.", "Emails, phones, amounts, code and URLs are masked, compressed around, restored byte for byte."),
    ("Routing study.", "Router fine tuning, difficulty scoring, conformal calibration and graded sets live with the cascade report."),
])

# ---- 3 motivation ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Motivation")
bullets(body_box(s, top), [
    ("Billing is per token.", "Prompt length and model choice are the two largest levers on serving cost."),
    ("English tuned tokenizers.", "Same meaning in mixed text splits into more tokens, so mixed users pay more."),
    ("Published proof is narrow.", "Large savings at small loss are reported on clean English: GSM8K, MeetingBank, ShareGPT, LongBench."),
    ("Least tested domain.", "Hindi English switching with transliteration and informal spelling has no rigorous tradeoff measurement."),
])

# ---- 4 research problem ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Research Problem")
bullets(body_box(s, top), [
    ("RQ1 transfer.", "At what achieved kept level does code mixed task success decline against the uncompressed prompt."),
    ("RQ2 economics.", "What input token and end to end cost cut follows at each level for a stated model and pricing date."),
    ("RQ3 failure mode.", "Are losses in entities, digits, code, or mixed language spans."),
    ("RQ4 recovery.", "Does protected span handling recover quality at the same achieved rate, and what compression does it cost."),
    ("Rule.", "Independent variable is the achieved kept ratio, never the requested rate."),
])

# ---- 5 literature review ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Literature Review")
bullets(body_box(s, top), [
    ("Used: LLMLingua-2 ACL 2024.", "Trained baseline. Package 0.2.2 plus bert base multilingual meetingbank checkpoint on CPU."),
    ("Used: LLMLingua EMNLP 2023.", "Budget controlled pruning reference. Our heuristic comparator mirrors filler pruning."),
    ("Used: PRESTO.", "Primary eval dataset with structured parses as machine checkable gold."),
    ("Used: Hinglish-Instruct.", "Sujalvc/hinglish-instruct-dataset (10,378 romanized prompts, 300-prompt pilot slice) for cascade routing calibration."),
    ("Cited only.", "LongLLMLingua, Petrov tokenizer fairness, FrugalGPT, RouteLLM, X-RiSAWOZ, GupShup, GLUECoS."),
])

# ---- 6 research gap ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Research Gap")
bullets(body_box(s, top), [
    ("Clean English only.", "Prior compression proof does not cover code switching, transliteration and informal spelling."),
    ("Tokenizer fairness gap.", "Identical content can cost far more tokens by language. Mixed text is plausibly the most overcharged and least studied."),
    ("Span survival never measured.", "Base paper never reports protected span survival. We measure it on identical inputs: raw vs protected."),
    ("No romanized cover yet.", "PRESTO Hindi has zero romanized rows. Romanized arm is reserved for GupShup, not claimed here."),
])

# ---- 7 problem statement ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Problem Statement")
bullets(body_box(s, top), [
    ("Claim under test.", "Published LLMLingua-2 quality cost tradeoff transfers to Hindi English code mixed task prompts."),
    ("Pre registered.", "Primary metric is task completion score. Margin minus 0.05 absolute on variant minus reference."),
    ("Stats rule.", "Lower 95 percent dialogue clustered paired bootstrap bound, 10000 replicates, seed 20260926."),
    ("Rates.", "Requested kept 0.90, 0.70, 0.50, 0.30. Protected recall bar 0.995 lower CI. No loss is never declared from a p value."),
])

# ---- 8 proposed framework ----
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
note = s.shapes.add_textbox(Emu(900000), y + bh + Emu(400000), W - Emu(1800000), Emu(1600000))
note.text_frame.word_wrap = True
p = note.text_frame.paragraphs[0]
p.text = "A0 none, A1 LLMLingua-2, A2 LLMLingua-2 plus protected spans, A3 heuristic. Shell fixed byte identical, history only compressed. d(x) = 0.40 mix + 0.30 entity + 0.20 math + 0.10 length."
p.font.size = Pt(15)
p.font.color.rgb = GREY
p.alignment = PP_ALIGN.CENTER

# ---- 9 dataset ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Dataset: PRESTO")
bullets(body_box(s, top), [
    ("Release.", "PRESTO v1, CC BY 4.0. 415,990,813 bytes. SHA 1fc67169 to cca2167f. 550K plus human task conversations."),
    ("Why fit.", "Real multi turn tasks, structured parses as gold with intent plus slots, hi-IN mixing partition with 5804 rows."),
    ("Splits.", "Deterministic seed 20260926 at example id level. Smoke 20, dev 150, test 500 frozen with zero rows called."),
    ("Script audit.", "Test is mixed 397, devanagari 103, romanized 0. Romanized claim needs a second arm, not made here."),
    ("Adapter.", "hi-IN only, targets parsed to gold at 100 percent parse rate, 21495 unique examples, 0 schema exclusions."),
])

# ---- 10 compression record ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Results: Compression Record")
add_table(s, top, [
    ("Split", "A1 kept", "A2 kept", "Heuristic"),
    ("Smoke 260 rows", "0.710", "0.708", "0.987"),
    ("Dev 1950 rows", "0.709", "0.704", "0.987"),
    ("Total 2210 rows", "100 pct ok", "0 fallbacks", "measured"),
])
note_box(s, int(top) + Emu(4800000), "Source: backend/results/presto-002/compression smoke and dev jsonl. Experiment suite 20 of 20 pass.")

# ---- 11 protected spans ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Results: Protected Span Survival")
add_table(s, top, [
    ("Arm", "Smoke recall", "Dev recall", "Rows"),
    ("A1 raw", "0.80, min 0.00", "0.69, min 0.00", "680"),
    ("A2 protected", "1.00, min 1.00", "1.00, min 1.00", "680"),
])
note_box(s, int(top) + Emu(4800000), "Same kept to 3 decimals. Worst raw case user at example dot com split into 3 tokens is intact in A2 by byte reinject.")

# ---- 12 quality + cost ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Results: Quality and Cost (Pilot)")
add_table(s, top, [
    ("Arm at rate", "n", "Mean", "Delta vs A0"),
    ("A0 uncompressed", "20", "0.55", "reference"),
    ("A1 at 0.30", "20", "0.625", "+0.075"),
    ("A1 at 0.50", "20", "0.60", "+0.050"),
    ("A1 at 0.70", "20", "0.525", "minus 0.025"),
    ("A1 at 0.90", "20", "0.575", "+0.025"),
    ("A3 heuristic", "20", "0.00", "about minus 0.55"),
], heights=Emu(5000000))
note_box(s, int(top) + Emu(5600000), "Judge gemini-3.6-flash blinded. Valid 114 of 129. A1 tied at all rates, all CIs cross zero. Answer 572318 in plus 260340 out, 0.2421 USD list, billed 0.00.")

# ---- 13 routing + failures ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Routing Study and Fixes")
bullets(body_box(s, top), [
    ("Live study.", "Router fine tuning, difficulty scoring, conformal calibration, graded sets and status report at backend/experiments/cascade_routing."),
    ("Fixed: entities.", "Raw classifier mangled spans. Fix is mask plus force tokens plus digit reserve. A2 recall 1.000."),
    ("Fixed: segments.", "Context filter gave 4 in 3 out with shifted rows. Fix is always off plus alignment assert."),
    ("Fixed: serving.", "Cloudflare 1010 false dead key fixed by httpx plus browser UA. 256 cap with 148 empties fixed by 1024 cap."),
    ("Fixed: scoring.", "Ungraded pairs scored 0.0 fixed by graded only join. 7 duplicate writer rows found and removed."),
    ("Blocked now.", "6 Gemini keys at daily 429. About 2000 dev grades pending quota reset. 100 row human audit labeling pending."),
])

# ---- 14 limitations + conclusion ----
s = prs.slides.add_slide(BLANK)
top = bar(s, "Limitations and Conclusion")
bullets(body_box(s, top, Emu(5200000)), [
    ("Limits.", "Pilot n20 with wide CIs. Devanagari only, zero romanized. Single model zero shot baseline about 0.55. Judge not human audited yet."),
    ("No overclaim.", "No test set claim. No production savings claim. No general Hinglish claim. Test 500 frozen, zero rows called."),
    ("Conclusion.", "A1 tied with uncompressed at all rates. Heuristic is 0.00 at all rates including 0.90. Protected handling gives 1.000 recall at same rate."),
])
cards(s, H - Emu(2900000), [
    ("2210 rows", "100 pct ok, 0 fallbacks"),
    ("Recall 1.000", "Protected spans intact"),
    ("114 graded", "Pilot tie, dev next"),
])

prs.save("Token-Optimisation-Review.pptx")
print("saved Token-Optimisation-Review.pptx, slides:", len(prs.slides._sldIdLst))
