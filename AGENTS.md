# Notes for an AI assistant working on this repo

You are helping someone rebuild or extend: USB joystick -> Raspberry Pi 5 -> PPM into the DSC jack of
a RadioMaster Pocket (EdgeTX) -> model. The person does the physical work (wiring, switches,
measuring); you run commands on the Pi and read the results.

## Start here

1. Read `docs/SETUP.md` completely. It is the procedure, in order, with the measured values.
2. Ask where they are in it (new hardware? same Pocket? already wired?) and continue from that
   section. Do not skip its checks.
3. Known open items are in `docs/SETUP.md` section 11. Don't present the setup as flight-ready.

## Repo map

| Path | What |
|------|------|
| `src/joystick_trainer/cli.py` | `joystick-trainer config.yaml`: main loop, joystick -> mapper -> sink |
| `src/joystick_trainer/calibrate.py` | `joystick-trainer-calibrate`: interactive axis/direction/button detection, writes config |
| `src/joystick_trainer/mapper.py` | axis/button -> channel us (deadzone, expo, invert, unipolar, toggle) |
| `src/joystick_trainer/sinks.py` | `print`, `lgpio` (software PPM, tested), `pio` (RP1 PIO helper, never run on a Pi) |
| `src/joystick_trainer/ppm.py`, `ppmcheck.py` | PPM frame generation; analysis of a captured edge CSV |
| `native/ppm_pio.c` | PIO helper, built by `setup-pi.sh` against the repo-local piolib |
| `scripts/setup-pi.sh`, `uninstall-pi.sh` | reversible Pi install (`.install-state` lists every change) |
| `scripts/capture_gpio.py` | record a GPIO as edge CSV (input only) - used to prove the radio's PPM |
| `scripts/read_joy_windows.py` | read the Pocket as USB joystick on Windows (winmm, no install) |
| `config.hotas-x.yaml` | verified config for the Thrustmaster T.Flight Hotas X |
| `docs/jack-measurement.md` | how the jack was measured, raw voltages, capture result |
| `docs/edgetx-setup.md` | EdgeTX settings, Pocket-specific findings, kill switch |
| `docs/captures/` | raw captures referenced by the docs |
| `tests/` | pytest; `test_calibrate_uinput.py` needs `/dev/uinput` (sudo on the Pi) |

## How to work with the person

- Physical actions: say exactly what to do, then **wait** until they confirm before you run anything
  that depends on it. Don't start timed recordings and hope they move in time; prefer "hold this
  position, press Enter / tell me", as the calibration does.
- Once a mapping is known (e.g. lead colours), give instructions in their terms ("measure red
  against black"), not in jargon they then have to translate.
- Report numbers, not impressions. When something does not match, say so and say what would prove
  it; label guesses as guesses.
- The person may speak German; answer in their language. Code, comments and docs here are English.

## Hard rules

- No GPIO output (`sink: lgpio`/`pio`) towards a jack that is not measured. Measurement first
  (`docs/jack-measurement.md`), and the Pi only through a series resistor.
- Test model with Internal and External RF Off until everything in `docs/SETUP.md` section 9 passes
  and section 11 is done.
- After any run that drove the pin, check `pinctrl get 17` shows `ip` (input).
- Keep `setup-pi.sh` reversible: anything it changes outside the repo must be recorded in
  `.install-state` and undone by `uninstall-pi.sh`. Re-test install -> uninstall against a baseline
  (dpkg list, `/usr/local`, groups, linger, user units) after changing either script.
- Run `.venv/bin/python -m pytest` before committing; on the Pi also the uinput test with sudo.
