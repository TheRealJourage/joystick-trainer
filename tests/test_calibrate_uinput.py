"""End-to-end: the real calibrate CLI against a virtual joystick with the Hotas X ranges.
Needs write access to /dev/uinput (on the Pi: sudo .venv/bin/python -m pytest tests/test_calibrate_uinput.py)."""

import os
import subprocess
import sys
import time

import pytest

from joystick_trainer import config

pytestmark = pytest.mark.skipif(not os.access("/dev/uinput", os.W_OK), reason="needs /dev/uinput")

NAME = "JT Fake Hotas"


@pytest.fixture
def fake():
    from evdev import AbsInfo, UInput, ecodes as e

    caps = {
        e.EV_ABS: [(e.ABS_X, AbsInfo(512, 0, 1023, 0, 63, 0)), (e.ABS_Y, AbsInfo(512, 0, 1023, 0, 63, 0)),
                   (e.ABS_Z, AbsInfo(255, 0, 255, 0, 15, 0)), (e.ABS_RZ, AbsInfo(128, 0, 255, 0, 15, 0)),
                   (e.ABS_THROTTLE, AbsInfo(128, 0, 255, 0, 15, 0)), (e.ABS_HAT0X, AbsInfo(0, -1, 1, 0, 0, 0))],
        e.EV_KEY: [e.BTN_TRIGGER, e.BTN_THUMB],
    }
    device = UInput(caps, name=NAME)
    time.sleep(0.5)
    yield device, e
    device.close()


def set_axes(device, e, **values):
    for name, value in values.items():
        device.write(e.EV_ABS, getattr(e, name), value)
    device.syn()


def read_prompt(process):
    text = b""
    while not text.endswith(b"skip] "):
        char = process.stdout.read(1)
        if not char:
            raise AssertionError(f"calibrate exited early: {text.decode()}")
        text += char
    return text.decode()


def test_calibrate_cli_on_virtual_hotas(fake, tmp_path):
    device, e = fake
    out = tmp_path / "config.yaml"
    process = subprocess.Popen([sys.executable, "-m", "joystick_trainer.calibrate", str(out), "--device", NAME],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    centre = dict(ABS_X=512, ABS_Y=512, ABS_Z=255, ABS_RZ=128)
    held = {"RIGHT.": dict(ABS_X=1023), "FORWARD (away": dict(ABS_Y=0), "FORWARD (full": dict(ABS_Z=0),
            "Twist": dict(ABS_RZ=255)}
    for _ in range(10):
        prompt = read_prompt(process)
        set_axes(device, e, **centre)
        device.write(e.EV_KEY, e.BTN_TRIGGER, 0)
        device.syn()
        for marker, values in held.items():
            if marker in prompt and "Centre" not in prompt:
                set_axes(device, e, **values)
        if "HOLD the button" in prompt:
            device.write(e.EV_KEY, e.BTN_TRIGGER, 1)
            device.syn()
        time.sleep(0.1)
        process.stdin.write(b"\n")
        process.stdin.flush()
    output = process.communicate(timeout=10)[0].decode()
    assert process.returncode == 0, output
    cfg = config.load(out)
    axes = {a.source: a for a in cfg["mapping"].axes}
    assert [(a.source, a.channel, a.invert, a.unipolar) for a in cfg["mapping"].axes] == [
        ("ABS_X", 1, False, False), ("ABS_Y", 2, True, False), ("ABS_Z", 3, True, True), ("ABS_RZ", 4, False, False)]
    assert axes["ABS_X"].expo == 0.2
    assert [(b.source, b.channel, b.toggle) for b in cfg["mapping"].buttons] == [("BTN_TRIGGER", 5, True)]
    assert cfg["device"] == NAME
