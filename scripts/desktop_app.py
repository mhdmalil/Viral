"""Start ViralClipper as a desktop window (Edge app mode) on 127.0.0.1:8000."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UVICORN = ROOT / "backend" / ".venv" / "Scripts" / "uvicorn.exe"
DIST_INDEX = ROOT / "frontend" / "dist" / "index.html"
HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}/"
CUT = "8s-hook-down"


def _popup(title: str, text: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)
    except Exception:
        print(text, file=sys.stderr)


def _listening() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.4):
            return True
    except OSError:
        return False


def _cut_ok() -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=1.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status == 200 and payload.get("cut") == CUT
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
        return False


def _healthy() -> bool:
    return _cut_ok()


def _edge() -> Path | None:
    roots = [
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
        os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        os.environ.get("LOCALAPPDATA", ""),
    ]
    names = [
        Path("Microsoft") / "Edge" / "Application" / "msedge.exe",
        Path("Microsoft") / "Edge Beta" / "Application" / "msedge.exe",
    ]
    for root in roots:
        if not root:
            continue
        for name in names:
            candidate = Path(root) / name
            if candidate.is_file():
                return candidate
    return None


def _ensure_ui() -> None:
    if DIST_INDEX.is_file():
        return
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        _popup("ViralClipper", "UI build is missing. Install Node, then run npm run build in frontend.")
        sys.exit(1)
    try:
        subprocess.check_call([npm, "run", "build"], cwd=str(ROOT / "frontend"))
    except subprocess.CalledProcessError:
        _popup("ViralClipper", "Could not build the UI. Run npm run build in frontend.")
        sys.exit(1)
    if not DIST_INDEX.is_file():
        _popup("ViralClipper", "UI build is missing after npm run build.")
        sys.exit(1)


def _listener_pids() -> list[int]:
    created = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"],
        capture_output=True,
        text=True,
        check=False,
    )
    pids: list[int] = []
    for line in created.stdout.splitlines():
        compact = " ".join(line.split())
        if "LISTENING" not in compact.upper():
            continue
        if f":{PORT} " not in compact and not compact.endswith(f":{PORT}"):
            continue
        if "127.0.0.1" not in compact and "0.0.0.0" not in compact:
            continue
        try:
            pid = int(compact.split()[-1])
        except ValueError:
            continue
        if pid > 4:
            pids.append(pid)
    return list(dict.fromkeys(pids))


def _stop_listeners() -> None:
    for pid in _listener_pids():
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
    deadline = time.monotonic() + 10.0
    while _listening() and time.monotonic() < deadline:
        time.sleep(0.2)
        for pid in _listener_pids():
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)


def _start_api() -> subprocess.Popen[bytes]:
    if not UVICORN.is_file():
        _popup("ViralClipper", "App venv is missing. Run backend\\.venv setup first.")
        sys.exit(1)
    _ensure_ui()
    return subprocess.Popen(
        [str(UVICORN), "app.main:app", "--app-dir", "backend", "--host", HOST, "--port", str(PORT)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_ready(timeout: float = 25.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _healthy():
            return True
        time.sleep(0.2)
    return False


def _open_window() -> subprocess.Popen[bytes] | None:
    edge = _edge()
    profile = ROOT / "data" / "desktop-profile"
    profile.mkdir(parents=True, exist_ok=True)
    if edge is None:
        os.startfile(URL)  # noqa: S606 — local loopback only
        return None
    return subprocess.Popen(
        [
            str(edge),
            f"--app={URL}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
    )


def desktop_dir() -> Path:
    for candidate in (
        Path.home() / "Desktop",
        Path.home() / "OneDrive" / "Desktop",
        Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop",
    ):
        if candidate.is_dir():
            return candidate
    return Path.home() / "Desktop"


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def ensure_shortcut() -> None:
    pythonw = ROOT / "backend" / ".venv" / "Scripts" / "pythonw.exe"
    if not pythonw.is_file():
        return
    link = desktop_dir() / "ViralClipper.lnk"
    script = ROOT / "scripts" / "desktop_app.py"
    ps = f"""
$s = New-Object -ComObject WScript.Shell
$l = $s.CreateShortcut({_ps_quote(str(link))})
$l.TargetPath = {_ps_quote(str(pythonw))}
$l.Arguments = {_ps_quote('"' + str(script) + '"')}
$l.WorkingDirectory = {_ps_quote(str(ROOT))}
$l.WindowStyle = 7
$l.Description = 'ViralClipper'
$l.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    ensure_shortcut()
    # Closing Edge leaves uvicorn running. Restart so Generate always uses current code.
    _stop_listeners()
    owned = _start_api()
    if not _wait_ready():
        if owned.poll() is None:
            owned.terminate()
        _popup("ViralClipper", "Could not start the local API on port 8000.")
        sys.exit(1)

    _open_window()
    owned.wait()


if __name__ == "__main__":
    main()
