#!/usr/bin/env python3
"""Record level changes on one Pi GPIO as a ppmcheck CSV (time_seconds,level). Input only, no pull:
safe to attach to a radio's trainer output through a series resistor, as long as it stays <= 3.3 V.

    .venv/bin/python scripts/capture_gpio.py --pin 17 --seconds 3 capture.csv
    .venv/bin/ppmcheck --active-low capture.csv
"""
import argparse
import time

import lgpio


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--pin", type=int, default=17, help="BCM number (17 = header pin 11)")
    parser.add_argument("--chip", type=int, default=0, help="gpiochip of the 40-pin header (gpiodetect)")
    parser.add_argument("--seconds", type=float, default=3.0)
    args = parser.parse_args()

    handle = lgpio.gpiochip_open(args.chip)
    edges = []
    try:
        lgpio.gpio_claim_alert(handle, args.pin, lgpio.BOTH_EDGES, lgpio.SET_PULL_NONE)
        start_level = lgpio.gpio_read(handle, args.pin)
        callback = lgpio.callback(handle, args.pin, lgpio.BOTH_EDGES,
                                  lambda chip, gpio, level, tick: edges.append((tick, level)))
        time.sleep(args.seconds)
        callback.cancel()
    finally:
        lgpio.gpio_free(handle, args.pin)
        lgpio.gpiochip_close(handle)

    print(f"start level {start_level}, {len(edges)} edges in {args.seconds:g} s")
    if not edges:
        print("no edges: nothing is sending (radio not in Slave/Jack, wrong pin or contact?)")
        return
    first = edges[0][0]
    with open(args.out, "w") as handle:
        handle.write("time_seconds,level\n")
        for tick, level in edges:
            handle.write(f"{(tick - first) / 1e9:.9f},{level}\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
