import { createFileRoute } from "@tanstack/react-router";
import { DataTable, Page, SectionHeading, Source } from "../components/site/SiteChrome";

export const Route = createFileRoute("/results")({
  head: () => ({
    meta: [
      { title: "Results — Code-Mixed Gateway" },
      {
        name: "description",
        content:
          "Measured results for the prompt compressor and the per-language router, with the file each number comes from.",
      },
    ],
  }),
  component: ResultsPage,
});

function ResultsPage() {
  return (
    <Page
      eyebrow="Results"
      title="Measured results"
      lede="Every number below comes from a file in backend/data/bench produced by a committed script. Differences are paired Wilcoxon or McNemar tests."
    >
      <section>
        <SectionHeading kicker="Compression" title="Against LLMLingua-2" />
        <p className="mb-6 max-w-2xl text-[15px] leading-relaxed text-muted-foreground">
          F1 of our compressor minus the baseline, at matched or fewer tokens. The settings were
          frozen on HotpotQA before these datasets were run. Answers by Qwen2.5-3B.
        </p>
        <DataTable
          head={["Dataset", "Uncompressed F1", "Keep 50%", "Keep 33%", "Keep 25%", "Keep 20%"]}
          rows={[
            ["SQuAD v2 (400)", "76.1", "+11.5", "+16.7", "+18.4", "+19.8"],
            ["MeetingBank-QA (367)", "59.1", "+1.6", "+4.3", "+11.9", "+15.6"],
            ["2WikiMultiHopQA (394)", "40.9", "-1.3", "+0.8", "+2.9", "+4.3"],
          ]}
        />
        <Source>docs/research/KEY_RESULTS.md section P (LLMLingua-2 base checkpoint)</Source>
      </section>

      <section className="mt-20">
        <SectionHeading kicker="Compression" title="Against stronger baselines" />
        <p className="mb-6 max-w-2xl text-[15px] leading-relaxed text-muted-foreground">
          Most of the margin above disappears against the large LLMLingua-2 checkpoint, and BM25
          sentence retrieval is better on single-paragraph text. The compressor is competitive, not
          state of the art.
        </p>
        <DataTable
          head={["Baseline", "Dataset", "Keep 50%", "Keep 33%"]}
          rows={[
            ["LLMLingua-2 large", "SQuAD v2", "+7.4", "+10.9"],
            ["LLMLingua-2 large", "MeetingBank-QA", "+0.8", "-0.2"],
            ["LLMLingua-2 large", "HotpotQA (144)", "-0.1", "-3.6"],
            ["BM25 sentences", "SQuAD v2", "-3.8", "-11.2"],
            ["BM25 sentences", "MeetingBank-QA", "+5.9", "+3.4"],
          ]}
        />
        <Source>docs/research/KEY_RESULTS.md section Q; backend/data/bench/baselines2</Source>
      </section>

      <section className="mt-20">
        <SectionHeading kicker="Routing" title="One threshold per language" />
        <p className="mb-6 max-w-2xl text-[15px] leading-relaxed text-muted-foreground">
          307 GSM8K questions asked in both English and Hinglish. The small model fails where the
          large one succeeds on 11.7% of English and 28.0% of Hinglish questions (p = 1.6e-7), so a
          single shared threshold breaks the error budget for one group. Error budget 10%, 1,000
          random calibration splits.
        </p>
        <DataTable
          head={[
            "Method",
            "EN budget broken",
            "EN cost saved",
            "HI budget broken",
            "HI cost saved",
          ]}
          rows={[
            ["Always large model", "0%", "0%", "0%", "0%"],
            ["Always small model", "83%", "100%", "100%", "100%"],
            ["Shared threshold (LTT)", "50%", "91%", "2%", "15%"],
            ["Uncalibrated per language", "53%", "92%", "47%", "42%"],
            ["Per-language threshold (LTT, ours)", "4%", "53%", "6%", "20%"],
          ]}
        />
        <Source>
          backend/data/bench/router_baselines_table_paired_gsm8k.md; paired_urate_gsm8k.json
        </Source>
      </section>
    </Page>
  );
}
