"""Interactive calibration: finds which axis/button is which control, its direction and reach,
and writes a config.yaml. Works on positions the user holds and confirms with Enter, not on timed
windows, so slow or partial movements cannot be misread."""

import argparse
import os
import sys
from dataclasses import dataclass

MIN_DELTA = 0.3        # an axis must move at least 30 % of its range to count
AMBIGUOUS_RATIO = 0.5  # a second axis moving more than half as much as the first = unclear
LOW_REACH = 0.9        # warn if the held position reaches less than 90 % of the way to the end


@dataclass
class Step:
    role: str
    channel: int
    kind: str          # stick | throttle | button
    rest_prompt: str
    hold_prompt: str


STEPS = [
    Step("roll", 1, "stick", "Centre the stick and let go.", "Hold the stick fully to the RIGHT."),
    Step("pitch", 2, "stick", "Centre the stick and let go.", "Push the stick fully FORWARD (away from you) and hold."),
    Step("throttle", 3, "throttle", "Pull the throttle fully back to IDLE.", "Push the throttle fully FORWARD (full power) and hold."),
    Step("yaw", 4, "stick", "Centre the stick (twist) and let go.", "Twist the stick fully to the RIGHT and hold."),
    Step("arm", 5, "button", "Release all buttons.", "Press and HOLD the button you want as ARM."),
]


@dataclass
class AxisPick:
    code: int
    invert: bool
    reach: float
    off_centre: float
    warnings: list


class CalibrationError(Exception):
    pass


def pick_axis(rest, held, ranges, exclude=(), kind="stick"):
    """rest/held: {code: raw value}; ranges: {code: (min, max)}. The control was commanded towards
    the + direction (right/forward/full), so an axis that went down needs invert."""
    deltas = {}
    for code, (lo, hi) in ranges.items():
        if code in exclude or hi - lo <= 2:      # hats are -1..1, never a main control
            continue
        deltas[code] = (held[code] - rest[code]) / (hi - lo)
    ranked = sorted(deltas, key=lambda c: abs(deltas[c]), reverse=True)
    if not ranked or abs(deltas[ranked[0]]) < MIN_DELTA:
        raise CalibrationError("no axis moved enough - move it all the way and hold it there")
    best = ranked[0]
    if len(ranked) > 1 and abs(deltas[ranked[1]]) > AMBIGUOUS_RATIO * abs(deltas[best]):
        raise CalibrationError("two axes moved - move only this one control")
    lo, hi = ranges[best]
    delta = deltas[best]
    warnings = []
    if kind == "throttle":
        reach = abs(delta)
        off_centre = 0.0
    else:
        span = (hi - rest[best]) if delta > 0 else (rest[best] - lo)
        reach = abs(held[best] - rest[best]) / span if span else 0.0
        mid = (lo + hi) / 2
        off_centre = abs(rest[best] - mid) / ((hi - lo) / 2)
        if off_centre > 0.1:
            warnings.append(f"rest position is {off_centre:.0%} off centre")
    if reach < LOW_REACH:
        warnings.append(f"held position reached only {reach:.0%} of the travel")
    return AxisPick(best, delta < 0, reach, off_centre, warnings)


def pick_button(rest_keys, held_keys, exclude=()):
    new = set(held_keys) - set(rest_keys) - set(exclude)
    if len(new) != 1:
        raise CalibrationError(f"expected exactly one newly pressed button, got {len(new)}")
    return new.pop()


# evdev lists group aliases first (288 = BTN_JOYSTICK and BTN_TRIGGER); the specific name reads better.
GROUP_ALIASES = {"BTN_JOYSTICK", "BTN_GAMEPAD", "BTN_MISC", "BTN_MOUSE", "BTN_DIGI", "BTN_WHEEL"}


def code_name(table, code):
    name = table[code]
    if isinstance(name, str):
        return name
    specific = [n for n in name if n not in GROUP_ALIASES]
    return (specific or name)[0]


