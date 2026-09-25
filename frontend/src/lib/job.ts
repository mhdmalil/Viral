const STATUS_LABEL: Record<string, string> = {
  QUEUED: "Queued",
  TRANSCRIBING: "Transcribing",
  ANALYZING: "Analyzing",
  DISCOVERING: "Analyzing",
  EXPANDING: "Expanding",
  VALIDATING: "Checking",
  SELECTING: "Selecting",
  REFINING: "Refining",
  RENDERING: "Clipping",
  GENERATING_CANDIDATES: "Clipping",
  SCORING: "Scoring",
  COMPLETED: "Done",
  FAILED: "Failed",
  CANCELLED: "Stopped",
};

export function shortJobLabel(status: string, stage?: string | null): string {
  const raw = (stage || "").trim();
  const cut = raw.match(/(\d+)\s*\/\s*(\d+)/);
  if (cut && /clip|cut/i.test(raw)) {
    return `Clipping ${cut[1]}/${cut[2]}`;
  }
  const mapped = STATUS_LABEL[status.toUpperCase()];
  if (mapped) return mapped;
  const msg = (stage || "").toLowerCase();
  if (msg.includes("transcrib")) return "Transcribing";
  if (msg.includes("cut") || msg.includes("render") || msg.includes("clip")) return "Clipping";
  if (msg.includes("discover") || msg.includes("analy") || msg.includes("scan")) return "Analyzing";
  if (msg.includes("stop")) return "Stopped";
  return "Working";
}
