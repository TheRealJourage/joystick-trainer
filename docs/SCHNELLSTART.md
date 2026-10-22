# Schnellstart mit Assistent

Für dich, wenn du **keine Erfahrung mit Raspberry Pi, Linux oder Programmieren** hast. Du tippst einen
einzigen Befehl ein. Danach führt dich ein **Assistent** auf Deutsch durch alles, prüft selbst nach,
ob es geklappt hat, und sagt dir, was zu tun ist, wenn nicht.

Rechne mit **2–4 Stunden** für alles, davon 20 Minuten Warten auf die Installation.

Was das Ganze ist und wie es funktioniert, steht in der [Einsteiger-Anleitung, Abschnitt 1](ANLEITUNG.md#1-was-ist-das-überhaupt).
Dort steht auch jeder Schritt noch einmal zum Nachlesen, falls du lieber ohne Assistent arbeitest.

> **Nicht zum Fliegen.** Das System funktioniert auf dem Tisch, ist aber nicht flugfertig. An der
> Fernsteuerung immer ein Testmodell mit **Internal RF und External RF = Off** benutzen.

---

## 1. Was du brauchst

Alles aus der [Einkaufsliste](ANLEITUNG.md#4-einkaufsliste), dazu:

- **Raspberry Pi Touch Display 2 (7 Zoll)** mit seinen beiden Kabeln: Dann ist das Display gleich dein
  Bildschirm, und später siehst du darauf die Kanäle.
- **USB-Tastatur** (eine Maus ist praktisch, der Touchscreen geht aber auch).
- Internet am Pi (WLAN reicht).

## 2. SD-Karte vorbereiten (am PC, ca. 15 Minuten)

Genau wie in der [Einsteiger-Anleitung, Schritt 5](ANLEITUNG.md#5-den-raspberry-pi-vorbereiten):
**Raspberry Pi Imager**, Gerät **Raspberry Pi 5**, Betriebssystem **Raspberry Pi OS (64-bit)** (die
Version **mit Desktop**, nicht „Lite“), Benutzername, Passwort und WLAN eintragen.

## 3. Display anschließen (Pi aus!)

Bevor du den Pi das erste Mal einschaltest:

1. **Flachbandkabel:** das **schmale** Ende in eine der beiden Buchsen `CAM/DISP` am Pi, das **breite**
   Ende ans Display. Am Display zeigen die Metallkontakte nach oben, am Pi zu den USB-Buchsen. Die
   kleinen Klemmbügel vorsichtig aufklappen, Kabel ganz einschieben, Bügel zudrücken.
2. **Stromkabel:** der kleine Stecker kommt ans Display (Buchse `J1`). Am Pi: **rot auf Pin 2, schwarz
   auf Pin 6**. So findest du die Pins (Pi so halten, dass die USB-Buchsen nach rechts zeigen):

   ```
     obere Reihe (Platinenrand):   [2]  4  [6]  8  10 ...    2 = rot, 6 = schwarz
     untere Reihe:                  1   3   5   7   9 ...
   ```

   **Zweimal prüfen.** Falsch herum kann das Display kaputtgehen.

Offizielle Anleitung mit Bildern: <https://www.raspberrypi.com/documentation/accessories/touch-display-2.html>.

Dann SD-Karte rein, Tastatur und Joystick an USB, Netzteil einstecken. Nach ein paar Minuten siehst du
den Desktop. Steht er hochkant: **Himbeer-Menü > Einstellungen > Control Centre > Screens**, auf
`DSI-1` rechtsklicken, **Orientation** > Left oder Right, **Apply**.

## 4. Den Assistenten starten (ein Befehl)

1. Am Pi den **Browser** öffnen (Weltkugel-Symbol oben links) und **diese Seite** aufrufen. Dann kannst
   du den Befehl unten einfach kopieren, statt ihn abzutippen.
2. Ein **Terminal** öffnen: oben in der Leiste das Symbol mit dem schwarzen Fenster.
3. Diesen Befehl kopieren, im Terminal mit **Strg + Umschalt + V** einfügen und **Enter** drücken:

   ```
   bash <(curl -fsSL https://raw.githubusercontent.com/TheRealJourage/joystick-trainer/main/scripts/install.sh)
   ```

4. Es fragt nach deinem **Passwort** (das vom Imager). Beim Tippen erscheinen **keine Zeichen**, das ist
   normal. Blind tippen, Enter.
5. Jetzt wird installiert, **10–20 Minuten**. Es laufen viele Zeilen durch; Wörter wie „WARNING“ dabei
   sind in Ordnung. Danach startet der Assistent von selbst.

## 5. Was der Assistent mit dir macht

Er zeigt immer an, wo du bist („Schritt 4 von 11“). Bei jeder Frage tippst du `j` (ja) oder `n` (nein)
und Enter, oder einfach Enter zum Weitermachen.

| Schritt | Was passiert | Was du tust |
|---------|--------------|-------------|
| 1 | Sicherheitsregeln | lesen, `j` |
| 2 | prüft den Pi | nichts; evtl. Neustart, dann weiter mit dem Symbol (siehe unten) |
| 3 | sucht den Joystick | Joystick einstecken, Enter |
| 4 | Kalibrieren | Hebel in die angesagte Stellung bringen, festhalten, Enter |
| 5 | prüft den Joystick | 15 Sekunden lang alle Hebel bis zum Anschlag bewegen |
| 6 | Kanalanzeige auf dem Display | schauen, ob Balken erscheinen und sich bewegen |
| 7 | Kabel zur Fernsteuerung bauen | Adern mit dem Multimeter bestimmen, verbinden (Pi wird dafür ausgeschaltet) |
| 8 | Fernsteuerung vorbereiten | Einstellungen an der Pocket, eine nach der anderen |
| 9 | prüft das Kabel | nichts: der Pi misst das Signal der Pocket und sagt, ob alles stimmt |
| 10 | Pi steuert die Pocket | Notschalter SD testen, sagen, was die Pocket anzeigt |
| 11 | fertig | Symbole auf dem Desktop |

**Unterbrechungen sind normal.** Für den Neustart (Schritt 2) und zum Verkabeln (Schritt 7) schaltet der
Assistent den Pi ab. Dein Fortschritt bleibt gespeichert. Danach auf dem Desktop **„Einrichtung
fortsetzen“** doppelklicken; der Assistent macht genau dort weiter. Fragt der Pi beim Doppelklick,
was er mit der Datei tun soll: **„Ausführen“** wählen.

Klappt ein Schritt nicht, erklärt der Assistent, woran es liegen kann, und fragt: nochmal (Enter),
überspringen (`u`) oder aufhören (`q`).

## 6. Danach: die Symbole auf dem Desktop

| Symbol | Wofür |
|--------|-------|
| **Joystick-Trainer starten** | Kanalanzeige + Senden an die Fernsteuerung. Stoppen: Fenster schließen oder Strg + C |
| **Joystick kalibrieren** | wenn ein Hebel falsch herum geht oder du einen anderen Joystick nimmst |
| **Diagnose-Bericht** | wenn etwas nicht klappt (siehe unten) |
| **Einrichtung fortsetzen** | den Assistenten erneut öffnen |

## 7. Wenn etwas nicht klappt

Doppelklick auf **„Diagnose-Bericht“**. Auf dem Desktop erscheint eine Textdatei
`joystick-trainer-diagnose-….txt`. Schick sie der Person, die dir hilft (E-Mail oder USB-Stick). Darin
stehen keine Passwörter und keine WLAN-Daten, nur der Zustand des Pi und dieses Projekts.

Der Befehl aus Abschnitt 4 schlägt fehl?

| Meldung | Was tun |
|---------|---------|
| `curl: (6) Could not resolve host` | kein Internet: WLAN oben rechts in der Leiste prüfen |
| `curl: (22) … 404` | der Befehl ist falsch kopiert, oder das Projekt ist (noch) nicht öffentlich |
| `Sorry, try again.` | Passwort falsch getippt; nochmal |

## 8. Alles wieder entfernen

Terminal öffnen und:

```
~/joystick-trainer/scripts/uninstall-pi.sh --delete-repo
```

Das macht alles rückgängig, was die Installation am Pi verändert hat, auch die Symbole. Nur
Diagnose-Berichte auf dem Desktop bleiben liegen.
