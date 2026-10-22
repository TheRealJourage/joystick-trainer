"""joystick-trainer-assistent: guides someone without Linux or radio knowledge through the whole setup,
in German. Each step says what to do, checks what software can check, and explains what failed.
Progress is kept in .assistant-state, so a reboot or a power-off for wiring loses nothing; the desktop
icon "Einrichtung fortsetzen" picks it up again."""

import argparse
import grp
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from . import calibrate, desktop
from .calibrate import Step

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / ".assistant-state"
LOG = REPO / ".assistant.log"
PIN, CHIP = 17, 0

ROLES = {1: "Querruder (rechts/links)", 2: "Höhenruder (vor/zurück)", 3: "Gas", 4: "Seitenruder (Drehen)",
         5: "Scharfschalten (Taste)"}

STEPS_DE = [
    Step("roll", 1, "stick", "Knüppel in die Mitte stellen und loslassen.", "Knüppel ganz nach RECHTS drücken und festhalten."),
    Step("pitch", 2, "stick", "Knüppel in die Mitte stellen und loslassen.", "Knüppel ganz nach VORNE (von dir weg) drücken und festhalten."),
    Step("throttle", 3, "throttle", "Gashebel ganz ZURÜCK ziehen.", "Gashebel ganz nach VORNE schieben und festhalten."),
    Step("yaw", 4, "stick", "Knüppel gerade stellen (nicht verdreht) und loslassen.", "Knüppel ganz nach RECHTS DREHEN und festhalten."),
    Step("arm", 5, "button", "Alle Tasten loslassen.", "Die Taste, mit der du scharfschalten willst, gedrückt HALTEN."),
]

# calibrate.Wizard speaks English; these turn its lines into German without touching that module.
TRANSLATIONS = [
    (r"\[Enter = ok, s = skip\]", "[Enter = weiter, s = überspringen]"),
    (r"^\n\[(\w+)\] -> channel (\d+)$", lambda m: f"\n--- {ROLES.get(int(m[2]), m[1])} -> Kanal {m[2]} ---"),
    (r"^  skipped$", "  übersprungen"),
    (r"^  ok: (\S+) \(inverted\), reach (\d+)%$", r"  erkannt: \1 (umgedreht), Ausschlag \2 %"),
    (r"^  ok: (\S+), reach (\d+)%$", r"  erkannt: \1, Ausschlag \2 %"),
    (r"^  ok: (\S+)$", r"  erkannt: \1"),
    (r"no axis moved enough - move it all the way and hold it there",
     "kein Hebel hat sich weit genug bewegt. Bis zum Anschlag bewegen und dort festhalten"),
    (r"two axes moved - move only this one control", "zwei Hebel haben sich bewegt. Nur diesen einen bewegen"),
    (r"expected exactly one newly pressed button, got (\d+)", r"es muss genau eine Taste gedrückt sein (erkannt: \1)"),
    (r"^  not recognised: (.*)\. Again\.$", r"  Nicht erkannt: \1. Noch einmal."),
    (r"rest position is (\d+)% off centre", r"Ruhestellung liegt \1 % neben der Mitte"),
    (r"held position reached only (\d+)% of the travel", r"es wurden nur \1 % des Weges erreicht"),
    (r"^  warning: (.*)$", r"  Hinweis: \1 (Kalibrierung ggf. wiederholen)"),
]


def translate(text):
    for pattern, replacement in TRANSLATIONS:
        text = re.sub(pattern, replacement, text)
    return text


class Abort(Exception):
    pass


class Ui:
    def __init__(self, ask=input, out=print, log=LOG):
        self._ask, self._out, self._log = ask, out, log

    def _write_log(self, text):
        if self._log:
            with open(self._log, "a", encoding="utf-8") as handle:
                handle.write(text + "\n")

    def say(self, text=""):
        text = translate(text)
        self._out(text)
        self._write_log(text)

    def ask(self, prompt):
        prompt = translate(prompt)
        try:
            answer = self._ask(prompt)
        except EOFError:
            raise Abort from None
        self._write_log(f"{prompt}> {answer}")
        return answer

    def enter(self, prompt="Weiter mit Enter."):
        self.ask(f"\n>>> {prompt} ")

    def yes(self, question):
        while True:
            answer = self.ask(f"\n>>> {question} [j/n] ").strip().lower()
            if answer in ("j", "ja", "y"):
                return True
            if answer in ("n", "nein"):
                return False
            self.say("Bitte j (ja) oder n (nein) eingeben.")

    def title(self, number, total, text):
        self.say("\n" + "=" * 70)
        self.say(f" Schritt {number} von {total}: {text}")
        self.say("=" * 70)


