# Parts and wiring

Wiring depends on the jack measurement (docs/jack-measurement.md). Do not connect before it.

## Parts

| Part | Why | Note |
|------|-----|------|
| 3.5 mm plug breakout, TRS and TRRS | Jack plug with screw terminals | Buy both until the Pocket jack is measured; TX16S reports mention a 4-pole plug |
| Resistor ~1 kOhm | In series with the signal pin | Limits current if pins are mismatched. Value is a protective guess |
| Jumper wires, breadboard | Pi to plug | |
| USB logic analyzer (8 channel) | Verify the PPM before the radio sees it | Works with `ppmcheck` through a CSV export |
| Multimeter | Jack measurement | |
| Pi 5 power supply | Official 27 W type | Brown-outs make PPM drop out |

## Connection (planned)

    Pi GPIO (BCM, default 18) --[ 1 kOhm ]--> jack contact carrying PPM
    Pi GND ---------------------------------> jack sleeve (GND)

- Common ground is required.
- The Pi outputs 3.3 V. The Pocket's input level tolerance is not confirmed.
- If the detect contact needs to be pulled for the Pocket to accept the plug, that goes
  into this file after the measurement.
- PIO pins are GPIO0 to GPIO27 on the 40-pin header.

## Order of work

1. Dry run on the Pi (`sink: print`), joystick axes verified.
2. `sink: pio`, signal on a logic analyzer only, `ppmcheck` on the capture.
3. Jack measured, then connect with the resistor, Trainer = Master/Jack, check the channel monitor.
4. Props off, no battery: kill switch and signal-loss tests (docs/edgetx-setup.md, section 4).
