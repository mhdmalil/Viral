from pathlib import Path
from uuid import uuid4
import re

from app.core.config import MEDIA_DIR, settings
from app.models.entities import Project

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def projects_root() -> Path:
    return Path(settings.projects_dir)


def project_tree(project: Project) -> Path:
    if project.folder_path:
        return Path(project.folder_path)
    return MEDIA_DIR / "accounts" / str(project.account_id) / "projects" / str(project.id)


def ensure_project_folder(project: Project) -> Path:
    if project.folder_path:
        root = Path(project.folder_path)
        for sub in ("source", "clips", "thumbnails", "analysis", "downloads", "branding"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        return root
    name = safe_filename(project.name)[:48]
    root = projects_root() / f"{project.id:04d}_{name}"
    if root.exists():
        root = projects_root() / f"{project.id:04d}_{name}_{uuid4().hex[:6]}"
    for sub in ("source", "clips", "thumbnails", "analysis", "downloads", "branding"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    project.folder_path = str(root)
    return root


def project_original_dir(project: Project) -> Path:
    return project_tree(project) / "source"


def project_analysis_dir(project: Project) -> Path:
    return project_tree(project) / "analysis"


def project_branding_dir(project: Project) -> Path:
    folder = project_tree(project) / "branding"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def project_clips_dir(project: Project) -> Path:
    return project_tree(project) / "clips"


def project_thumb_dir(project: Project) -> Path:
    return project_tree(project) / "thumbnails"


def project_downloads_dir(project: Project) -> Path:
    return project_tree(project) / "downloads"


def library_root() -> Path:
    root = projects_root() / "library"
    (root / "clips").mkdir(parents=True, exist_ok=True)
    return root


def library_clips_dir() -> Path:
    folder = library_root() / "clips"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def safe_filename(name: str) -> str:
    cleaned = _SAFE.sub("_", Path(name).name).strip("._")
    return cleaned or "video"


_WIN_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clip_file_stem(title: str, clip_id: int, index: int | None = None) -> str:
    raw = _WIN_BAD.sub("", str(title or "")).replace("\n", " ")
    raw = re.sub(r"\s+", " ", raw).strip(" .")
    raw = raw[:80].rstrip(" .")
    base = raw or f"clip_{clip_id:04d}"
    if index is None:
        return base
    return f"{max(1, int(index)):02d} - {base}"


def unique_clip_path(folder: Path, stem: str, clip_id: int, suffix: str = ".mp4") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{stem}_{clip_id}{suffix}"


def media_url(path: Path | str | None) -> str | None:
    if path is None:
        return None
    resolved = Path(path).resolve()
    roots = (
        (projects_root().resolve(), "/files/"),
        (MEDIA_DIR.resolve(), "/media/"),
    )
    for root, prefix in roots:
        try:
            relative = resolved.relative_to(root)
        except ValueError:
            continue
        return prefix + relative.as_posix()
    return None
