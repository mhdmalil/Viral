export const VIBE_OPTIONS = [
  "funny",
  "sad",
  "viral",
  "shocking",
  "awkward",
  "wholesome",
  "angry",
  "debate",
  "cringe",
  "informative",
  "financial",
  "lifestyle",
] as const;

export type VibeId = (typeof VIBE_OPTIONS)[number];

export function toggleVibe(current: string[], id: string): string[] {
  return current.includes(id) ? current.filter((item) => item !== id) : [...current, id];
}

export function clipVibes(clip: { vibe?: string | null; vibes?: string[] }): string[] {
  if (clip.vibes && clip.vibes.length) return clip.vibes;
  return clip.vibe ? [clip.vibe] : [];
}
