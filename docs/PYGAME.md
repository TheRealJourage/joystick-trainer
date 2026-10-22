# Zusatzanleitung: Joystick über pygame einlesen

Diese Anleitung ist eine **Ergänzung** zur [Einsteiger-Anleitung](ANLEITUNG.md). Mach dort zuerst die
Schritte 1–7 (Pi vorbereiten, Software installieren). Hier geht es nur darum, **wie der Pi den
Joystick ausliest**. Alles danach (Kabel, Fernsteuerung, Notschalter) bleibt genau gleich.

Rechne mit **15–20 Minuten**.

---

## 1. Worum geht es?

Der Pi muss wissen, wie du den Joystick gerade hältst. Dafür gibt es zwei Wege, und **du wählst
einen davon**:

| | **evdev** (Standard) | **pygame** (diese Anleitung) |
|---|---|---|
| Was ist das? | liest den Joystick direkt über Linux | liest den Joystick über **pygame**, eine bekannte Bibliothek für Spiele in Python (darunter steckt SDL) |
| Installation | ist schon dabei | ein zusätzlicher Befehl (Schritt 3) |
| Getestet? | ja, komplett mit Hotas X und Pocket | teilweise, siehe unten |
| Namen der Hebel in der Einstellungsdatei | `ABS_X`, `ABS_Z`, `BTN_TRIGGER` … | `AXIS_0`, `AXIS_2`, `BUTTON_0` … |

So läuft das Signal mit pygame:

```
 USB-Joystick ──> pygame (SDL) ──> joystick-trainer ──> PPM ──> Fernsteuerung ──> Modell
                  ▲ nur dieser Teil ist anders als beim Standardweg
```

**Wann lohnt sich pygame?**

- Dein Joystick oder Gamepad wird mit evdev nicht gefunden oder verhält sich komisch.
- Du willst selbst mit pygame weiterbasteln (pygame ist gut dokumentiert und es gibt viele Beispiele).

Wenn der Standardweg bei dir funktioniert, brauchst du pygame **nicht**.

## 2. Stand: was mit pygame getestet ist

Getestet am 2026-10-22 auf dem Raspberry Pi 5 mit dem Thrustmaster T.Flight Hotas X:

- pygame lässt sich installieren, der Pi findet den Hotas X über pygame (5 Achsen, 12 Tasten, 1 Hat).
- Das Programm liest Achsen und Tasten über pygame aus.
- Abstecken des Joysticks wird erkannt (automatischer Test ohne Hardware).

**Noch nicht getestet:** die Kalibrierung mit echten Bewegungen über pygame, der Probelauf und das
Senden an die Pocket über pygame. Mach deshalb Schritt 5 und 6 genauso sorgfältig wie in der
Einsteiger-Anleitung, und die Sicherheitsregeln aus deren Abschnitt 2 gelten unverändert.

## 3. pygame installieren

