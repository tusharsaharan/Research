import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Code-Mixed Gateway" },
      {
        name: "description",
        content:
          "A gateway that compresses prompts, routes each one to the cheapest model that can answer it, and prices every call. Built and tested on Hindi–English text.",
      },
    ],
  }),
  component: Index,
});

const STAGES = [
  {
    n: "01",
    title: "Compress",
    body: "Keeps the sentences that matter for the question, then removes filler words inside them. Numbers, emails, amounts and names are protected from deletion.",
  },
  {
    n: "02",
    title: "Route",
    body: "A small scorer predicts whether gpt-oss-20b will answer as well as gpt-oss-120b. Its threshold is calibrated separately for English and Hinglish, so the error budget holds for both.",
  },
  {
    n: "03",
    title: "Price",
    body: "Each call is priced from its actual token counts at list rates, input and output separately. Savings are the difference against sending the full prompt to the large model.",
  },
];

const FINDINGS = [
  {
    value: "+7 to +11",
    unit: "F1",
    text: "over LLMLingua-2 (large) on SQuAD v2 when keeping half to a third of the tokens. Ties on MeetingBank and HotpotQA.",
  },
  {
    value: "53% / 20%",
    unit: "saved",
    text: "API cost with per-language routing at a 10% error budget, English / Hinglish. The budget held in at least 94% of 1,000 re-splits for both.",
  },
  {
    value: "28% vs 12%",
    unit: "",
    text: "of questions the small model gets wrong and the large one gets right, Hinglish vs English. One shared threshold cannot serve both.",
  },
];

function Index() {
  return (
    <main>
      <section className="mx-auto max-w-5xl px-6 pt-20 pb-24 sm:pt-28">
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">
          LLM gateway · Hindi–English
        </p>
        <h1 className="mt-6 max-w-3xl text-5xl leading-[1.04] sm:text-[4.25rem]">
          Shorter prompts, the right model, and a bill you can check.
        </h1>
        <p className="mt-7 max-w-2xl text-lg leading-relaxed text-muted-foreground">
          The gateway sits in front of an LLM API. It compresses each prompt, sends it to the
          cheaper model when that model is likely to be right, and records what the call cost. It is
          tuned and tested on Hinglish, the way most people in India actually type.
        </p>
        <div className="mt-10 flex flex-wrap items-center gap-6">
          <Link
            to="/demo"
            className="rounded-full bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Run a prompt
          </Link>
          <Link
            to="/cost"
            className="text-sm font-medium text-foreground underline decoration-border underline-offset-[6px] hover:decoration-foreground"
          >
            Estimate your cost
          </Link>
        </div>
      </section>

      <section className="border-y border-border/70 bg-card/60">
        <div className="mx-auto grid max-w-5xl gap-12 px-6 py-20 md:grid-cols-3 md:gap-10">
          {STAGES.map((s) => (
            <div key={s.n}>
              <p className="font-mono text-xs text-primary">{s.n}</p>
              <h2 className="mt-3 text-3xl">{s.title}</h2>
              <p className="mt-4 text-[15px] leading-relaxed text-muted-foreground">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 py-24">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h2 className="text-3xl sm:text-4xl">What we measured</h2>
          <Link
            to="/results"
            className="text-sm text-muted-foreground underline decoration-border underline-offset-[6px] hover:text-foreground"
          >
            Full results and sources
          </Link>
        </div>
        <div className="mt-12 grid gap-px overflow-hidden rounded-xl border border-border bg-border md:grid-cols-3">
          {FINDINGS.map((f) => (
            <div key={f.value} className="bg-background p-7">
              <p className="font-serif text-4xl text-foreground">
                {f.value}
                {f.unit ? (
                  <span className="ml-2 font-sans text-sm text-muted-foreground">{f.unit}</span>
                ) : null}
              </p>
              <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{f.text}</p>
            </div>
          ))}
        </div>
        <p className="mt-5 text-xs leading-relaxed text-muted-foreground">
          Answers from Qwen2.5-3B (compression) and gpt-oss-20b / 120b (routing). The compressor is
          competitive, not state of the art: BM25 sentence retrieval beats it on SQuAD.
        </p>
      </section>
    </main>
  );
}