def load_state(path=STATE):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return {"done": []}


def save_state(state, path=STATE):
    path.write_text(json.dumps(state, indent=1))


# --- checks the software can do on its own ------------------------------------------------------

def pi_model():
    try:
        return Path("/proc/device-tree/model").read_text().strip("\0\n ")
    except OSError:
        return "unbekannt"


def input_group_state(user_groups=None):
    """'ok' = this session may read joysticks; 'reboot' = added to the group but not active yet; 'missing'."""
    try:
        group = grp.getgrnam("input")
    except KeyError:
        return "missing"
    active = os.getgroups() if user_groups is None else user_groups
    if group.gr_gid in active:
        return "ok"
    user = os.environ.get("USER", "")
    return "reboot" if user in group.gr_mem else "missing"


def in_desktop(environ=os.environ):
    return bool(environ.get("WAYLAND_DISPLAY") or environ.get("DISPLAY"))


def dsi_connected(drm=Path("/sys/class/drm")):
    for status in drm.glob("card*-DSI-*/status"):
        if status.read_text().strip() == "connected":
            return True
    return False


def pin_is_output(pin=PIN, run=subprocess.run):
    """After the trainer stopped, the pin must not be left driving the jack (pinctrl: 'op')."""
    try:
        out = run(["pinctrl", "get", str(pin)], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return False
    return " op " in f" {out} "


def sweep_result(minimum, maximum, mapping):
    """Which mapped channels reached both ends during the sweep: [(channel, min, max, ok)]."""
    channels = sorted({a.channel for a in mapping.axes} | {b.channel for b in mapping.buttons})
    return [(ch, minimum[ch - 1], maximum[ch - 1], minimum[ch - 1] <= 1020 and maximum[ch - 1] >= 1980)
            for ch in channels]


def rest_problems(channels, mapping):
    """Sticks let go and throttle at idle: centred axes near 1500, throttle at 1000."""
    problems = []
    for axis in mapping.axes:
        value = channels[axis.channel - 1]
        if axis.unipolar and value > 1030:
            problems.append(f"Kanal {axis.channel} ({ROLES.get(axis.channel, axis.source)}) steht auf {value} statt 1000")
        elif not axis.unipolar and abs(value - 1500) > 40:
            problems.append(f"Kanal {axis.channel} ({ROLES.get(axis.channel, axis.source)}) steht auf {value} statt 1500")
    return problems


def judge_capture(result):
    """ppmcheck result of the radio's own PPM (Slave/Jack) -> (ok, German explanation)."""
    if result is None:
        return False, ("Es kommt kein Signal an. Steht die Fernsteuerung auf Trainer-Modus Slave/Jack? "
                       "Steckt der Klinkenstecker ganz drin? Sitzt das Signal-Kabel auf Pin 11 und die Masse auf Pin 9?")
    if result["pulse_us_mean"] > 1000:
        return False, ("Das Signal ist andersherum gepolt als bei der getesteten RadioMaster Pocket. "
                       "Hier bitte NICHT weitermachen, sondern den Diagnose-Bericht schicken.")
    if result["channels"] < 4:
        return False, f"Nur {result['channels']} Kanäle erkannt, erwartet sind mindestens 4. Wackelkontakt?"
    frame = result.get("frame_us_mean") or 0
    return True, (f"Signal der Fernsteuerung erkannt: {result['channels']} Kanäle, Puls {result['pulse_us_mean']:.0f} µs, "
                  f"Rahmen {frame / 1000:.1f} ms. Kabel, Pins und Polarität stimmen.")


def lgpio_config_text(config_text):
    """The calibrated dry-run config with the output block switched to the measured Pocket values."""
    output = (
        "output:\n"
        "  sink: lgpio             # values measured on the RadioMaster Pocket, docs/jack-measurement.md\n"
        f"  pin: {PIN}                 # BCM 17 = header pin 11, through the series resistor to the jack tip\n"
        f"  chip: {CHIP}\n"
        "  pulse_us: 300\n"
        "  frame_us: 22500\n"
        "  active_high: false      # Pocket PPM idles high, pulses go low\n"
    )
    replaced, count = re.subn(r"(?ms)^output:\n(?:[ #].*?\n)*", output, config_text)
    if count != 1:
        raise ValueError("config has no output block")
    return replaced


# --- the steps -----------------------------------------------------------------------------------

class Assistant:
    def __init__(self, ui, state, repo=REPO):
        self.ui, self.state, self.repo = ui, state, repo
        self.config = repo / "config.yaml"
        self.config_lgpio = repo / "config.lgpio.yaml"

    def tip(self):
        return self.state.get("tip_colour", "Spitze")

    def sleeve(self):
        return self.state.get("sleeve_colour", "Schaft")

    def welcome(self):
        ui = self.ui
        ui.say("Hallo! Dieser Assistent führt dich durch den ganzen Aufbau des Joystick-Trainers.")
        ui.say("Du kannst jederzeit aufhören (Fenster schließen oder Strg + C). Dein Fortschritt bleibt")
        ui.say("gespeichert: Doppelklick auf das Symbol \"Einrichtung fortsetzen\" auf dem Desktop macht weiter.")
        ui.say("")
        ui.say("Drei Regeln, die immer gelten:")
        ui.say("  1. Das System ist NICHT zum Fliegen freigegeben. Nur auf dem Tisch testen.")
        ui.say("  2. An der Fernsteuerung immer ein Testmodell mit Internal RF und External RF = Off.")
        ui.say("     Dann funkt sie nichts und kein Modell kann sich bewegen.")
        ui.say("  3. Kabel am Raspberry Pi nur anstecken, wenn er aus ist und das Netzteil gezogen ist.")
        if not ui.yes("Hast du die drei Regeln gelesen und hältst du dich daran?"):
            raise Abort
        desktop.install_resume_icon(self.repo)
        return True

    def system(self):
        ui = self.ui
        model = pi_model()
        ui.say(f"Gerät: {model}")
        if "Raspberry Pi 5" not in model:
            ui.say("Das ist kein Raspberry Pi 5. Getestet ist nur der Pi 5; auf anderen Geräten nicht weitermachen.")
            return False
        groups = input_group_state()
        if groups == "reboot":
            ui.say("Die Installation ist fertig, der Pi muss aber einmal neu starten, damit er den Joystick lesen darf.")
            return self.reboot()
        if groups == "missing":
            ui.say("Die Installation ist nicht vollständig (Gruppe \"input\" fehlt). Starte den Assistenten über")
            ui.say("scripts/assistent.sh neu, der installiert das Fehlende.")
            return False
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        for module, name in (("evdev", "evdev"), ("lgpio", "rpi-lgpio"), ("pygame", "pygame")):
            try:
                __import__(module)
            except ImportError:
                ui.say(f"Das Programmteil {name} fehlt. Starte den Assistenten über scripts/assistent.sh neu.")
                return False
        ui.say("Raspberry Pi 5, Software installiert, Joystick-Rechte vorhanden: alles in Ordnung.")
        if not in_desktop():
            ui.say("Hinweis: Du bist nicht am Desktop des Pi (z. B. über SSH verbunden). Bis zur Kanalanzeige")
            ui.say("geht das, die Anzeige selbst musst du später am Pi starten (Symbol \"Einrichtung fortsetzen\").")
        return True

    def joystick(self):
        ui = self.ui
        ui.say("Steck jetzt den USB-Joystick in eine USB-Buchse des Pi.")
        ui.enter("Wenn er steckt: Enter.")
        found = calibrate.find_joysticks()
        names = [d.name for d in found]
        for device in found:
            device.close()
        if not names:
            ui.say("Kein Joystick gefunden. Ab- und wieder anstecken, andere USB-Buchse probieren.")
            return False
        if len(names) == 1:
            choice = names[0]
        else:
            ui.say("Mehrere Eingabegeräte gefunden:")
            for i, name in enumerate(names, 1):
                ui.say(f"  {i}: {name}")
            answer = ui.ask("Welche Nummer ist dein Joystick? ").strip()
            if not answer.isdigit() or not 1 <= int(answer) <= len(names):
                return False
            choice = names[int(answer) - 1]
        ui.say(f"Gefunden: {choice}")
        self.state["joystick"] = choice
        return True

    def calibrate(self):
        ui = self.ui
        ui.say("Jetzt lernt der Pi, welcher Hebel was ist. Für jeden Schritt:")
        ui.say("  erst die erste Stellung einnehmen -> Enter, dann die zweite Stellung HALTEN -> Enter.")
        ui.say("Wichtig: Wackel vorher einmal kurz an allen Hebeln, manche Joysticks melden sich erst dann.")
        if self.config.exists() and not ui.yes("Es gibt schon eine Kalibrierung. Neu kalibrieren (die alte wird ersetzt)?"):
            return True
        ui.enter("Bereit? Enter.")
        name, wizard = calibrate.evdev_device(self.state["joystick"])
        wizard.ask, wizard.say = ui.ask, ui.say
        axes, buttons = wizard.run(STEPS_DE)
        if len(axes) < 4:
            ui.say(f"Nur {len(axes)} von 4 Hebeln wurden erkannt. Ohne alle vier geht es nicht weiter.")
            return False
        self.config.write_text(calibrate.render_config(name, axes, buttons))
        if self.config_lgpio.exists():
            self.config_lgpio.write_text(lgpio_config_text(self.config.read_text()))
        ui.say("Kalibrierung gespeichert.")
        return True

    def sweep(self):
        from . import config as config_module
        from .joystick import Joystick
        from .mapper import Mapper

        ui = self.ui
        cfg = config_module.load(self.config)
        mapping = cfg["mapping"]
        joystick = Joystick(cfg["device"], [a.source for a in mapping.axes], [b.source for b in mapping.buttons])
        mapper = Mapper(mapping)
        seconds = 15
        try:
            ui.say(f"Prüfung: Bewege in den nächsten {seconds} Sekunden ALLE Hebel einmal ganz bis zu beiden")
            ui.say("Anschlägen (rechts/links, vor/zurück, Gas vor/zurück, drehen) und drück die Scharf-Taste zweimal.")
            ui.enter("Los geht's mit Enter.")
            minimum, maximum = [2000] * mapping.channel_count, [1000] * mapping.channel_count
            end, shown = time.monotonic() + seconds, 0.0
            while time.monotonic() < end:
                joystick.poll(0.02)
                values = mapper.channels(joystick.state)
                minimum = [min(a, b) for a, b in zip(minimum, values)]
                maximum = [max(a, b) for a, b in zip(maximum, values)]
                if time.monotonic() < shown:
                    continue
                shown = time.monotonic() + 0.2
                sys.stdout.write("\r  " + " ".join(f"{v:4d}" for v in values) + f"   noch {end - time.monotonic():4.1f} s ")
                sys.stdout.flush()
            ui.say("")
            results = sweep_result(minimum, maximum, mapping)
            for channel, low, high, ok in results:
                ui.say(f"  Kanal {channel} {ROLES.get(channel, ''):28s} {low:4d} .. {high:4d}  {'OK' if ok else 'NICHT VOLL'}")
            if not all(ok for *_, ok in results):
                ui.say("Nicht alle Kanäle haben 1000 und 2000 erreicht. Noch einmal und dabei bis zum Anschlag bewegen.")
                return False
            ui.say("Jetzt: Knüppel loslassen (Mitte), nicht verdreht, Gashebel ganz ZURÜCK.")
            ui.enter("Wenn alles so steht: Enter.")
            joystick.poll(0.1)
            problems = rest_problems(mapper.channels(joystick.state), mapping)
            for problem in problems:
                ui.say("  " + problem)
            if problems:
                ui.say("Die Ruhestellung stimmt nicht. Oft hilft es, die Kalibrierung zu wiederholen.")
                if ui.yes("Kalibrierung wiederholen?"):
                    self.state["done"] = [s for s in self.state["done"] if s != "calibrate"]
                return False
            ui.say("Alle Hebel arbeiten richtig.")
            return True
        finally:
            joystick.close()

    def display(self):
        ui = self.ui
        if not ui.yes("Hast du ein Raspberry Pi Touch Display 2 und willst die Kanalanzeige nutzen?"):
            self.state["display"] = False
            return True
        self.state["display"] = True
        if not dsi_connected():
            ui.say("Der Pi erkennt kein Display. So schließt du es an (Pi vorher AUS, Netzteil gezogen):")
            ui.say("  1. Flachbandkabel: SCHMALES Ende in eine Buchse \"CAM/DISP\" am Pi, BREITES Ende ans Display.")
            ui.say("     Metallkontakte am Display nach oben, am Pi zu den USB-Buchsen. Klemmbügel auf, Kabel rein, Bügel zu.")
            ui.say("  2. Stromkabel: kleiner Stecker ans Display (J1). Am Pi: ROT auf Pin 2, SCHWARZ auf Pin 6.")
            ui.say("     Bilder dazu: docs/DISPLAY.md im Projektordner, Abschnitt 5.")
            ui.say("Danach den Pi wieder einschalten und \"Einrichtung fortsetzen\" doppelklicken.")
            return self.poweroff()
        if not in_desktop():
            ui.say("Display erkannt. Die Anzeige lässt sich aber nur am Pi selbst starten, nicht über SSH.")
            ui.say("Setz dich an den Pi und doppelklicke \"Einrichtung fortsetzen\".")
            raise Abort
        ui.say("Display erkannt. Ich starte jetzt die Anzeige und das Trainer-Programm im Probelauf (es sendet nichts).")
        ui.say("Tipp: Steht das Bild hochkant, kannst du es später unter Einstellungen > Control Centre > Screens drehen.")
        procs = self.start_programs(self.config)
        try:
            ok = ui.yes("Siehst du auf dem Display Balken, die sich bewegen, wenn du den Joystick bewegst?")
        finally:
            self.stop_programs(procs)
        if not ok:
            ui.say("Dann bitte den Diagnose-Bericht erstellen (Symbol \"Diagnose\") und schicken.")
        return ok

    def wiring(self):
        ui = self.ui
        ui.say("Jetzt baust du das Kabel vom Pi zur Fernsteuerung. Du brauchst: Klinkenkabel mit offenen Adern,")
        ui.say("einen Widerstand 1-10 kOhm, zwei Jumper-Kabel (Buchse), ein Multimeter, Isolierband.")
        ui.say("")
        ui.say("a) Welche Ader ist welche? Multimeter auf Durchgang (Piepser). Eine Spitze an die SPITZE des Steckers,")
        ui.say("   mit der anderen die Adern antippen. Wo es piept, das ist die Ader der Spitze.")
        self.state["tip_colour"] = ui.ask("Welche Farbe hat die Ader der SPITZE? ").strip() or "Spitze"
        ui.say("   Dasselbe mit dem SCHAFT (das lange Metallstück direkt vor dem Griff).")
        self.state["sleeve_colour"] = ui.ask("Welche Farbe hat die Ader des SCHAFTS? ").strip() or "Schaft"
        ui.say("   Die dritte Ader (Ring) wird nicht gebraucht: Ende mit Isolierband abkleben.")
        ui.say("")
        ui.say("b) Pins am Pi (Stiftleiste oben, USB-Buchsen rechts):")
        ui.say("     obere Reihe:   2   4   6   8  10 ...")
        ui.say("     untere Reihe:  1   3   5   7  [9] [11] ...")
        ui.say("   Pin 11 = Signal, Pin 9 = Masse (GND). Pins 2 und 4 haben 5 Volt: nicht berühren!")
        ui.say("   (Pin 9 statt Pin 6, weil Pin 6 für das Display gebraucht wird. Pin 9 geht immer.)")
        ui.say("")
        ui.say("c) Verbinden:")
        ui.say(f"     Pin 11 -> Jumper-Kabel -> Widerstand -> Ader {self.tip()}")
        ui.say(f"     Pin 9  -> Jumper-Kabel -------------> Ader {self.sleeve()}")
        ui.say("   Verbindungen löten oder verdrillen + Wago-Klemme, alles Blanke isolieren. Zweimal nachzählen.")
        ui.say("   Dann den Klinkenstecker in die Trainer-Buchse der Pocket stecken.")
        ui.say("")
        ui.say("Dafür muss der Pi aus sein. Ich fahre ihn jetzt herunter. Wenn alles verbunden ist: Netzteil wieder")
        ui.say("einstecken und \"Einrichtung fortsetzen\" doppelklicken.")
        if ui.yes("Ist das Kabel schon fertig verbunden und der Stecker in der Pocket? (n = jetzt herunterfahren)"):
            return True
        self.state["done"].append("wiring")
        return self.poweroff()

    def radio(self):
        ui = self.ui
        ui.say("Jetzt die Fernsteuerung (RadioMaster Pocket). Die Menüs sind englisch. Hake jeden Punkt ab:")
        for item in (
            "Neues Modell anlegen, Name z. B. \"Pi\", und auswählen.",
            "In diesem Modell: Internal RF = Off und External RF = Off. (Dann funkt die Pocket nichts.)",
            "Special Functions dieses Modells ansehen und alles löschen, was du nicht selbst angelegt hast.",
            "Gibt es im Model Setup keinen Punkt \"Trainer\": Model Setup > Enabled Features > Trainer = On.",
            "Model Setup > Trainer: Mode = Slave/Jack (nur für den nächsten Test; danach kommt Master/Jack).",
        ):
            ui.say(f"  - {item}")
            ui.enter("Erledigt? Enter.")
        return True

    def radio_to_pi(self):
        from .ppmcheck import analyze

        ui = self.ui
        ui.say("Test: Die Pocket schickt jetzt ihr Signal zum Pi. Der Pi hört nur zu, er sendet nichts.")
        ui.enter("Pocket eingeschaltet, Modell \"Pi\" ausgewählt, Trainer = Slave/Jack? Enter.")
        edges = capture_edges(seconds=3)
        ok, message = judge_capture(analyze([(t, level) for t, level in edges], active_high=False) if edges else None)
        ui.say(message)
        return ok

    def pi_to_radio(self):
        ui = self.ui
        ui.say("Jetzt sendet der Pi zur Pocket. Erst die Pocket umstellen:")
        for item in (
            "Model Setup > Trainer: Mode = Master/Jack. Ch. Range CH1-8. PPM frame 22.5 ms, 300 us, Polarität \"-\".",
            "Special Functions > neue Zeile: Schalter SD unten (\"SD↓\") | Trainer | Sticks | an.",
            "Schalter SD nach OBEN stellen (= die Pocket steuert selbst).",
        ):
            ui.say(f"  - {item}")
            ui.enter("Erledigt? Enter.")
        self.config_lgpio.write_text(lgpio_config_text(self.config.read_text()))
        ui.say("Ich starte jetzt das Senden.")
        procs = self.start_programs(self.config_lgpio)
        try:
            checks = [
                "Schalter SD nach UNTEN. Zeigt die Pocket \"Trainer signal recovered\" (oder hat sie es kurz gezeigt)?",
                "Öffne auf der Pocket die Kanalanzeige (Channel Monitor). Folgen die Balken dem Joystick?",
                "Notschalter-Test: Gashebel am Joystick ganz vorne, Gasknüppel der Pocket ganz unten. SD unten = "
                "Kanalanzeige zeigt Vollgas, SD oben = Leerlauf. Ist das so?",
            ]
            ok = all(ui.yes(check) for check in checks)
        finally:
            self.stop_programs(procs)
        if ok:
            ok = ui.yes("Ich habe das Senden gestoppt. Zeigt die Pocket \"Trainer signal lost\"?")
        if pin_is_output():
            ui.say("Achtung: Pin 11 ist nach dem Beenden noch ein Ausgang. Bitte Diagnose-Bericht schicken.")
            return False
        if not ok:
            ui.say("Ein Punkt hat nicht gepasst. Prüfe die Einstellungen oben noch einmal; hilft das nicht,")
            ui.say("Diagnose-Bericht erstellen (Symbol \"Diagnose\") und schicken.")
        return ok

    def finish(self):
        ui = self.ui
        icons = desktop.install_icons(self.repo)
        ui.say("Geschafft! Dein Aufbau funktioniert so weit wie der getestete.")
        ui.say("Auf dem Desktop liegen jetzt diese Symbole:")
        for name in icons:
            ui.say(f"  - {name}")
        ui.say("")
        ui.say("Zur Erinnerung: NICHT damit fliegen. Was vorher noch getestet werden muss, steht in")
        ui.say("docs/SETUP.md, Abschnitt 11.")
        return True

    # --- helpers ---

    def start_programs(self, config):
        procs = []
        if self.state.get("display") and in_desktop():
            procs.append(subprocess.Popen([str(self.repo / ".venv/bin/joystick-trainer-display")]))
            time.sleep(1)
        procs.append(subprocess.Popen([str(self.repo / ".venv/bin/joystick-trainer"), str(config)],
                                      stdout=subprocess.DEVNULL))
        time.sleep(1)
        return procs

    def stop_programs(self, procs):
        for proc in reversed(procs):
            proc.terminate()
            try:
                proc.wait(3)
            except subprocess.TimeoutExpired:
                proc.kill()

    def reboot(self):
        save_state(self.state)
        if self.ui.yes("Jetzt neu starten? Danach \"Einrichtung fortsetzen\" auf dem Desktop doppelklicken."):
            subprocess.run(["sudo", "reboot"])
        raise Abort

    def poweroff(self):
        save_state(self.state)
        if self.ui.yes("Jetzt herunterfahren?"):
            self.ui.say("Warte, bis die grüne LED am Pi nicht mehr blinkt, erst dann das Netzteil ziehen.")
            subprocess.run(["sudo", "poweroff"])
        raise Abort


def capture_edges(seconds=3, pin=PIN, chip=CHIP):
    """Level changes on the pin as (time_s, level), input only (same as scripts/capture_gpio.py)."""
    import lgpio

    handle = lgpio.gpiochip_open(chip)
    edges = []
    try:
        lgpio.gpio_claim_alert(handle, pin, lgpio.BOTH_EDGES, lgpio.SET_PULL_NONE)
        callback = lgpio.callback(handle, pin, lgpio.BOTH_EDGES, lambda c, g, level, tick: edges.append((tick, level)))
        time.sleep(seconds)
        callback.cancel()
    finally:
        lgpio.gpio_free(handle, pin)
        lgpio.gpiochip_close(handle)
    if not edges:
        return []
    first = edges[0][0]
    return [((tick - first) / 1e9, level) for tick, level in edges]


STEPS = [
    ("welcome", "Willkommen und Sicherheit"),
    ("system", "Raspberry Pi prüfen"),
    ("joystick", "Joystick einstecken"),
    ("calibrate", "Joystick kalibrieren"),
    ("sweep", "Joystick prüfen"),
    ("display", "Kanalanzeige (Touch Display 2, optional)"),
    ("wiring", "Kabel zur Fernsteuerung bauen"),
    ("radio", "Fernsteuerung vorbereiten"),
    ("radio_to_pi", "Verbindung prüfen: Fernsteuerung -> Pi"),
    ("pi_to_radio", "Senden: Pi -> Fernsteuerung"),
    ("finish", "Fertig"),
]
CALIBRATION_ONLY = ["joystick", "calibrate", "sweep"]


def run(assistant, keys):
    ui, state = assistant.ui, assistant.state
    total = len(keys)
    for number, key in enumerate(keys, 1):
        if key in state["done"]:
            continue
        title = dict(STEPS)[key]
        while True:
            ui.title(number, total, title)
            if getattr(assistant, key)():
                if key not in state["done"]:
                    state["done"].append(key)
                save_state(state)
                break
            save_state(state)
            answer = ui.ask("\n>>> Nochmal versuchen (Enter), überspringen (u) oder aufhören (q)? ").strip().lower()
            if answer == "q":
                raise Abort
            if answer == "u":
                break


def main(argv=None):
    parser = argparse.ArgumentParser(prog="joystick-trainer-assistent")
    parser.add_argument("--kalibrieren", action="store_true", help="nur Joystick einstecken, kalibrieren, prüfen")
    parser.add_argument("--neu", action="store_true", help="von vorne beginnen (Kalibrierung bleibt erhalten)")
    args = parser.parse_args(argv)
    ui = Ui()
    state = {"done": []} if args.neu else load_state()
    assistant = Assistant(ui, state)
    keys = CALIBRATION_ONLY if args.kalibrieren else [key for key, _ in STEPS]
    if args.kalibrieren:
        state["done"] = [k for k in state["done"] if k not in CALIBRATION_ONLY]
    try:
        run(assistant, keys)
    except (Abort, KeyboardInterrupt):
        save_state(state)
        ui.say("\nAngehalten. Weitermachen: Doppelklick auf \"Einrichtung fortsetzen\" auf dem Desktop.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