def render_config(device_name, axes, buttons, output="print", input_source="evdev"):
    """axes: [(role, channel, name, invert, unipolar)], buttons: [(role, channel, name)]."""
    expo = {"roll": 0.2, "pitch": 0.2}
    lines = [
        "# Written by joystick-trainer-calibrate. Re-run it instead of editing the mapping by hand.",
        f'device: "{device_name}"',
    ]
    if input_source == "pygame":
        lines.append("input: pygame             # read the joystick through pygame/SDL instead of evdev")
    lines += [
        "channels: 8",
        "rate_hz: 50",
        "on_lost: stop             # stop = emit no PPM; neutral = emit defaults_us",
        "output:",
    ]
    if output == "lgpio":
        lines += [
            "  sink: lgpio             # values measured on the RadioMaster Pocket, docs/jack-measurement.md",
            "  pin: 17                 # BCM 17 = header pin 11, through the series resistor to the jack tip",
            "  chip: 0                 # Pi 5 header gpiochip on current kernels; check with gpiodetect",
            "  pulse_us: 300",
            "  frame_us: 22500",
            "  active_high: false      # Pocket PPM idles high, pulses go low",
        ]
    else:
        lines += [
            "  sink: print             # dry run; see docs/SETUP.md for lgpio",
            "  # pin: 17",
            "  # chip: 0",
            "  # pulse_us: 300",
            "  # frame_us: 22500",
            "  # active_high: false",
        ]
    lines += ["defaults_us:", "  3: 1000                 # throttle low before the throttle axis reports", "axes:"]
    for role, channel, name, invert, unipolar in axes:
        fields = [f"source: {name}", f"channel: {channel}"]
        if role in expo:
            fields.append(f"expo: {expo[role]}")
        if unipolar:
            fields.append("unipolar: true")
        if invert:
            fields.append("invert: true")
        lines.append(f"  - {{{', '.join(fields)}}}  # {role}")
    lines.append("buttons:" if buttons else "buttons: []")
    for role, channel, name in buttons:
        lines.append(f"  - {{source: {name}, channel: {channel}, toggle: true}}  # {role}: each press flips it, starts off")
    return "\n".join(lines) + "\n"


class Wizard:
    """Runs the steps against a device given as snapshot functions, so tests can drive it."""

    def __init__(self, ranges, read_axes, read_keys, axis_names, key_names, ask=input, say=print):
        self.ranges = ranges
        self.read_axes = read_axes
        self.read_keys = read_keys
        self.axis_names = axis_names
        self.key_names = key_names
        self.ask = ask
        self.say = say

    def _confirm(self, prompt):
        answer = self.ask(f"  {prompt}  [Enter = ok, s = skip] ").strip().lower()
        return answer != "s"

    def run(self, steps=STEPS):
        axes, buttons, used_axes, used_keys = [], [], set(), set()
        for step in steps:
            self.say(f"\n[{step.role}] -> channel {step.channel}")
            while True:
                if not self._confirm(step.rest_prompt):
                    self.say("  skipped")
                    break
                rest = self.read_axes() if step.kind != "button" else self.read_keys()
                if not self._confirm(step.hold_prompt):
                    self.say("  skipped")
                    break
                held = self.read_axes() if step.kind != "button" else self.read_keys()
                try:
                    if step.kind == "button":
                        code = pick_button(rest, held, used_keys)
                        used_keys.add(code)
                        name = self.key_names(code)
                        buttons.append((step.role, step.channel, name))
                        self.say(f"  ok: {name}")
                    else:
                        pick = pick_axis(rest, held, self.ranges, used_axes, step.kind)
                        used_axes.add(pick.code)
                        name = self.axis_names(pick.code)
                        axes.append((step.role, step.channel, name, pick.invert, step.kind == "throttle"))
                        self.say(f"  ok: {name}{' (inverted)' if pick.invert else ''}, reach {pick.reach:.0%}")
                        for warning in pick.warnings:
                            self.say(f"  warning: {warning}")
                    break
                except CalibrationError as error:
                    self.say(f"  not recognised: {error}. Again.")
        return axes, buttons


