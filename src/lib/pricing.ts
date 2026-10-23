// Mirrors backend/src/gateway/pricing.py (Groq list prices, USD per 1M tokens).
export const PRICING_DATE = "2026-09-26";

export const TIERS = {
  cheap: { model: "gpt-oss-20b", input: 0.075, output: 0.3 },
  premium: { model: "gpt-oss-120b", input: 0.15, output: 0.6 },
} as const;

export type Tier = keyof typeof TIERS;

export function callCostUsd(tier: Tier, inputTokens: number, outputTokens: number): number {
  const p = TIERS[tier];
  return (inputTokens * p.input + outputTokens * p.output) / 1_000_000;
}

export function formatUsd(v: number): string {
  if (v === 0) return "$0";
  if (v < 0.01) return `$${v.toFixed(6)}`;
  if (v < 100) return `$${v.toFixed(2)}`;
  return `$${Math.round(v).toLocaleString("en-US")}`;
}
