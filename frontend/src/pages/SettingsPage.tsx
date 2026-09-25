import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { AppSettings } from "../types/api";

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.settings().then(setSettings).catch((err: Error) => setError(err.message));
  }, []);

  return (
    <section>
      <h1>Settings</h1>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {settings ? (
        <dl className="panel">
          <div>
            <dt>API</dt>
            <dd>
              {settings.host} · loopback {settings.bind_is_loopback ? "yes" : "no"}
            </dd>
          </div>
          <div>
            <dt>Whisper</dt>
            <dd>
              {settings.whisper_model} · {settings.whisper_device}
            </dd>
          </div>
          <div>
            <dt>Models</dt>
            <dd>
              Groq {settings.groq_configured ? "on" : "off"} · Gemini {settings.gemini_configured ? "on" : "off"} ·
              OpenRouter {settings.openrouter_configured ? "on" : "off"}
            </dd>
          </div>
        </dl>
      ) : (
        <p>Loading…</p>
      )}
    </section>
  );
}