def find_joysticks():
    from evdev import InputDevice, ecodes, list_devices

    found = []
    for path in list_devices():
        device = InputDevice(path)
        caps = device.capabilities()
        abs_codes = [c for c, _ in caps.get(ecodes.EV_ABS, [])]
        if ecodes.ABS_X in abs_codes and ecodes.EV_KEY in caps:
            found.append(device)
        else:
            device.close()
    return found


def evdev_device(selector):
    from evdev import ecodes

    from .joystick import find_device

    if selector:
        device = find_device(selector)
    else:
        candidates = find_joysticks()
        if len(candidates) != 1:
            names = ", ".join(f"{d.path} {d.name!r}" for d in candidates) or "none"
            sys.exit(f"found {len(candidates)} joysticks ({names}); pick one with --device")
        device = candidates[0]
    absinfo = dict(device.capabilities().get(ecodes.EV_ABS, []))
    ranges = {code: (info.min, info.max) for code, info in absinfo.items()}
    return device.name, Wizard(
        ranges=ranges,
        read_axes=lambda: {code: device.absinfo(code).value for code in ranges},
        read_keys=lambda: set(device.active_keys()),
        axis_names=lambda code: code_name(ecodes.ABS, code),
        key_names=lambda code: code_name(ecodes.BTN, code) if code in ecodes.BTN else code_name(ecodes.KEY, code),
    )


def pygame_device(selector):
    from . import pygame_input

    if selector:
        device = pygame_input.find_joystick(selector)
    else:
        candidates = pygame_input.list_joysticks()
        if len(candidates) != 1:
            names = ", ".join(repr(d.get_name()) for d in candidates) or "none"
            sys.exit(f"found {len(candidates)} joysticks ({names}); pick one with --device")
        device = candidates[0]
    import pygame

    def read_axes():
        pygame.event.get()   # SDL updates the joystick state while it processes its event queue
        return {i: pygame_input.read_axis(device, i) for i in range(device.get_numaxes())}

    def read_keys():
        pygame.event.get()
        return {i for i in range(device.get_numbuttons()) if device.get_button(i)}

    scale = pygame_input.AXIS_SCALE
    return device.get_name(), Wizard(
        ranges={i: (-scale, scale) for i in range(device.get_numaxes())},
        read_axes=read_axes,
        read_keys=read_keys,
        axis_names=lambda i: f"AXIS_{i}",
        key_names=lambda i: f"BUTTON_{i}",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="joystick-trainer-calibrate",
                                     description="Detect axes, directions and the arm button; write a config.")
    parser.add_argument("out", help="config file to write, e.g. config.yaml")
    parser.add_argument("--device", help="name substring or /dev/input/eventN (default: the only joystick)")
    parser.add_argument("--output", choices=["print", "lgpio"], default="print",
                        help="print = dry run (default); lgpio = measured Pocket values, GPIO17")
    parser.add_argument("--input", choices=["evdev", "pygame"], default="evdev",
                        help="how to read the joystick: evdev (default, tested) or pygame (pip install pygame)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = parser.parse_args(argv)

    if os.path.exists(args.out) and not args.force:
        sys.exit(f"{args.out} exists; use --force to overwrite")

    open_device = pygame_device if args.input == "pygame" else evdev_device
    name, wizard = open_device(args.device)
    print(f"Calibrating {name!r}. Answer each prompt once the control is in place.")
    axes, buttons = wizard.run()
    text = render_config(name, axes, buttons, args.output, args.input)
    with open(args.out, "w") as handle:
        handle.write(text)
    print(f"\nwrote {args.out}:\n\n{text}")
    print("Next: dry run with `joystick-trainer " + args.out + "` (sink: print) and check every channel.")


if __name__ == "__main__":
    main()
