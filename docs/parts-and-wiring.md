# Parts and wiring

Step-by-step procedure: `docs/SETUP.md`. Jack measurement: `docs/jack-measurement.md`.

## Parts

| Part | Why | Note |
|------|-----|------|
| 3.5 mm plug with open leads (TRS) | Jack plug to the Pi | We used a 3.5 mm-to-2x-RCA cable cut open. A 3-pole plug is enough for the Pocket; the ring is not used |
| Resistor 1-10 kOhm | In series with the signal pin | Protects the GPIO; we used a 5-band metal film (5.1 k or 1.1 k, both fine) |
| Jumper wires (Dupont) | Pi header to the leads | |
| Multimeter | Continuity, DC volts | No frequency range needed; the Pi does the signal check (`scripts/capture_gpio.py`) |
| USB logic analyzer (optional) | Independent PPM check | Export as CSV for `ppmcheck` |
| Pi 5 power supply | Official 27 W type | Brown-outs make PPM drop out |

## Connection (measured on the Pocket, in use since 2026-10-15)

    Pi header pin 11 (GPIO17) --[ 1-10 kOhm ]--> jack tip     (PPM, negative polarity, <= 3.3 V)
    Pi header pin 6  (GND)    -----------------> jack sleeve  (GND)
                                                 jack ring    not connected (~3.25 V when trainer on)

- Common ground is required.
- Lead colours of the plug cable are not standard: identify them by continuity (`docs/SETUP.md` 2).
  Ours: red = tip, white = ring, black = sleeve.
- Wire with the Pi off; header pins 2 and 4 (5 V) are next to pin 6.
- Any GPIO0-27 works for `lgpio`/`pio`; the configs and docs use GPIO17.

## Order of work

1. Dry run on the Pi (`sink: print`), joystick calibrated (`joystick-trainer-calibrate`).
2. Jack measured; radio in Slave/Jack, `scripts/capture_gpio.py` + `ppmcheck --active-low` on the tip.
3. Radio in Master/Jack, `sink: lgpio`, check what arrives (radio screen or USB joystick on a PC).
4. Kill switch, then crash/signal-loss tests with props off and no battery (`docs/SETUP.md` 11).
