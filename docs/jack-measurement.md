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
