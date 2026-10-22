# Setup from scratch

This rebuilds the working setup of 2026-10-15 step by step: USB joystick -> Raspberry Pi 5 -> PPM
into the DSC (trainer) jack of a RadioMaster Pocket -> the Pocket's own radio link to the model.
Every value below was measured or tested on that day unless it says otherwise.

Read section 0 first. Do the sections in order; each one ends with a check that must pass before
the next one.

## 0. Safety rules

- Until section 9 is complete, use a **test model with Internal RF and External RF Off**: the radio
  then transmits nothing and no model can move.
- Never connect the Pi to a radio jack that has not been measured (section 3). The Pi's GPIO is 3.3 V
  only.
- Wire the Pi only while it is **powered off**. Header pins 2 and 4 are 5 V and sit right next to GND.
- Before any real flight: the open items in section 11 must be done, with props off and no battery.

## 1. Parts

| Part | Used here | Note |
|------|-----------|------|
| Raspberry Pi 5 | Pi OS Trixie (Debian 13), kernel 6.18, Python 3.13 | Any Pi 5 OS with `/dev/pio0` |
| USB joystick | Thrustmaster T.Flight Hotas X (USB 044f:b108) | Others work; calibrate in section 6 |
| RadioMaster Pocket | EdgeTX, DSC jack = 3.5 mm | Version was not recorded |
| 3.5 mm plug with open leads | A 3.5 mm-to-2x-RCA adapter cable cut open: three leads | Any 3-pole (TRS) plug with wires |
| Resistor 1-10 kOhm | 5-band, green-brown-black-brown-brown (5.1 k or 1.1 k, both fine) | Series protection for the GPIO |
| Jumper wires (Dupont) | to the Pi header | |
| Multimeter | continuity + DC volts | No frequency range needed |
| Windows PC (optional) | reads the Pocket as USB joystick, section 9b | Python 3, no packages |

## 2. Identify the leads of the plug cable

Lead colours are **not** standard. On our cable they were the opposite of the usual audio convention.

1. Cable not plugged in anywhere. Multimeter on continuity.
2. Touch one probe to the plug **tip**, the other to each lead in turn. Repeat for the **ring** (middle
   band) and the **sleeve** (the long shaft next to the grip).
3. Write it down. Ours: **red = tip, white = ring, black = sleeve.**
4. Insulate the bare ends so they cannot touch each other (tape or terminals).

From here on, use your colours. This guide says tip/ring/sleeve plus our colours in brackets.

## 3. Measure the radio jack

Full procedure and raw results: `docs/jack-measurement.md`. Short version and our result:

| Check | How | Pocket result |
|-------|-----|---------------|
| GND | radio off, plug in, continuity sleeve (black) to the USB-C shell of the radio | beeps: sleeve = GND |
| Idle levels | radio on, trainer off, DC volts tip/ring against sleeve | 2.8 V / 2.8 V |
| Slave/Jack (radio sends) | DC volts | tip 2.8 V (mean of PPM), ring 3.25 V |
| Master/Jack (radio listens) | DC volts | tip **0 V**, ring 3.25 V |

Conclusion for the Pocket: **tip = PPM in both directions, sleeve = GND, ring is not needed.** All
levels <= 3.3 V, so the Pi can drive the tip directly through the series resistor. A multimeter
cannot prove that the tip carries PPM (a 2.8 V mean looks like 2.8 V DC); section 9a proves it with
the Pi itself.

The trainer mode menu may be hidden on the Pocket, see section 8 step 3.

## 4. Pi header: find the pins

Hold the Pi with the 40-pin header on top and the USB/Ethernet sockets pointing **right**. Pin 1 is
at the **left** end of the **lower** row (the row towards the middle of the board); on the underside
it is the only **square** solder pad.

```
board edge
  2   4  [6]  8  10  12 ...   upper row: even numbers
  1   3   5   7   9 [11] ...  lower row: odd numbers
board middle                  -> USB / Ethernet on the right
```

- **Pin 6 = GND**: 3rd pin of the upper row.
- **Pin 11 = GPIO17**: 6th pin of the lower row.
- Pins 2 and 4 = **5 V**: leave free.

Check with the Pi powered off: continuity between the pin you think is 6 and the metal shell of a Pi
USB socket must beep; on pin 11 it must not.

## 5. Wire it (Pi off)

