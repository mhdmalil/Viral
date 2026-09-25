import { useState } from "react";
import { Link } from "react-router-dom";
import { formatLogTime } from "../lib/format";
import type { UsageLog, UsageReport } from "../types/api";

function outcomeLabel(outcome: string): string {
  if (outcome === "ok") return "ok";
  if (outcome === "429") return "limited";
  if (outcome === "calling") return "calling";
  return outcome;
}

function LiveLine({ data, projectId }: { data: UsageReport; projectId?: number }) {
  const live = data.live;
  const mine = projectId == null || live.project_id == null || live.project_id === projectId;
  if (mine && live.provider && live.model) {
    const prefix = live.outcome === "calling" ? "Now" : "Last";
    return (
      <p className="usage-live">
        {prefix} <strong>{live.provider}</strong> · {live.model}
        {live.project_name ? ` · ${live.project_name}` : ""}
      </p>
    );
  }
  return <p className="usage-live idle">No API call in flight</p>;
}

function formatTick(row: UsageReport["series"][number]): string {
  if (row.at) {
    const date = new Date(row.at);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
    }
  }
  return row.label;
}

function Chart({ series }: { series: UsageReport["series"] }) {
  if (series.length === 0) {
    return <p className="empty">No requests in the last hour.</p>;
  }
  const width = 1000;
  const height = 220;
  const padX = 2;
  const padY = 10;
  const max = Math.max(1, ...series.map((row) => row.requests));
  const last = Math.max(1, series.length - 1);
  const points = series.map((row, index) => {
    const x = padX + (index / last) * (width - padX * 2);
    const y = height - padY - (row.requests / max) * (height - padY * 2);
    return { x, y, label: formatTick(row), requests: row.requests };
  });
  const line = points.map((point) => `${point.x},${point.y}`).join(" ");
  const area = `${padX},${height - padY} ${line} ${width - padX},${height - padY}`;
  const ticks = points.filter((_, index) => index % 10 === 0 || index === points.length - 1);
  return (
    <div className="usage-chart-wrap">
      <svg className="usage-line" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label="Requests over the last hour">
        <polyline fill="currentColor" fillOpacity="0.08" stroke="none" points={area} />
        <polyline fill="none" stroke="currentColor" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" points={line} />
      </svg>
      <div className="usage-line-axis">
        {ticks.map((tick) => (
          <span key={`${tick.label}-${tick.x}`} style={{ left: `${(tick.x / width) * 100}%` }}>
            {tick.label}
          </span>
        ))}
      </div>
    </div>
  );
}

const WATCH_PROVIDERS = ["groq", "gemini", "openrouter"] as const;

function ProviderLanes({ data, projectId }: { data: UsageReport; projectId?: number }) {
  const live = data.live;
  const mine = projectId == null || live.project_id == null || live.project_id === projectId;
  const byName = new Map(data.providers.map((row) => [row.provider.toLowerCase(), row]));
  return (
    <ul className="api-lanes">
      {WATCH_PROVIDERS.map((name) => {
        const row = byName.get(name);
        const active = Boolean(mine && live.job_id && (live.provider || "").toLowerCase() === name);
        const model = active ? live.model : row?.last_model;
        return (
          <li key={name} className={active ? "api-lane on" : "api-lane"} aria-current={active ? "true" : undefined}>
            <strong>{name}</strong>
            <span className="api-lane-model">{model || "—"}</span>
            <span className="meta">{row ? `${row.requests} req` : "0 req"}</span>
          </li>
        );
      })}
    </ul>
  );
}

