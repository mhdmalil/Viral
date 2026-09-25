import { useEffect, useState } from "react";
import { ApiMonitor } from "../components/ApiMonitor";
import { api } from "../services/api";
import type { UsageReport } from "../types/api";

export function UsagePage() {
  const [data, setData] = useState<UsageReport | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    function refresh() {
      api
        .usage({ provider: selected || undefined })
        .then((payload) => {
          if (alive) setData(payload);
        })
        .catch((err: Error) => {
          if (alive) setError(err.message);
        });
    }
    refresh();
    const timer = window.setInterval(refresh, 2000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [selected]);

  async function resetUsage() {
    if (!window.confirm("Clear all API usage history?")) return;
    setError(null);
    try {
      await api.resetUsage();
      setData(await api.usage({ provider: selected || undefined }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reset usage");
    }
  }

  return (
    <section className="usage-page">
      <div className="page-head">
        <h1>API</h1>
      </div>
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}
      {data ? (
        <ApiMonitor data={data} variant="full" selected={selected} onSelect={setSelected} onReset={() => void resetUsage()} />
      ) : (
        <p className="empty">Loading usage…</p>
      )}
    </section>
  );
}