```
Pi pin 11 (GPIO17) ---[ 1-10 kOhm ]--- tip    (red)
Pi pin 6  (GND)    ------------------- sleeve (black)
                                        ring   (white): insulated, not connected
```

Then plug the 3.5 mm plug into the Pocket's DSC jack and power the Pi.

## 6. Install the software on the Pi

```
git clone <this repo> ~/joystick-trainer
cd ~/joystick-trainer
scripts/setup-pi.sh
```

`setup-pi.sh` (uses sudo for apt only) installs build tools and Python packages into `.venv`, builds
piolib into `.piolib/` (not `/usr/local`) and `native/ppm_pio`, enables linger and writes a systemd
user unit. Everything it changes outside the repo is listed in `.install-state`.

To remove everything again, exactly as it was before:

```
scripts/uninstall-pi.sh --delete-repo
```

Tested on 2026-10-15: after install + uninstall, dpkg, `/usr/local`, groups, linger and user units
were identical to the pre-install state.

Check: `.venv/bin/python -m pytest` passes (36 tests; `test_calibrate_uinput` is skipped without
uinput access, run it with `sudo .venv/bin/python -m pytest tests/test_calibrate_uinput.py`).

## 7. Calibrate the joystick

Plug the joystick into the Pi, then:

```
.venv/bin/joystick-trainer-calibrate config.yaml
```

It finds the joystick (or use `--device "name"`), then asks for one position at a time; you put the
control there, **hold it**, and press Enter:

| Step | Rest position | Held position | Channel |
|------|---------------|---------------|---------|
| roll | stick centred, let go | stick fully RIGHT | 1 |
| pitch | stick centred | stick fully FORWARD (away from you) | 2 |
| throttle | throttle fully back (IDLE) | throttle fully FORWARD | 3 |
| yaw | twist centred | twist fully RIGHT | 4 |
| arm | no button pressed | hold the ARM button | 5 (toggle) |

Type `s` + Enter to skip a step. From each pair it picks the axis that moved most, sets `invert`
so that **right / forward / full = 2000 us**, and warns if the rest position was off centre or the
held position did not reach the end of the travel. If two axes moved or nothing moved enough, it
asks again. Hats are ignored.

The result is a dry-run config (`sink: print`). For the Hotas X it is identical to
`config.hotas-x.yaml`, which was verified by hand (its throttle reads 255 at idle, hence inverted).

Check (dry run, no GPIO):

```
.venv/bin/joystick-trainer config.yaml
```

It prints the 8 channel values in us whenever they change. Every mapped axis must reach 1000 and
2000, centred sticks 1500, throttle at idle **1000**, arm 1000 until the button is pressed once
(each press flips it). Stop with Ctrl+C.

Elevator/aileron direction for a particular model is set in EdgeTX (servo reverse), not here.

## 8. Radio setup (EdgeTX on the Pocket)

Menu names as seen on the Pocket's monochrome screen; details in `docs/edgetx-setup.md`.

1. New model, e.g. "Pi". **Internal RF: Off, External RF: Off.**
2. Look at Special Functions of the new model and delete or overwrite anything you did not set.
3. If Model Setup shows no Trainer section: Model Setup > Enabled Features > **Trainer = On** (it was
   Global and hidden).
4. Model Setup > Trainer: **Mode Master/Jack**, **Ch. Range CH1-8**, **PPM frame 22.5 ms, 300 us,
   polarity "-"** (these were the defaults and match the Pi).
5. Special Functions, one line: **`SD down | Trainer | Sticks | enabled`**. SD is a latching
   2-position switch: down = the Pi flies, up = the Pocket's own sticks (manual override). `Sticks`
   is what the EdgeTX manual calls Axis; it covers channels 1-4 only.
6. Recommended: preflight switch check SD up, so loading the model warns if the Pi would already be
   in control (not set up yet on 2026-10-15).

## 9. Verify the link

### 9a. Radio -> Pi (proves the tip is PPM and its polarity)

Pocket Trainer mode **Slave/Jack** (the radio now sends on the tip). On the Pi:

```
.venv/bin/python scripts/capture_gpio.py --pin 17 --seconds 3 capture.csv
.venv/bin/ppmcheck --active-low capture.csv
```

Expected (ours, `docs/captures/pocket-slave-20261015.csv`): 8 channels, pulse ~300 us, frame
~22505 us, line idles high = negative polarity -> `active_high: false`. Without `--active-low`
ppmcheck measures the wrong phase and reports a ~2200 us "pulse". Zero edges = the radio is not in
Slave/Jack or the wiring is wrong.

