"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Row = { name: string; count?: number; pct?: number };

export function SimpleBarChart({
  data,
  valueKey = "count",
  height = 280,
}: {
  data: Row[];
  valueKey?: "count" | "pct";
  height?: number;
}) {
  if (!data?.length) {
    return (
      <p className="text-sm text-ink/50 py-8 text-center">No data available yet.</p>
    );
  }
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 48 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#d9cfc0" />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fill: "#3d3429" }}
            interval={0}
            angle={-35}
            textAnchor="end"
            height={70}
          />
          <YAxis tick={{ fontSize: 11, fill: "#3d3429" }} />
          <Tooltip
            contentStyle={{
              background: "#f7f1e8",
              border: "1px solid #c4a882",
              borderRadius: 8,
            }}
          />
          <Bar dataKey={valueKey} fill="#8b3a2b" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-cedar/15 bg-cream/80 px-4 py-5 shadow-sm">
      <div className="text-xs uppercase tracking-wide text-ink/50">{label}</div>
      <div className="mt-1 font-display text-3xl text-cedar">{value}</div>
    </div>
  );
}

export function Panel({
  title,
  children,
  subtitle,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-cedar/15 bg-cream/70 p-5 shadow-sm">
      <h2 className="font-display text-xl text-ink">{title}</h2>
      {subtitle ? <p className="mt-1 text-sm text-ink/55">{subtitle}</p> : null}
      <div className="mt-4">{children}</div>
    </section>
  );
}
