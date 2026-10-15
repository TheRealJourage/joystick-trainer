# Measuring the Pocket DSC jack

Firmware (EdgeTX `radio/src/boards/hw_defs/pocket.json`): trainer in = PC8, out = PC9,
detect = PA8 (inverted, low when plugged). Which jack contact maps to which pin is not in the
firmware. Measure before connecting the Pi.

Tools: multimeter, 3.5 mm plug or cable with open ends, optional logic analyzer.

1. Radio off: continuity between plug sleeve and the USB-C shell. Continuity = GND.
2. Model Setup > Trainer = Slave/Jack, plug in. Measure DC voltage of tip and ring against GND.
   The contact carrying PPM should read a fluctuating level; a logic analyzer shows 8-22 ms frames.
3. Trainer = Master/Jack. Check which contact idles at a defined level.
4. Note which contact changes when the plug is inserted (detect).
5. Record: tip, ring, sleeve roles, voltage level, 3 or 4 poles, EdgeTX version, trainer modes offered.

## Result (2026-10-15, our Pocket)

Measured through a 3.5 mm TRS plug (3-pole) with open leads. Lead colours of that cable, verified by
continuity: red = tip, white = ring, black = sleeve.

| Contact | Role | Evidence |
|---------|------|----------|
| Sleeve | GND | continuity to the USB-C shell, radio off |
| Tip | PPM, both directions | Slave/Jack: PPM captured (below). Master/Jack: idles at 0 V (input) |
| Ring | unknown, not needed | ~3.25 V steady in Slave/Jack and Master/Jack, ~2.8 V with trainer off |

DC voltages against GND (multimeter):

| Trainer mode | Tip | Ring |
|--------------|-----|------|
| off | 2.8 V | 2.8 V |
| Slave/Jack | 2.8 V (mean of the PPM signal) | 3.25 V |
| Master/Jack | 0 V | 3.25 V |

Levels stay below 3.3 V: 3.3 V logic, compatible with the Pi GPIO without level shifting.

Capture of Slave/Jack output: tip -> 1.1 or 5.1 kOhm series resistor -> Pi GPIO17 (input, no pull),
edges via lgpio alerts, `ppmcheck --active-low docs/captures/pocket-slave-20261015.csv`:

    frames: 134 (132 complete), channels: 8
    pulse: 299.8 us (stdev 0.2)
    frame: 22505 us (stdev 0.3)

The line idles high and the 300 us pulses go low, i.e. negative polarity, which matches the "-" in
the Pocket's PPM frame setting. For the Pi: `active_high: false`, `pulse_us: 300`, `frame_us: 22500`.

Radio: EdgeTX, Trainer mode was hidden until Model Setup > Enabled Features > Trainer was set to On.
Modes used: Off, Master/Jack, Slave/Jack (full list not recorded). EdgeTX version not recorded.

Detect: with a 3-pole plug only tip, ring and sleeve are reachable; the detect contact was not
identified. The Pocket (Master/Jack) showed "Trainer signal lost" once while the Pi was being
power-cycled with the tip connected; cause not verified.

Not yet tested: Pi -> Pocket (Master/Jack).
