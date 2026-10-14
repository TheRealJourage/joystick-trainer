# joystick-trainer

USB joystick on a Raspberry Pi 5 -> PPM on the trainer jack (DSC) of a RadioMaster Pocket
(EdgeTX, Trainer = Master/Jack) -> the radio's own ELRS link to the aircraft.

Status: core software only. Not yet run against a real radio. The jack pinout of the Pocket is
unmeasured (see docs/jack-measurement.md); do not connect the Pi to the jack before it is.

## Run (dry run, no GPIO)

    python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
    cp config.example.yaml config.yaml    # set device and axes
    .venv/bin/joystick-trainer config.yaml

Find axis and button names with `.venv/bin/python -m evdev.evtest`.

## Output backends

- `print`: prints channel values, for development.
- `lgpio`: software-timed PPM in a separate process (SCHED_FIFO if permitted). Bring-up backend;
  jitter not measured. Needs `pip install '.[pi]'` on the Pi.
- `pio`: PIO on the RP1 through `native/ppm_pio` (C, piolib). Compiles against piolib on x86; never run
  on a Pi. `--pio-hz` (default 200 MHz) is an assumption to verify.

## Docs

- `docs/jack-measurement.md`: measure the Pocket DSC jack at home.
- `docs/edgetx-setup.md`: trainer settings on the Pocket.
- `docs/parts-and-wiring.md`: parts and planned wiring.
- `scripts/setup-pi.sh`: one-shot Pi setup (untested).
- `ppmcheck capture.csv`: analyse a logic-analyzer export (time_seconds,level).

## Safety

`on_lost: stop` emits no PPM when the joystick disappears. What the Pocket then does with a
missing trainer signal is not verified; test with props off and no battery.

## Tests

    .venv/bin/python -m pytest