Im Terminal auf dem Pi (wie das geht: [Einsteiger-Anleitung, Abschnitt 6](ANLEITUNG.md#6-ein-terminal-öffnen)):

```
cd ~/joystick-trainer
.venv/bin/pip install -e ".[pygame]"
```

Das dauert eine Minute. pygame landet dabei nur im Projektordner, nicht im restlichen System.

Prüfen, ob pygame den Joystick sieht (Joystick vorher einstecken):

```
.venv/bin/python -c "from joystick_trainer import pygame_input as p; print([j.get_name() for j in p.list_joysticks()])"
```

Es muss der Name deines Joysticks erscheinen, z. B. `['Thrustmaster T.Flight Hotas X']`.
`[]` heißt: kein Joystick gefunden, siehe Abschnitt 8.

## 4. Kalibrieren mit pygame

Genau wie in der [Einsteiger-Anleitung, Schritt 8](ANLEITUNG.md#8-den-joystick-einrichten), nur mit
`--input pygame` dahinter:

```
.venv/bin/joystick-trainer-calibrate --input pygame config.yaml
```

Hast du vorher schon mit dem Standardweg kalibriert, meldet es `config.yaml exists`. Dann:

```
.venv/bin/joystick-trainer-calibrate --input pygame --force config.yaml
```

**Wichtig beim Hotas X (und vielleicht anderen Joysticks):** Der Joystick meldet seine Werte erst,
wenn du ihn **einmal bewegt** hast. Wackel also vor dem Start kurz an allen Hebeln. Ohne Bewegung
stehen alle Achsen auf „ganz am Anschlag“.

Danach steht in der `config.yaml` eine Zeile `input: pygame`. Daran erkennt das Programm, dass es
pygame nehmen soll. Du musst sonst nichts umstellen.

## 5. Probelauf

Genau derselbe Befehl wie beim Standardweg:

```
.venv/bin/joystick-trainer config.yaml
```

Prüfen wie in der Einsteiger-Anleitung: Mitte = **1500**, Enden = **1000** und **2000**, Gas ganz
zurück = **1000**. Beenden mit **Strg + C**.

## 6. Senden an die Fernsteuerung

Kabel und Fernsteuerung wie in der Einsteiger-Anleitung, Schritte 9 und 10. Dann:

```
.venv/bin/joystick-trainer-calibrate --input pygame --output lgpio config.lgpio.yaml
.venv/bin/joystick-trainer config.lgpio.yaml
```

Weiter mit [Einsteiger-Anleitung, Schritt 11](ANLEITUNG.md#11-alles-zusammen-testen), ab Punkt 3
(SD nach unten, Kanalanzeige, Notschalter prüfen).

## 7. Zurück zum Standardweg

Einfach ohne `--input pygame` neu kalibrieren:

```
.venv/bin/joystick-trainer-calibrate --force config.yaml
```

Oder in der `config.yaml` die Zeile `input: pygame` löschen **und** neu kalibrieren. Die Namen der
Hebel (`AXIS_…` gegenüber `ABS_…`) unterscheiden sich, die alte Zuordnung passt also nicht.

## 8. Wenn etwas nicht klappt

| Was du siehst | Was du tun kannst |
|---------------|-------------------|
| `No module named 'pygame'` | Schritt 3 vergessen, oder nicht im Ordner `~/joystick-trainer` |
| `found 0 joysticks (none)` | Joystick ab- und wieder anstecken; nach der Installation einmal neu gestartet? (Einsteiger-Anleitung 7.4) |
| `found 2 joysticks` | ein zweites Eingabegerät steckt; abziehen oder `--device "Hotas"` (Teil des Namens) dazuschreiben |
| `no axis moved enough` bei der Kalibrierung | Hebel ganz bis zum Anschlag halten; vorher einmal an allen Hebeln wackeln (Abschnitt 4) |
| `is not a pygame control name, expected AXIS_<number>` | die `config.yaml` stammt vom Standardweg, hat aber `input: pygame`: neu kalibrieren (Abschnitt 4) |
| Probelauf zeigt dauerhaft 1000 oder 2000 | Joystick nach dem Einstecken noch nicht bewegt, siehe Abschnitt 4 |

## 9. Entfernen

pygame steckt nur im Projektordner. Es verschwindet mit
`scripts/uninstall-pi.sh --delete-repo` ([Einsteiger-Anleitung, Abschnitt 13](ANLEITUNG.md#13-alles-wieder-entfernen)).
Nur pygame entfernen, den Rest behalten:

```
.venv/bin/pip uninstall -y pygame
```

Danach mit dem Standardweg neu kalibrieren (Abschnitt 7).

## 10. Für Bastler: wo pygame im Code steckt

Diesen Abschnitt brauchst du nur, wenn du selbst programmieren willst.

- `src/joystick_trainer/pygame_input.py`: die pygame-Eingabe. Die Klasse `PygameJoystick` hat dieselbe
  Schnittstelle wie die evdev-Eingabe in `joystick.py`: `state` (aktuelle Werte), `lost` (Joystick
  abgesteckt), `poll(timeout)` (auf Änderungen warten und Werte lesen) und `close()`.
- Achsen werden als `AXIS_<n>` mit Werten von -32767 bis 32767 abgelegt, Tasten als `BUTTON_<n>`.
  Hats (Coolie-Hat / Steuerkreuz) werden nicht ausgewertet.
- Die Auswahl passiert über `input:` in der Config (`config.py`) und `joystick_class()` in `cli.py`.
- pygame läuft ohne Fenster (`SDL_VIDEODRIVER=dummy`) und bekommt Joystick-Ereignisse auch ohne
  Fokus (`SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1`).
- Tests: `tests/test_pygame_input.py` (mit einem nachgebauten pygame, braucht keine Hardware).
