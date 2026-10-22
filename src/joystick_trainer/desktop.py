"""Desktop icons for people who don't use a terminal. Every file written here is recorded in
.install-state, so scripts/uninstall-pi.sh removes it again."""

import os
import subprocess
from pathlib import Path

ICONS = {
    "joystick-trainer-fortsetzen": ("Einrichtung fortsetzen", "Assistent: macht da weiter, wo du aufgehört hast",
                                    "scripts/assistent.sh"),
    "joystick-trainer-starten": ("Joystick-Trainer starten", "Startet das Senden (und die Kanalanzeige)",
                                 "scripts/start.sh"),
    "joystick-trainer-kalibrieren": ("Joystick kalibrieren", "Joystick neu einlernen und prüfen",
                                     "scripts/assistent.sh --kalibrieren"),
    "joystick-trainer-diagnose": ("Diagnose-Bericht", "Erstellt eine Textdatei für die Fehlersuche",
                                  ".venv/bin/joystick-trainer-diagnose"),
}


def desktop_dir():
    try:
        path = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:
        path = ""
    return Path(path) if path and path != str(Path.home()) else Path.home() / "Desktop"


def record(repo, line):
    state = repo / ".install-state"
    lines = state.read_text().splitlines() if state.exists() else []
    if line not in lines:
        with open(state, "a") as handle:
            handle.write(line + "\n")


def entry(repo, name, comment, command):
    program, *arguments = command.split()
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        f"Name={name}",
        f"Comment={comment}",
        f"Exec={repo / 'scripts/keep-open.sh'} {repo / program}{''.join(' ' + a for a in arguments)}",
        "Icon=input-gaming",
        "Terminal=true",
        "",
    ])


def install(repo, keys, target=None):
    target = target or desktop_dir()
    if not target.exists():
        target.mkdir(parents=True)
        record(repo, f"dir={target}")
    names = []
    for key in keys:
        name, comment, command = ICONS[key]
        path = target / f"{key}.desktop"
        path.write_text(entry(repo, name, comment, command))
        os.chmod(path, 0o755)
        record(repo, f"file={path}")
        names.append(name)
    return names


def install_resume_icon(repo, target=None):
    return install(repo, ["joystick-trainer-fortsetzen"], target)


def install_icons(repo, target=None):
    return install(repo, list(ICONS), target)
