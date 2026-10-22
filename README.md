# joystick-trainer

> **Neu hier und keine Ahnung von GitHub oder Programmieren?** Lies
> **[docs/ANLEITUNG.md](docs/ANLEITUNG.md)**: was das ist, was du kaufen musst und wie du es Schritt
> für Schritt aufbaust (Deutsch, ohne Vorkenntnisse).

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
| `docs/ANLEITUNG.md` | beginner guide in German, no prior knowledge needed |
| `docs/PYGAME.md` | add-on guide (German): read the joystick through pygame instead of evdev |
| `docs/DISPLAY.md` | add-on guide (German): live channel bars on a Raspberry Pi Touch Display 2 |
| `docs/SETUP.md` | the full procedure, values and gotchas |
| `docs/jack-measurement.md` | measuring the DSC jack, raw results |
| `docs/edgetx-setup.md` | EdgeTX settings, Pocket-specific findings, kill switch |
| `docs/parts-and-wiring.md` | parts and wiring |
| `AGENTS.md` | notes for an AI assistant continuing this work |

## Input backends

- `evdev` (default): reads `/dev/input` directly. Tested end to end.
- `pygame`: `input: pygame` in the config, controls named `AXIS_<n>`/`BUTTON_<n>`. Install with
  `.venv/bin/pip install -e ".[pygame]"`, calibrate with `--input pygame`. Detection and reading
  verified on the Pi with the Hotas X; calibration and sending through it not yet. See `docs/PYGAME.md`.

## Output backends

- `print`: prints channel values when they change (dry run).
- `lgpio`: software-timed PPM in a separate process (SCHED_FIFO if permitted). Tested against the
  Pocket; jitter not measured. Hands the pin back as input on exit.
- `pio`: PIO on the RP1 through `native/ppm_pio` (C, piolib). Built by `setup-pi.sh`, never run on a
  Pi; `--pio-hz` (default 200 MHz) is an assumption to verify.

## Channel display

`joystick-trainer-display` (pygame, needs a desktop session) shows one bar per channel and the state
(sending / stopped / no data). The trainer sends its current channels as JSON over UDP to
127.0.0.1:5600 at 20 Hz, fire and forget (`display:` in the config, `enabled: false` to turn it off).
Rendering verified headless for 8 and 16 channels; not yet run on a real Touch Display 2. With the
display powered from pins 2/6, the trainer cable's GND moves to pin 9. See `docs/DISPLAY.md`.

Channel count: `channels:` (default 8). It must fit the frame: `channels * 2000 + 3000 <= frame_us`,
so at most 9 at 22.5 ms, 16 needs 35 ms. Checked when the config is loaded.

## Tools

- `ppmcheck [--active-low] capture.csv`: analyse an edge CSV (time_seconds,level).
- `scripts/capture_gpio.py`: record a Pi GPIO as such a CSV (input only).
- `scripts/read_joy_windows.py`: read the Pocket as USB joystick on Windows.

## Tests

    .venv/bin/python -m pytest
    sudo .venv/bin/python -m pytest tests/test_calibrate_uinput.py   # on the Pi: end-to-end calibration
