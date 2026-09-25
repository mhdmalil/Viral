# Design System

Specified target for the desktop UI (Phase 1 implements a first pass). Tokens live in `frontend/src/styles/tokens.css` once the frontend exists.

## Design Tokens
### Color
| Token | Value | Used for |
|---|---|---|
| `--bg` | `#121212` | App background |
| `--bg-elevated` | `#2a2a2a` | Sidebar, cards |
| `--border` | `#4a4a4a` | Dividers |
| `--text` | `#f5f5f5` | Primary text |
| `--text-muted` | `#b8b8b8` | Secondary |
| `--accent` | `#ececec` | Primary actions |
| `--danger` | `#d08989` | Destructive |
| `--ok` | `#7dba7d` | Active API lane |
| `--focus` | `#d4d4d4` | Keyboard focus |

### Typography
| Token | Font / size / weight / line-height | Used for |
|---|---|---|
| UI sans | system-ui, Segoe UI, sans-serif | All UI |
| `--text-sm` | 13px / 1.4 | Meta, nav |
| `--text-md` | 15px / 1.45 | Body |
| `--text-lg` | 20px / 1.3 / 600 | Page titles |

### Spacing Scale
| Token | Value |
|---|---|
| `--s-1` | 4px |
| `--s-2` | 8px |
| `--s-3` | 12px |
| `--s-4` | 16px |
| `--s-5` | 24px |
| `--s-6` | 32px |

### Breakpoints
| Name | Width |
|---|---|
| compact | 768px (sidebar stacks above content) |
| desktop | 1280px |

### Radii / Shadows / Borders
- Radius 8px on cards/buttons. Hairline borders, no heavy drop shadows.

## Core Components
| Component | Location | Variants | Notes |
|---|---|---|---|
| AppLayout | `frontend/src/layouts/AppLayout.tsx` | collapsible sidebar | No Favorites/Trash |
| Clip cards | `ProjectDetailPage` | selectable square previews + stacked meta | Bulk download/delete |
| Job status | `ProjectDetailPage` | single loader | No step list while generating |
| Source import | `ProjectDetailPage` | empty dropzone; Replace next to Delete when a video exists | Compact after first import |
| Caption setup | `ProjectDetailPage` options bar | clips / captions / style / vibe chips / Socials or Picture | Multi-select vibes; none = all |
| Projects grid | `ProjectsPage` | cards side by side | |
| Library | `LibraryPage` | filter bar + vibe chips + clip rows | Same chips filter existing clips |
| API monitor | `UsagePage` / `ApiMonitor` | full, dashboard logs, project dock | Providers/models from recorded usage |

## Motion Language
- Generate uses three bouncing dots (`LoaderDots`). Reduced motion: opacity pulse only; other UI still has no animation.
- Hover is color-only.

## Imagery & Iconography
- Large thumbnails later. Phase 1: text + simple SVG icons, one style.

## States Covered
- Empty states on list pages. Focus rings on controls. Loading on submit.

## Anti-Patterns Observed
- None yet (new UI).