function Logs({ rows }: { rows: UsageLog[] }) {
  if (rows.length === 0) {
    return <p className="empty">No API calls recorded yet. They appear when Generate talks to Groq, Gemini, or OpenRouter.</p>;
  }
  return (
    <ul className="usage-log">
      {rows.map((row) => (
        <li key={row.id}>
          <time dateTime={row.created_at}>{formatLogTime(row.created_at)}</time>
          <span className="usage-log-api">{row.provider}</span>
          <span className="usage-log-model">{row.model}</span>
          <span className={`usage-pill ${row.outcome}`}>{outcomeLabel(row.outcome)}</span>
          <span className="meta">{row.latency_ms}ms</span>
          {row.limit != null ? (
            <span className="meta">
              {row.remaining ?? "—"}/{row.limit}
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function ResetButton({ onReset }: { onReset?: () => void }) {
  if (!onReset) return null;
  return (
    <button type="button" className="btn-quiet" onClick={onReset}>
      Reset
    </button>
  );
}

function LogCard({ rows }: { rows: UsageLog[] }) {
  const [open, setOpen] = useState(false);
  return (
    <article className="card">
      <div className="usage-card-head">
        <h2>Log</h2>
        <button type="button" className="btn-quiet" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
          {open ? "Minimize" : `Expand (${rows.length})`}
        </button>
      </div>
      {open ? <Logs rows={rows} /> : <p className="meta">{rows.length === 0 ? "No entries." : `${rows.length} entries hidden`}</p>}
    </article>
  );
}

export function ApiMonitor({
  data,
  variant,
  selected,
  onSelect,
  onReset,
  projectId,
}: {
  data: UsageReport;
  variant: "full" | "dock" | "logs";
  selected?: string | null;
  onSelect?: (provider: string | null) => void;
  onReset?: () => void;
  projectId?: number;
}) {
  if (variant === "logs") {
    return (
      <article className="card activity-card">
        <div className="usage-card-head">
          <h2>API</h2>
          <Link className="btn-quiet" to="/usage">
            Monitor
          </Link>
        </div>
        <LiveLine data={data} />
        <Logs rows={data.logs.slice(0, 8)} />
      </article>
    );
  }

  if (variant === "dock") {
    return (
      <aside className="api-dock" aria-label="API usage">
        <div className="usage-card-head">
          <p className="meta">
            {data.totals.requests} req · {data.totals.limited} limited · {data.totals.avg_ms}ms
          </p>
          <ResetButton onReset={onReset} />
        </div>
        <ProviderLanes data={data} projectId={projectId} />
        <Link to="/usage">Open full monitor</Link>
      </aside>
    );
  }

  return (
    <div className="usage-full">
      <div className="usage-card-head">
        <LiveLine data={data} />
        <ResetButton onReset={onReset} />
      </div>
      <div className="stats-row usage-stats">
        <article className="card stat-card">
          <p>Requests</p>
          <strong>{data.totals.requests}</strong>
        </article>
        <article className="card stat-card">
          <p>OK</p>
          <strong>{data.totals.ok}</strong>
        </article>
        <article className="card stat-card">
          <p>Limited</p>
          <strong>{data.totals.limited}</strong>
        </article>
        <article className="card stat-card">
          <p>Avg ms</p>
          <strong>{data.totals.avg_ms}</strong>
        </article>
      </div>
      <div className="usage-providers" role="tablist" aria-label="API filter">
        <button type="button" className={!selected ? "usage-provider on" : "usage-provider"} onClick={() => onSelect?.(null)}>
          All APIs
        </button>
        {WATCH_PROVIDERS.map((name) => (
          <button
            key={name}
            type="button"
            className={selected === name ? "usage-provider on" : "usage-provider"}
            onClick={() => onSelect?.(name)}
          >
            {name}
          </button>
        ))}
      </div>
      <article className="card usage-chart-card">
        <h2>Requests (1h)</h2>
        <Chart series={data.series} />
      </article>
      <article className="card">
        <h2>Models</h2>
        {data.models.length === 0 ? (
          <p className="empty">No models yet.</p>
        ) : (
          <ul className="usage-models">
            {data.models.map((row) => (
              <li key={`${row.provider}-${row.model}`}>
                <span>
                  {row.provider} · {row.model}
                </span>
                <span>
                  {row.requests} req · {row.ok} ok · {row.limited} limited · {row.avg_ms}ms
                </span>
              </li>
            ))}
          </ul>
        )}
      </article>
      <LogCard rows={data.logs} />
    </div>
  );
}
