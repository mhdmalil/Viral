import { toggleVibe, VIBE_OPTIONS } from "../lib/vibes";

type Props = {
  value: string[];
  onChange: (next: string[]) => void;
  label: string;
  hint: string;
};

export function VibeChips({ value, onChange, label, hint }: Props) {
  return (
    <div className="vibe-chips" role="group" aria-label={label}>
      <p className="vibe-chips-hint">{hint}</p>
      <div className="vibe-chip-row">
        {VIBE_OPTIONS.map((id) => {
          const on = value.includes(id);
          return (
            <button
              key={id}
              type="button"
              className={on ? "vibe-chip on" : "vibe-chip"}
              aria-pressed={on}
              onClick={() => onChange(toggleVibe(value, id))}
            >
              {id}
            </button>
          );
        })}
      </div>
    </div>
  );
}
