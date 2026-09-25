export function formatScore(score: number | null): string {
  if (score == null || Number.isNaN(score)) return "—";
  const outOf100 = score <= 1 ? score * 100 : score;
  return `${Math.round(outOf100)}`;
}

export function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function formatSourceRange(start: number | null, end: number | null): string | null {
  if (start == null || end == null) return null;
  return `${formatDuration(start)}–${formatDuration(end)}`;
}

export function formatLogTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const day = date.getDate();
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const hh = date.getHours().toString().padStart(2, "0");
  const mm = date.getMinutes().toString().padStart(2, "0");
  return `${day} ${months[date.getMonth()]} ${hh}:${mm}`;
}
