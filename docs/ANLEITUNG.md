# Anleitung für Einsteiger

Diese Anleitung ist für dich, wenn du **noch nie mit GitHub, Linux oder Programmieren** zu tun hattest.
Du musst nichts programmieren. Du tippst (oder kopierst) ein paar fertige Befehle ab, steckst ein paar
Kabel und stellst etwas an deiner Fernsteuerung ein.

Rechne mit **3–5 Stunden** für den ersten Aufbau (ohne Wartezeit auf Teile).

Die technische Fassung mit allen Messwerten steht in [`SETUP.md`](SETUP.md) (Englisch). Diese Anleitung
folgt derselben Reihenfolge und verweist dorthin, wenn du Details brauchst.

---

## Inhalt

1. [Was ist das überhaupt?](#1-was-ist-das-überhaupt)
2. [Wichtig: Sicherheit und Stand](#2-wichtig-sicherheit-und-stand)
3. [Kurz erklärt: GitHub, Terminal, Befehle](#3-kurz-erklärt-github-terminal-befehle)
4. [Einkaufsliste](#4-einkaufsliste)
5. [Den Raspberry Pi vorbereiten](#5-den-raspberry-pi-vorbereiten)
6. [Ein Terminal öffnen](#6-ein-terminal-öffnen)
7. [Die Software installieren](#7-die-software-installieren)
8. [Den Joystick einrichten (ohne Kabel zur Fernsteuerung)](#8-den-joystick-einrichten)
9. [Das Kabel bauen](#9-das-kabel-bauen)
10. [Die Fernsteuerung einstellen](#10-die-fernsteuerung-einstellen)
11. [Alles zusammen testen](#11-alles-zusammen-testen)
12. [Wenn etwas nicht klappt](#12-wenn-etwas-nicht-klappt)
13. [Alles wieder entfernen](#13-alles-wieder-entfernen)
14. [Wörterbuch](#14-wörterbuch)

---

## 1. Was ist das überhaupt?

Du willst ein ferngesteuertes Modell (z. B. eine Drohne oder ein Flugzeug) mit einem **PC-Joystick**
steuern statt mit den kleinen Knüppeln der Fernsteuerung.

So läuft das Signal:

```
 USB-Joystick  ──USB──>  Raspberry Pi 5  ──Kabel──>  Fernsteuerung  ──Funk──>  Modell
 (Hotas X)               (kleiner Computer)          (RadioMaster Pocket)
```

- Der **Raspberry Pi** liest aus, wie du den Joystick bewegst.
- Er wandelt das in ein Signal um, das Fernsteuerungen verstehen (**PPM**), und schickt es über ein
  Kabel in die **Trainer-Buchse** der Fernsteuerung. Das ist dieselbe Buchse, über die sonst ein
  Fluglehrer und ein Schüler zwei Fernsteuerungen verbinden.
- Die Fernsteuerung funkt wie gewohnt zum Modell. **Am Modell änderst du nichts.**
- Mit einem **Schalter an der Fernsteuerung** (bei uns „SD“) schaltest du jederzeit zurück auf die
  eigenen Knüppel der Fernsteuerung. Das ist dein Notschalter.

Getestet wurde genau diese Kombination: **Raspberry Pi 5**, Joystick **Thrustmaster T.Flight Hotas X**,
Fernsteuerung **RadioMaster Pocket** mit EdgeTX. Andere Joysticks funktionieren wahrscheinlich auch
(Schritt 8 erkennt sie). Bei einer anderen Fernsteuerung musst du die Buchse selbst ausmessen
(siehe [`jack-measurement.md`](jack-measurement.md)) – das ist dann nichts mehr für Einsteiger.

## 2. Wichtig: Sicherheit und Stand

> **Das System ist nicht flugfertig.** Es funktioniert auf dem Tisch: Der Pi steuert die Fernsteuerung
> über den ganzen Weg, der Notschalter funktioniert. **Nicht getestet** ist, was passiert, wenn der Pi
> abstürzt oder der Strom wegfällt. Bis das geklärt ist: **nicht mit einem echten Modell fliegen.**
> Die offenen Punkte stehen in [`SETUP.md`](SETUP.md) Abschnitt 11.

Regeln, die immer gelten:

- Solange du baust und testest, nutzt du an der Fernsteuerung ein **Testmodell, bei dem der Funk
  ausgeschaltet ist** (Internal RF und External RF auf **Off**). Dann sendet die Fernsteuerung nichts
  und kein Modell kann sich bewegen. Wie das geht, steht in Schritt 10.
- Bei echten Modellen später: **Propeller ab, Akku raus**, bis alles geprüft ist.
- Kabel am Pi **nur im ausgeschalteten Zustand** (Netzteil gezogen) anstecken oder abziehen.
- Die Anschlüsse des Pi vertragen nur **3,3 Volt**. Zwei Pins direkt daneben führen 5 Volt – Schritt 9
  zeigt genau, welche Pins du nimmst.

## 3. Kurz erklärt: GitHub, Terminal, Befehle

**GitHub** ist eine Webseite, auf der Leute Software und Anleitungen ablegen. Diese Sammlung hier
heißt **Repository** (kurz „Repo“) – stell es dir wie einen Ordner vor. Du brauchst **kein
GitHub-Konto**. Du kannst alle Dateien im Browser lesen: einfach anklicken.

**Das Terminal** ist ein Fenster, in das man Befehle als Text eintippt, statt mit der Maus zu klicken.
Auf dem Raspberry Pi installierst und startest du die Software darüber.

**Befehle** stehen in dieser Anleitung in grauen Kästen, z. B.:

```
cd ~/joystick-trainer
```

So gehst du damit um:

1. Den Text im Kasten kopieren (auf GitHub gibt es rechts oben im Kasten ein Kopier-Symbol).
2. Ins Terminal einfügen. Achtung: Im Terminal des Raspberry Pi heißt Einfügen **Strg + Umschalt + V**
   (nicht nur Strg + V). In der Windows-PowerShell reicht ein **Rechtsklick**.
3. **Enter** drücken.
4. Warten, bis wieder die Eingabezeile erscheint (sie endet mit `$`).

Gut zu wissen:

- Ein Befehl mit `sudo` fragt nach dem **Passwort** deines Pi. Beim Tippen erscheinen **keine Zeichen**
  – das ist normal. Einfach blind tippen und Enter.
- Ein laufendes Programm beendest du mit **Strg + C**.
- Text hinter `#` ist nur eine Erklärung. Den kannst du mitkopieren, er stört nicht.
- Fast alle Befehle müssen **im Projektordner** laufen. Wenn ein Befehl „No such file or directory“
  meldet, hast du wahrscheinlich `cd ~/joystick-trainer` vergessen.

## 4. Einkaufsliste

| Teil | Wofür | Hinweis |
|------|-------|---------|
| Raspberry Pi 5 | der kleine Computer | getestet mit dem Pi 5; ältere Pis werden **nicht** unterstützt |
| Offizielles Pi-5-Netzteil (27 W, USB-C) | Strom | schwache Netzteile lassen das Signal aussetzen |
| microSD-Karte | Betriebssystem | 16 GB oder mehr |
| USB-Joystick | zum Steuern | getestet: Thrustmaster T.Flight Hotas X |
| RadioMaster Pocket mit EdgeTX | Fernsteuerung | getestet; andere siehe Abschnitt 1 |
| Kabel mit 3,5-mm-Klinkenstecker und offenen Adern | Verbindung zur Fernsteuerung | wir haben ein „3,5 mm auf 2× Cinch“-Kabel durchgeschnitten; ein 3-poliger Stecker (Spitze/Ring/Schaft) reicht |
| Widerstand 1–10 kΩ (Kiloohm) | schützt den Pi | jeder Wert dazwischen geht, z. B. 4,7 kΩ oder 10 kΩ |
| 2 Jumper-Kabel „Buchse“ (Dupont, female) | Steckverbindung zum Pi | gibt es im Set für wenige Euro |
| Isolierband oder Schrumpfschlauch, evtl. Wago-Klemmen | Verbindungen isolieren | |
| Multimeter | Kabeladern bestimmen | ein einfaches mit Durchgangsprüfer (Piepser) reicht |

Zum Einrichten zusätzlich **eins von beiden**:

- **Variante A (einfacher):** Bildschirm mit **Micro-HDMI**-Kabel, USB-Tastatur und Maus für den Pi.
- **Variante B:** ein Windows-PC im selben WLAN – du bedienst den Pi dann vom PC aus.

## 5. Den Raspberry Pi vorbereiten

Du spielst das Betriebssystem (**Raspberry Pi OS**) mit einem kostenlosen Programm auf die SD-Karte.

1. Am PC den **Raspberry Pi Imager** von <https://www.raspberrypi.com/software/> herunterladen und
   installieren.
2. SD-Karte in den PC stecken, Imager starten.
3. Auswählen:
   - Gerät: **Raspberry Pi 5**
   - Betriebssystem: **Raspberry Pi OS (64-bit)**
   - Speicher: deine SD-Karte
4. Der Imager bietet an, **Einstellungen anzupassen** (je nach Version heißt das „OS customisation“
   o. Ä.). Ja wählen und eintragen:
   - **Hostname:** z. B. `joypi` (so heißt der Pi später im Netzwerk)
   - **Benutzername und Passwort:** gut merken, du brauchst beides
   - **WLAN:** Name und Passwort deines WLANs, Land **DE**
   - **SSH aktivieren** (mit Passwort) – nötig für Variante B, schadet bei Variante A nicht
5. Schreiben lassen, warten, SD-Karte auswerfen.
6. SD-Karte in den Pi stecken, bei Variante A Bildschirm/Tastatur/Maus anschließen, dann das Netzteil.
   Der erste Start dauert ein paar Minuten.

## 6. Ein Terminal öffnen

**Variante A (direkt am Pi):** Auf dem Desktop oben in der Leiste auf das Symbol mit dem schwarzen
Fenster klicken (Terminal).

**Variante B (vom Windows-PC):**

1. Am PC auf Start klicken, `PowerShell` eintippen, öffnen.
2. Eingeben (Benutzername und Hostname aus Schritt 5 einsetzen):

   ```
   ssh benutzername@joypi.local
   ```

3. Beim ersten Mal fragt es, ob du der Verbindung vertraust: `yes` tippen, Enter.
4. Passwort eingeben (unsichtbar, siehe Abschnitt 3).

Klappt `joypi.local` nicht, schau in deinem Router (z. B. FRITZ!Box: Heimnetz > Netzwerk) nach der
IP-Adresse des Pi und nimm die stattdessen, z. B. `ssh benutzername@192.168.178.50`.

Alle folgenden Befehle tippst du in dieses Terminal.

## 7. Die Software installieren

1. Erst den Pi auf den neuesten Stand bringen (dauert einige Minuten):

   ```
   sudo apt update
   sudo apt full-upgrade -y
   sudo apt install -y git
   sudo reboot
   ```

   Der Pi startet neu. Bei Variante B bricht dabei die Verbindung ab – nach einer Minute wieder mit
   `ssh …` verbinden (Schritt 6).

2. Die Software aus diesem Repo auf den Pi holen:

   ```
   git clone https://github.com/TheRealJourage/joystick-trainer.git ~/joystick-trainer
   ```

   Das legt im Benutzerordner einen Ordner `joystick-trainer` mit allen Dateien an.

3. In den Ordner wechseln und das Installationsskript starten (dauert 5–15 Minuten):

   ```
   cd ~/joystick-trainer
   scripts/setup-pi.sh
   ```

   Es fragt einmal nach deinem Passwort. Am Ende stehen ein paar Prüfzeilen. Steht dort
   `WARNING: /dev/pio0 missing`, hast du Schritt 1 ausgelassen.

   Das Skript merkt sich alles, was es außerhalb des Ordners verändert. Du kannst es später
   vollständig rückgängig machen (Abschnitt 13).

4. Einmal neu starten, damit der Pi den Joystick lesen darf:

   ```
   sudo reboot
   ```

5. Prüfen, ob alles da ist (nach dem Neustart wieder ein Terminal öffnen):

   ```
   cd ~/joystick-trainer
   .venv/bin/python -m pytest
   ```

   Am Ende muss eine grüne Zeile mit `passed` stehen. Ein `skipped` ist in Ordnung. Steht dort
   `failed`, hör hier auf und schau in Abschnitt 12.

## 8. Den Joystick einrichten

In diesem Schritt ist der Pi **noch nicht** mit der Fernsteuerung verbunden. Es geht nur darum, dass
der Pi weiß, welcher Hebel was ist.

1. Joystick per USB an den Pi stecken.
2. Kalibrierung starten:

   ```
   cd ~/joystick-trainer
   .venv/bin/joystick-trainer-calibrate config.yaml
   ```

3. Das Programm fragt nacheinander nach jeder Bewegung. Immer gleich: **Position einnehmen, festhalten,
   Enter drücken.**

   | Schritt | Erst so halten … | … dann so halten | wird Kanal |
   |---------|------------------|------------------|------------|
   | roll (Querruder) | Knüppel in der Mitte loslassen | Knüppel ganz nach **rechts** | 1 |
   | pitch (Höhenruder) | Knüppel in der Mitte | Knüppel ganz nach **vorne** (von dir weg) | 2 |
   | throttle (Gas) | Gashebel ganz **zurück** | Gashebel ganz **nach vorne** | 3 |
   | yaw (Seitenruder) | Drehgriff in der Mitte | Knüppel ganz nach **rechts drehen** | 4 |
   | arm (Scharfschalten) | keine Taste gedrückt | die Taste gedrückt halten, die du dafür willst | 5 |

   Einen Schritt überspringen: `s` tippen, Enter. Wenn das Programm unsicher ist, fragt es noch einmal.

4. Probelauf – der Pi zeigt nur Zahlen an, sendet aber nichts:

   ```
   .venv/bin/joystick-trainer config.yaml
   ```

   Beweg den Joystick. Es erscheinen Zeilen mit 8 Zahlen, eine Zahl pro Kanal. Das muss stimmen:

   - Knüppel in der Mitte: **1500**
   - ganz an einem Ende **1000**, am anderen **2000**
   - Gas ganz zurück: **1000**

   Beenden mit **Strg + C**.

Erscheint gar nichts, wenn du den Joystick bewegst: Abschnitt 12.

**Alternative:** Statt über Linux direkt kann der Pi den Joystick auch über **pygame** auslesen,
z. B. wenn dein Joystick oder Gamepad hier nicht gefunden wird. Das steht in der Zusatzanleitung
[`PYGAME.md`](PYGAME.md).

## 9. Das Kabel bauen

**Ab hier ist der Pi ausgeschaltet** (`sudo poweroff` eingeben, warten bis die LED nicht mehr
blinkt, dann Netzteil ziehen).

### 9.1 Welche Ader ist welche?

Ein Klinkenstecker hat drei Kontakte:

```
   Spitze   Ring    Schaft (langes Stück vor dem Griff)
    ▼        ▼       ▼
   ◀█▌──────█▌────────────█████  Griff
```

Die Farben der Adern sind **nicht genormt**. Du musst sie messen:

1. Multimeter auf **Durchgang** stellen (Symbol mit Lautsprecher/Piepser).
2. Eine Messspitze an die **Spitze** des Steckers, mit der anderen nacheinander die Adern antippen.
   Die Ader, bei der es piept, gehört zur Spitze. Aufschreiben.
3. Dasselbe für den **Schaft**.
4. Die dritte Ader (Ring) wird **nicht gebraucht**: Ende mit Isolierband abkleben.

Bei uns war es: **rot = Spitze, weiß = Ring, schwarz = Schaft.** Bei dir kann es anders sein.

### 9.2 Die richtigen Pins am Pi finden

Der Pi hat eine Doppelreihe mit 40 Metallstiften (Pins). Halte den Pi so, dass diese Stiftleiste
**oben** liegt und die USB- und Netzwerkbuchsen nach **rechts** zeigen:

```
          Rand der Platine
  ┌──────────────────────────────────────
  │  2   4  [6]  8  10  12  …     obere Reihe
  │  1   3   5   7   9 [11]  …    untere Reihe
  └──────────────────────────────────────    → USB/Netzwerk rechts
          Mitte der Platine
```

- **Pin 6** = Masse (GND): obere Reihe, **dritter** Stift von links.
- **Pin 11** = Signal (GPIO17): untere Reihe, **sechster** Stift von links.
- **Pins 2 und 4 (5 Volt) nicht berühren!**

Kontrolle mit dem Multimeter (Pi aus, Durchgangsprüfung): zwischen Pin 6 und dem Metallgehäuse einer
USB-Buchse des Pi muss es **piepen**, zwischen Pin 11 und dem Gehäuse **nicht**.

### 9.3 Verbinden

```
Pi Pin 11 ──── Jumper-Kabel ────[ Widerstand ]──── Ader der SPITZE  (bei uns rot)
Pi Pin 6  ──── Jumper-Kabel ─────────────────────── Ader des SCHAFTS (bei uns schwarz)
                                                    Ader des RINGS   (bei uns weiß): abgeklebt
```

- Der Widerstand sitzt **zwischen** Pin 11 und der Spitzen-Ader. Er hat keine Richtung, egal wie
  herum.
- Die Verbindungen löten, oder verdrillen und mit einer Wago-Klemme sichern. Danach alle blanken
  Stellen isolieren, damit sich nichts berührt.
- Jumper-Kabel auf Pin 11 und Pin 6 stecken. **Zweimal nachzählen.**

Dann den Stecker in die **Trainer-Buchse** der Pocket stecken (die 3,5-mm-Klinkenbuchse) und erst
jetzt den Pi wieder einschalten.

## 10. Die Fernsteuerung einstellen

Die Menünamen sind auf der Pocket englisch. Mehr Details: [`edgetx-setup.md`](edgetx-setup.md).

1. Ein **neues Modell** anlegen, z. B. mit dem Namen „Pi“.
2. Im Modell **Internal RF: Off** und **External RF: Off** einstellen. Jetzt sendet die Fernsteuerung
   nichts – sicher zum Testen.
3. Unter **Special Functions** des neuen Modells nachsehen und alles löschen, was du nicht selbst
   angelegt hast.
4. Gibt es im **Model Setup** keinen Punkt **Trainer**: Model Setup > **Enabled Features** >
   **Trainer = On**.
5. Model Setup > **Trainer**:
   - Mode: **Master/Jack**
   - Ch. Range: **CH1–8**
   - PPM frame **22.5 ms**, **300 us**, Polarität **„-“** (das waren bei uns die Standardwerte)
6. **Special Functions** > neue Zeile: **`SD down | Trainer | Sticks | enabled`**

   Das ist der **Notschalter**: Schalter SD **unten** = der Joystick steuert, SD **oben** = die
   eigenen Knüppel der Pocket steuern.

## 11. Alles zusammen testen

1. Am Pi eine Einstellungsdatei erzeugen, die jetzt wirklich sendet. Die Kalibrierung läuft dafür
   noch einmal genauso wie in Schritt 8:

   ```
   cd ~/joystick-trainer
   .venv/bin/joystick-trainer-calibrate --output lgpio config.lgpio.yaml
   ```

2. Senden starten:

   ```
   .venv/bin/joystick-trainer config.lgpio.yaml
   ```

3. Schalter **SD nach unten**. Die Pocket meldet **„Trainer signal recovered“**.
4. Den Joystick bewegen und auf der Pocket die Kanalanzeige (Channel Monitor) ansehen: die Balken
   müssen dem Joystick folgen.
5. **Notschalter prüfen:** Gashebel am Joystick und Gasknüppel der Pocket in verschiedene Stellungen
   bringen. SD unten = Anzeige folgt dem Joystick, SD oben = Anzeige folgt der Pocket.
6. Am Pi **Strg + C**. Die Pocket meldet **„Trainer signal lost“** und folgt wieder ihren eigenen
   Knüppeln.

Wenn das alles klappt, funktioniert dein Aufbau genauso weit wie unserer. **Fliegen noch nicht** –
siehe Abschnitt 2.

## 12. Wenn etwas nicht klappt

| Was du siehst | Was du tun kannst |
|---------------|-------------------|
| `No such file or directory` | erst `cd ~/joystick-trainer`, dann den Befehl wiederholen |
| `Permission denied` beim Joystick | Neustart vergessen (Schritt 7.4): `sudo reboot` |
| `config.yaml exists; use --force to overwrite` | du kalibrierst ein zweites Mal: denselben Befehl mit ` --force` am Ende wiederholen |
| `found 0 joysticks` | Joystick nicht eingesteckt oder nicht erkannt: ab- und wieder anstecken |
| `found 2 joysticks` | noch ein zweites Eingabegerät steckt; das andere abziehen |
| Probelauf zeigt nichts, wenn du den Joystick bewegst | Joystick ab- und wieder anstecken; es erscheinen nur Zeilen, wenn sich etwas ändert |
| Gas ist verkehrt herum | Kalibrierung (Schritt 8) wiederholen, Gashebel genau wie beschrieben halten |
| Pi per WLAN ständig weg | Pi näher an den Router stellen oder Netzwerkkabel nehmen |
| Pocket meldet nie „signal recovered“ | Mode Master/Jack? SD unten? Pins 11 und 6 nachzählen (Pi aus!) |
| Ein Kanal bleibt auf der Pocket fest auf einem Wert | im neuen Modell steht noch eine alte Special Function, löschen (Schritt 10.3) |
| `failed` beim Test in Schritt 7.5 | Ausgabe abfotografieren oder kopieren und als „Issue“ auf GitHub melden (Reiter **Issues** oben im Repo; dafür brauchst du ein kostenloses Konto) |

Weitere Fälle stehen in [`SETUP.md`](SETUP.md) Abschnitt 12.

**Tipp:** Wenn du mit einer KI (z. B. Claude oder ChatGPT) weitermachen willst, gib ihr die Datei
[`AGENTS.md`](../AGENTS.md). Darin steht, wie sie dir bei diesem Projekt helfen soll.

## 13. Alles wieder entfernen

Das macht alles rückgängig, was die Installation am Pi verändert hat, und löscht den Ordner:

```
cd ~/joystick-trainer
scripts/uninstall-pi.sh --delete-repo
```

## 14. Wörterbuch

| Wort | Bedeutung |
|------|-----------|
| Repository / Repo | der „Ordner“ auf GitHub mit allen Dateien dieses Projekts |
| `git clone` | lädt das Repo auf den Pi herunter |
| Terminal | Fenster zum Eintippen von Befehlen |
| `sudo` | führt einen Befehl mit Administratorrechten aus (fragt nach dem Passwort) |
| SSH | den Pi vom PC aus über das Netzwerk bedienen |
| GPIO / Pin | die Metallstifte am Pi, über die er Signale ausgibt |
| GND / Masse | der gemeinsame Minuspol; muss zwischen Pi und Fernsteuerung verbunden sein |
| PPM | ein Signal, das alle Kanäle nacheinander als kurze Pulse überträgt; Fernsteuerungen nutzen es an der Trainer-Buchse |
| Trainer / Lehrer-Schüler | Funktion der Fernsteuerung, Steuerbefehle von außen anzunehmen |
| Master/Jack | die Pocket nimmt Steuerbefehle über die Buchse an |
| Kanal | ein Steuerwert, z. B. Kanal 3 = Gas; Werte von 1000 bis 2000 |
| Kalibrieren | dem Pi zeigen, welcher Hebel was ist und in welche Richtung |
| Testmodell mit RF Off | Modellspeicher in der Fernsteuerung, der nichts funkt |