Set the Pocket back to **Master/Jack** afterwards.

### 9b. Pi -> Radio

Write a config that drives GPIO17 with the measured values:

```
.venv/bin/joystick-trainer-calibrate --output lgpio config.lgpio.yaml
.venv/bin/joystick-trainer config.lgpio.yaml
```

With SD down, the Pocket shows **"Trainer signal recovered"** when the Pi starts and **"Trainer signal
lost"** when it stops; then its outputs follow its own sticks again.

Numbers instead of the radio screen: connect the Pocket to a Windows PC over USB-C, choose
**Joystick** on the radio, and on the PC:

```
python scripts/read_joy_windows.py              # lists joysticks; the Pocket is VID 1209 PID 4f54
python scripts/read_joy_windows.py <id> 60      # min/max per axis over 60 s while you move the joystick
```

Pocket USB axes map to channels as X = ch1, Y = ch2, Z = ch3, V = ch4 (range 0..65535). Our result
with full deflection: X 320-64477, Y 704-64798, Z 512-59988 (throttle sent up to 1925 us),
V 704-64798.

### 9c. Kill switch

Pi sending, Pocket throttle stick and joystick throttle at clearly different positions. Flip SD:
down = Pocket output follows the joystick, up = it follows its own stick. Tested and working.

### 9d. Channel display (optional)

`docs/DISPLAY.md` (German): Touch Display 2 power uses pins 2 and 6, so the trainer cable's GND moves to
**pin 9**. Start `.venv/bin/joystick-trainer-display` in the Pi's desktop session, then the trainer.
Not yet tested on a real display; Pi OS Lite does not work with the pip pygame (no kmsdrm).

Channel count is `channels:` (default 8); `channels * 2000 + 3000` must not exceed `frame_us`
(at most 9 at 22500). The config is rejected at load otherwise. Only 8 channels at 22.5 ms are tested.

## 10. Running it as a service

```
cp config.lgpio.yaml config.yaml
systemctl --user enable --now joystick-trainer
```

The unit runs `.venv/bin/joystick-trainer config.yaml`. On stop (SIGTERM) the program sets the pin
idle and hands it back as an **input** (fixed on 2026-10-15, tested for timeout, SIGINT and SIGTERM).
The service itself has **not** been tested yet.

## 11. Open before any real flight

- **Crash behaviour**: kill only the main process with `kill -9`, then the output process, then pull
  the Pi's power, each with SD down; watch what the Pocket does. Suspected risk: with only the main
  process killed, the output process may keep sending the last values. Not tested.
- Channel 5 (arm) does not pass with `Sticks`; needs `Chans` or a mix. Not tested.
- `lgpio` timing jitter is not measured; the `pio` backend has not been run on a Pi and probably
  does not reset its pin on exit.
- Preflight switch check for SD.

## 12. Gotchas we hit

| Symptom | Cause / fix |
|---------|-------------|
| Pi unreachable every few minutes | Weak WLAN; moving the Pi helped. Prefer Ethernet |
| Windows `ping` says replies received but SSH times out | "Destination host unreachable" counts as a reply; check from another Linux host |
| `pip install` fails building `lgpio` (`swig` missing) | needs `swig` + `liblgpio-dev`; `setup-pi.sh` installs them |
| piolib build fails with `cannot find -lgpiolib` | its examples need gpiolib; build only the `pio` target (done in `setup-pi.sh`) |
| No Trainer section in Model Setup | Enabled Features > Trainer = On |
| A channel stuck at 0 on the Pocket | stray Special Function (Override) in a new model |
| Throttle reversed | Hotas X reads 255 at idle; calibration sets invert |
| Dry run prints nothing while moving | `print` only prints on change: the joystick events did not arrive, or nothing moved |
| GPIO stayed an output after stopping | fixed; check with `pinctrl get 17` (should say `ip`) |
| A background test process ignores Ctrl+C/SIGINT | non-interactive shells start `&` jobs with SIGINT ignored; use SIGTERM |
| `pgrep -f` finds a process that isn't there | it matched the shell running pgrep |
| Full throttle right after start (Hotas X, until the lever was moved) | the Hotas X reads 0 on every axis until first moved; fixed 2026-10-22: an axis counts only once it reported, unreported throttles send 1000 |
