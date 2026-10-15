# joystick-trainer

Fly an RC model with a USB joystick: a Raspberry Pi 5 reads the joystick and sends PPM into the
trainer (DSC) jack of a RadioMaster Pocket (EdgeTX, Trainer = Master/Jack); the Pocket transmits to
the model over its own link. A switch on the radio (SD) hands control back to the radio's sticks.

**Status (2026-10-15):** working on the bench with a test model that does not transmit. Verified:
joystick -> Pi (all axes 1000-2000 us), Pocket jack measured (tip = PPM, negative polarity, 3.3 V),
Pi -> Pocket (all four stick channels arrive over the full range), signal lost/recovered on stop/start,
kill switch. **Not flight-ready**: crash behaviour, arm channel and timing jitter are untested, see
`docs/SETUP.md` section 11.

## Rebuild it

Follow **`docs/SETUP.md`** from section 0. Short version once the hardware is wired:

    scripts/setup-pi.sh                                   # reversible, see .install-state
    .venv/bin/joystick-trainer-calibrate config.yaml      # guided: hold each position, press Enter
    .venv/bin/joystick-trainer config.yaml                # dry run, prints channel values
    .venv/bin/joystick-trainer-calibrate --output lgpio config.lgpio.yaml
    .venv/bin/joystick-trainer config.lgpio.yaml          # PPM on GPIO17 (header pin 11)

Remove everything: `scripts/uninstall-pi.sh --delete-repo`.

Wiring (Pocket, measured): GPIO17 (pin 11) -> 1-10 kOhm -> jack tip; GND (pin 6) -> jack sleeve;
ring unconnected. Lead colours of plug cables vary: measure them (`docs/SETUP.md` section 2).

## Docs

| File | Content |
|------|---------|
| `docs/SETUP.md` | the full procedure, values and gotchas |
| `docs/jack-measurement.md` | measuring the DSC jack, raw results |
| `docs/edgetx-setup.md` | EdgeTX settings, Pocket-specific findings, kill switch |
| `docs/parts-and-wiring.md` | parts and wiring |
| `AGENTS.md` | notes for an AI assistant continuing this work |

## Output backends

- `print`: prints channel values when they change (dry run).
- `lgpio`: software-timed PPM in a separate process (SCHED_FIFO if permitted). Tested against the
  Pocket; jitter not measured. Hands the pin back as input on exit.
- `pio`: PIO on the RP1 through `native/ppm_pio` (C, piolib). Built by `setup-pi.sh`, never run on a
  Pi; `--pio-hz` (default 200 MHz) is an assumption to verify.

## Tools

- `ppmcheck [--active-low] capture.csv`: analyse an edge CSV (time_seconds,level).
- `scripts/capture_gpio.py`: record a Pi GPIO as such a CSV (input only).
- `scripts/read_joy_windows.py`: read the Pocket as USB joystick on Windows.

## Tests

    .venv/bin/python -m pytest
    sudo .venv/bin/python -m pytest tests/test_calibrate_uinput.py   # on the Pi: end-to-end calibration
