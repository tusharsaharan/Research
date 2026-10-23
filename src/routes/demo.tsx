import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useRef, useState, type ReactNode } from "react";
import { Page } from "../components/site/SiteChrome";
import {
  chatCompletion,
  compressText,
  streamChatCompletion,
  type CompressResponse,
  type GatewayMeta,
} from "../lib/gateway";
import { formatUsd } from "../lib/pricing";

export const Route = createFileRoute("/demo")({
  head: () => ({
    meta: [
      { title: "Gateway — Code-Mixed Gateway" },
      {
        name: "description",
        content:
          "Send a prompt through the gateway and see the compressed prompt, the routing decision and the cost of the call.",
      },
    ],
  }),
  component: DemoPage,
});

const PRESETS = [
  {
    label: "Support",
    text: "yaar mera hostel ka wifi slow hai, complaint kahan karun? kal se assignment submit karna hai",
  },
  {
    label: "Arithmetic",
    text: "arre yaar 15*8+22 ka answer kya hoga? exam me aaya tha, jaldi batao na",
  },
  {
    label: "Filler words",
    text: "hello sir, yaar matlab basically mera phone charge nahi ho raha hai, actually dekho na help chahiye tha please",
  },
  {
    label: "Protected spans",
    text: "yaar matlab mera email user@example.com par bhejo na, aur amount Rs. 2,500 ka check karo",
  },
] as const;

// Model output is markdown; the page shows plain text without emoji or bold markers.
function cleanAnswer(text: string): string {
  return text.replace(/[\p{Extended_Pictographic}\u{FE0F}\u{20E3}]/gu, "").replace(/\*\*/g, "");
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border/60 py-2.5 last:border-b-0">
      <dt className="text-sm text-muted-foreground">{k}</dt>
      <dd className="font-mono text-sm text-foreground">{v}</dd>
    </div>
  );
}

function Panel({ n, title, children }: { n: string; title: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <p className="font-mono text-xs text-primary">{n}</p>
      <h2 className="mt-2 text-2xl">{title}</h2>
      <div className="mt-5">{children}</div>
    </div>
  );
}

function DemoPage() {
  const [input, setInput] = useState<string>(PRESETS[0].text);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comp, setComp] = useState<CompressResponse | null>(null);
  const [meta, setMeta] = useState<GatewayMeta | null>(null);
  const [answer, setAnswer] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async () => {
    const text = input.trim();
    if (!text) {
      setError("Enter a prompt first.");
      return;
    }
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setLoading(true);
    setError(null);
    setComp(null);
    setMeta(null);
    setAnswer("");

    try {
      const c = await compressText(text, "auto");
      if (ac.signal.aborted) return;
      setComp(c);

      let full = "";
      let gotMeta = false;
      for await (const chunk of streamChatCompletion(text)) {
        if (ac.signal.aborted) return;
        if (chunk.meta) {
          gotMeta = true;
          setMeta(chunk.meta);
        }
        if (chunk.content) {
          full += chunk.content;
          setAnswer(full);
        }
      }
      if (!gotMeta) {
        const res = await chatCompletion(text);
        if (ac.signal.aborted) return;
        setAnswer(res.choices[0]?.message.content ?? full);
        if (res.x_gateway) setMeta(res.x_gateway);
      }
    } catch (e) {
      if ((e as Error)?.name === "AbortError") return;
      setError(
        e instanceof Error
          ? `${e.message}. Is the gateway running on port 8000?`
          : "The gateway did not respond.",
      );
    } finally {
      if (!ac.signal.aborted) setLoading(false);
    }
  }, [input]);

  const origTokens = meta?.original_tokens ?? comp?.token_original;
  const compTokens = meta?.compressed_tokens ?? comp?.token_compressed;
  const compressed = meta?.compressed_prompt ?? comp?.compressed;
  const saved =
    origTokens && compTokens != null ? Math.round((1 - compTokens / origTokens) * 100) : null;

  return (
    <Page
      eyebrow="Gateway"
      title="Send a prompt through it"
      lede="The prompt is compressed, scored, routed to one of two models and priced. Each step is shown below."
    >
      <div className="rounded-xl border border-border bg-card">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={4}
          maxLength={4000}
          aria-label="Prompt"
          className="block w-full resize-y rounded-t-xl bg-transparent px-6 py-5 text-[15px] leading-relaxed outline-none placeholder:text-muted-foreground"
          placeholder="Type a question in English, Hindi or a mix of both"
        />
        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-border px-6 py-4">
          <div className="flex flex-wrap gap-x-5 gap-y-2">
            {PRESETS.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => setInput(p.text)}
                className={`text-sm transition-colors hover:text-foreground ${input === p.text ? "text-foreground" : "text-muted-foreground"}`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={run}
            disabled={loading}
            className="rounded-full bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {loading ? "Running" : "Run"}
          </button>
        </div>
      </div>

      {error ? (
        <p className="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <div className="mt-10 grid gap-5 lg:grid-cols-3">
        <Panel n="01" title="Compress">
          {compressed != null ? (
            <>
              <p className="rounded-lg bg-secondary/50 px-4 py-3 text-sm leading-relaxed">
                {compressed}
              </p>
              <dl className="mt-4">
                <Row k="Tokens in" v={String(origTokens)} />
                <Row k="Tokens out" v={String(compTokens)} />
                <Row k="Removed" v={saved != null ? `${saved}%` : "-"} />
              </dl>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">The compressed prompt appears here.</p>
          )}
        </Panel>

        <Panel n="02" title="Route">
          {meta ? (
            <>
              <p className="text-sm">
                Sent to <span className="font-mono">{meta.model_routed}</span>
                <span className="text-muted-foreground"> ({meta.tier} tier)</span>
              </p>
              <dl className="mt-4">
                <Row k="Difficulty score" v={meta.difficulty_score.toFixed(3)} />
                <Row k="Threshold" v={meta.conformal_threshold.toFixed(3)} />
                <Row k="Error budget" v={`${(meta.error_bound * 100).toFixed(0)}%`} />
              </dl>
              <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
                Scores above the threshold go to the large model.
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">The routing decision appears here.</p>
          )}
        </Panel>

        <Panel n="03" title="Price">
          {meta ? (
            <>
              <p className="font-serif text-4xl">{formatUsd(meta.estimated_cost_usd)}</p>
              <p className="mt-1 text-sm text-muted-foreground">this call</p>
              <dl className="mt-4">
                <Row
                  k="Saved vs. full prompt on large model"
                  v={formatUsd(meta.estimated_cost_savings_usd)}
                />
                <Row k="Cost per 10,000 calls" v={formatUsd(meta.estimated_cost_usd * 10_000)} />
                <Row
                  k="Saved per 10,000 calls"
                  v={formatUsd(meta.estimated_cost_savings_usd * 10_000)}
                />
              </dl>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">The cost of the call appears here.</p>
          )}
        </Panel>
      </div>

      {answer ? (
        <section className="mt-10">
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
            Answer
          </p>
          <p className="mt-3 max-w-3xl whitespace-pre-wrap text-[15px] leading-relaxed">
            {cleanAnswer(answer)}
          </p>
        </section>
      ) : null}
    </Page>
  );
}
