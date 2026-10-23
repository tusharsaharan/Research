import { Link } from "@tanstack/react-router";
import { useState, type ReactNode } from "react";

const NAV = [
  { to: "/", label: "Overview" },
  { to: "/demo", label: "Gateway" },
  { to: "/cost", label: "Cost" },
  { to: "/results", label: "Results" },
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur-sm">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link to="/" className="font-serif text-xl tracking-tight" onClick={() => setOpen(false)}>
          Code-Mixed Gateway
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              activeOptions={{ exact: item.to === "/" }}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground data-[status=active]:text-foreground"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <button
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="text-sm text-muted-foreground md:hidden"
        >
          {open ? "Close" : "Menu"}
        </button>
      </div>

      {open ? (
        <nav className="border-t border-border/70 px-6 py-3 md:hidden">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setOpen(false)}
              className="block py-2.5 text-sm text-muted-foreground hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-28 border-t border-border/70">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-6 py-10 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <p>Prompt compression and calibrated routing for Hindi–English text.</p>
        <p className="font-mono text-xs">Prices: Groq list, 2026-09-26</p>
      </div>
    </footer>
  );
}

export function Page({
  eyebrow,
  title,
  lede,
  children,
}: {
  eyebrow: string;
  title: string;
  lede: string;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto max-w-5xl px-6 pt-16 sm:pt-20">
      <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">{eyebrow}</p>
      <h1 className="mt-4 max-w-3xl text-4xl leading-[1.08] sm:text-5xl">{title}</h1>
      <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted-foreground">{lede}</p>
      <div className="mt-14">{children}</div>
    </main>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-border bg-card p-6 ${className}`}>{children}</div>
  );
}

export function SectionHeading({ kicker, title }: { kicker?: string; title: string }) {
  return (
    <div className="mb-8">
      {kicker ? (
        <p className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
          {kicker}
        </p>
      ) : null}
      <h2 className="mt-2 text-3xl">{title}</h2>
    </div>
  );
}

export function DataTable({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card">
      <table className="w-full min-w-[560px] border-collapse text-sm">
        <thead>
          <tr>
            {head.map((h) => (
              <th
                key={h}
                className="border-b border-border px-5 py-3 text-left font-mono text-[11px] font-normal uppercase tracking-[0.1em] text-muted-foreground"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="align-top">
              {row.map((cell, j) => (
                <td
                  key={j}
                  className={`border-b border-border/60 px-5 py-3.5 ${
                    j === 0 ? "text-foreground" : "font-mono text-[13px] text-muted-foreground"
                  }`}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Source({ children }: { children: ReactNode }) {
  return <p className="mt-3 font-mono text-[11px] text-muted-foreground">Source: {children}</p>;
}
