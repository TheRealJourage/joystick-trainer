"""joystick-trainer-diagnose: one text file with what someone helping remotely needs to know. Holds no
passwords, network names or addresses: only the device, the software state and this project's files."""

import datetime
import subprocess
import sys
from pathlib import Path

from .desktop import desktop_dir

REPO = Path(__file__).resolve().parents[2]


def command(args, cwd=REPO):
    try:
        result = subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return f"({error})"
    return (result.stdout + result.stderr).strip() or "(keine Ausgabe)"


def read(path, tail=None):
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except OSError as error:
        return f"({error.strerror})"
    return "\n".join(lines[-tail:] if tail else lines)


def joysticks():
    try:
        from .calibrate import find_joysticks
    except ImportError as error:
        return f"({error})"
    found = find_joysticks()
    names = [f"{d.path}: {d.name}" for d in found]
    for device in found:
        device.close()
    return "\n".join(names) or "(keiner gefunden)"


def connectors():
    lines = []
    for status in sorted(Path("/sys/class/drm").glob("card*-*/status")):
        lines.append(f"{status.parent.name}: {status.read_text().strip()}")
    return "\n".join(lines) or "(keine)"


def sections(repo=REPO):
    python = str(repo / ".venv/bin/python")
    return [
        ("Zeit", datetime.datetime.now().isoformat(timespec="seconds")),
        ("Gerät", read("/proc/device-tree/model").strip("\0")),
        ("Betriebssystem", read("/etc/os-release", tail=None)),
        ("Kernel", command(["uname", "-r"])),
        ("Gruppen", command(["id", "-nG"])),
        ("Projektstand", command(["git", "log", "--oneline", "-3"], repo) + "\n" + command(["git", "status", "--short"], repo)),
        ("Python-Pakete", command([python, "-m", "pip", "list"], repo)),
        ("Joysticks", joysticks()),
        ("Bildschirm-Anschlüsse", connectors()),
        ("GPIO17", command(["pinctrl", "get", "17"])),
        ("Assistent: Fortschritt", read(repo / ".assistant-state")),
        ("Assistent: letzte Schritte", read(repo / ".assistant.log", tail=150)),
        ("config.yaml", read(repo / "config.yaml")),
        ("config.lgpio.yaml", read(repo / "config.lgpio.yaml")),
        ("Installationsprotokoll (.install-state)", read(repo / ".install-state")),
        ("Tests", command([python, "-m", "pytest", "-q"], repo).splitlines()[-1]),
        ("Dienst", command(["journalctl", "--user", "-u", "joystick-trainer", "-n", "30", "--no-pager"])),
    ]


def main(argv=None):
    target = desktop_dir()
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"joystick-trainer-diagnose-{datetime.datetime.now():%Y%m%d-%H%M}.txt"
    print("Erstelle den Diagnose-Bericht (dauert ein paar Sekunden) ...")
    with open(path, "w", encoding="utf-8") as handle:
        for title, body in sections():
            handle.write(f"##### {title} #####\n{body}\n\n")
    print(f"\nFertig: {path}")
    print("Diese Datei liegt auf dem Desktop. Schick sie per E-Mail oder USB-Stick an die Person, die dir hilft.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
