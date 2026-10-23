import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Page } from "../components/site/SiteChrome";
import { countTokensCl100k } from "../lib/tokenizer";
import { PRICING_DATE, TIERS, callCostUsd, formatUsd } from "../lib/pricing";

export const Route = createFileRoute("/cost")({
  head: () => ({
    meta: [
      { title: "Cost — Code-Mixed Gateway" },
      {
        name: "description",
        content:
          "Count the tokens in a prompt and estimate monthly LLM spend with and without compression and routing.",
      },
    ],
  }),
  component: CostPage,
});

const SAMPLE = {
  en: "My hostel wifi has been slow since yesterday. Where do I file a complaint? I have to submit an assignment tomorrow.",
  hi: "yaar mera hostel ka wifi kal se slow hai, complaint kahan karun? kal assignment submit karna hai",
};

function Field({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
}) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="font-mono text-sm">
          {value.toLocaleString("en-US")}
          {suffix}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-3 w-full accent-[var(--color-primary)]"
      />
    </label>
  );
}

function TokenCounter() {
  const [text, setText] = useState(SAMPLE.hi);
  const [tokens, setTokens] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    const id = setTimeout(() => {
      countTokensCl100k(text).then((n) => !cancelled && setTokens(n));
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(id);
    };
  }, [text]);

  return (
    <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
      <div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          aria-label="Prompt to count"
          className="block w-full resize-y rounded-xl border border-border bg-card px-5 py-4 text-[15px] leading-relaxed outline-none focus:border-primary/50"
        />
        <div className="mt-3 flex gap-5 text-sm">
          <button
            type="button"
            onClick={() => setText(SAMPLE.hi)}
            className="text-muted-foreground hover:text-foreground"
          >
            Hinglish sample
          </button>
          <button
            type="button"
            onClick={() => setText(SAMPLE.en)}
            className="text-muted-foreground hover:text-foreground"
          >
            English sample
          </button>
        </div>
      </div>
      <dl className="self-start rounded-xl border border-border bg-card px-6 py-2">
        <div className="flex items-baseline justify-between border-b border-border/60 py-3">
          <dt className="text-sm text-muted-foreground">Tokens (cl100k)</dt>
          <dd className="font-mono text-sm">{tokens ?? "-"}</dd>
        </div>
        {(["cheap", "premium"] as const).map((t) => (
          <div
            key={t}
            className="flex items-baseline justify-between border-b border-border/60 py-3 last:border-b-0"
          >
            <dt className="text-sm text-muted-foreground">{TIERS[t].model}, per 1,000 prompts</dt>
            <dd className="font-mono text-sm">
              {tokens != null ? formatUsd(1000 * callCostUsd(t, tokens, 0)) : "-"}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function Estimator() {
  const [perDay, setPerDay] = useState(10_000);
  const [inTok, setInTok] = useState(600);
  const [outTok, setOutTok] = useState(300);
  const [keep, setKeep] = useState(50);
  const [cheapShare, setCheapShare] = useState(40);

  const monthly = perDay * 30;
  const baseline = monthly * callCostUsd("premium", inTok, outTok);
  const keptIn = (inTok * keep) / 100;
  const share = cheapShare / 100;
  const withGateway =
    monthly *
    (share * callCostUsd("cheap", keptIn, outTok) +
      (1 - share) * callCostUsd("premium", keptIn, outTok));
  const pct = baseline > 0 ? Math.round((1 - withGateway / baseline) * 100) : 0;

  return (
    <div className="grid gap-10 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-7">
        <Field
          label="Requests per day"
          value={perDay}
          onChange={setPerDay}
          min={100}
          max={200_000}
          step={100}
        />
        <Field
          label="Input tokens per request"
          value={inTok}
          onChange={setInTok}
          min={20}
          max={8000}
          step={10}
        />
        <Field
          label="Output tokens per request"
          value={outTok}
          onChange={setOutTok}
          min={10}
          max={4000}
          step={10}
        />
        <Field
          label="Input kept after compression"
          value={keep}
          onChange={setKeep}
          min={20}
          max={100}
          suffix="%"
        />
        <Field
          label="Requests routed to the small model"
          value={cheapShare}
          onChange={setCheapShare}
          min={0}
          max={100}
          suffix="%"
        />
      </div>
      <div className="self-start rounded-xl border border-border bg-card p-7">
        <p className="text-sm text-muted-foreground">Every request to {TIERS.premium.model}</p>
        <p className="mt-1 font-serif text-3xl">{formatUsd(baseline)}</p>
        <p className="mt-6 text-sm text-muted-foreground">Through the gateway</p>
        <p className="mt-1 font-serif text-5xl text-primary">{formatUsd(withGateway)}</p>
        <p className="mt-6 border-t border-border/60 pt-4 text-sm">
          {pct}% lower, per 30-day month
        </p>
      </div>
    </div>
  );
}

function CostPage() {
  return (
    <Page
      eyebrow="Cost"
      title="What a prompt costs, and what it would cost through the gateway"
      lede="Token counts use the cl100k tokenizer as a stand-in. Prices are Groq list rates for the two study models."
    >
      <section>
        <h2 className="text-3xl">Count a prompt</h2>
        <p className="mt-2 mb-8 text-sm text-muted-foreground">
          Paste any prompt to see its token count and input cost on each model.
        </p>
        <TokenCounter />
      </section>

      <section className="mt-24">
        <h2 className="text-3xl">Estimate a month</h2>
        <p className="mt-2 mb-10 text-sm text-muted-foreground">
          Defaults are illustrative. Measured values are on the Results page: about 50% of input
          kept, and 20 to 53% of cost saved by routing depending on language.
        </p>
        <Estimator />
      </section>

      <div className="mt-20 overflow-x-auto">
        <table className="w-full min-w-[420px] text-sm">
          <thead>
            <tr className="text-left font-mono text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
              <th className="pb-3 font-normal">Model</th>
              <th className="pb-3 font-normal">Input / 1M tokens</th>
              <th className="pb-3 font-normal">Output / 1M tokens</th>
            </tr>
          </thead>
          <tbody className="font-mono text-[13px]">
            {(["cheap", "premium"] as const).map((t) => (
              <tr key={t} className="border-t border-border/60">
                <td className="py-3">{TIERS[t].model}</td>
                <td className="py-3">${TIERS[t].input.toFixed(3)}</td>
                <td className="py-3">${TIERS[t].output.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 font-mono text-[11px] text-muted-foreground">
          Groq list prices, accessed {PRICING_DATE}.
        </p>
      </div>
    </Page>
  );
}
