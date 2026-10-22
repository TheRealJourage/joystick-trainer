import os
import signal
import sys
import time
import types

import pytest

from joystick_trainer import cli
from joystick_trainer.sinks import LgpioSink


@pytest.fixture
def fake_lgpio(tmp_path, monkeypatch):
    """Stand-in for lgpio that logs calls to a file, so the forked output process can report them."""
    log = tmp_path / "lgpio.log"
    module = types.ModuleType("lgpio")

    def recorder(name):
        def call(*args, **_):
            with open(log, "a") as f:
                f.write(f"{name} {' '.join(map(str, args))}\n")
            return 7 if name == "gpiochip_open" else 0
        return call

    for name in ("gpiochip_open", "gpio_claim_output", "gpio_write", "gpio_claim_input", "gpiochip_close"):
        setattr(module, name, recorder(name))
    monkeypatch.setitem(sys.modules, "lgpio", module)
    return log


def calls(log):
    return [line.split() for line in log.read_text().splitlines()]


def wait_for(log, name, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if log.exists() and any(c[0] == name for c in calls(log)):
            return
        time.sleep(0.01)
    raise AssertionError(f"{name} never called")


@pytest.mark.parametrize("ending", ["close", "sigterm"])
def test_lgpio_sink_hands_pin_back_as_input(fake_lgpio, ending):
    sink = LgpioSink(pin=17, chip=0, active_high=False)
    sink.set_channels([1500] * 8)
    wait_for(fake_lgpio, "gpio_claim_output")
    time.sleep(0.05)
    if ending == "close":
        sink.close()
    else:
        os.kill(sink._process.pid, signal.SIGTERM)
        sink._process.join(2)
    tail = calls(fake_lgpio)[-3:]
    assert tail == [["gpio_write", "7", "17", "1"], ["gpio_claim_input", "7", "17"], ["gpiochip_close", "7"]]


def test_main_closes_sink_on_sigterm(monkeypatch, tmp_path):
    closed = []

    class Sink:
        def close(self):
            closed.append(True)

    def run(cfg, sink, connect):
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(1)

    monkeypatch.setattr(cli.config_module, "load", lambda path: {"output": {}, "input": "evdev"})
    monkeypatch.setattr(cli, "make_sink", lambda output: Sink())
    monkeypatch.setattr(cli, "run", run)
    monkeypatch.setattr(sys, "argv", ["joystick-trainer", "config.yaml"])
    previous = signal.getsignal(signal.SIGTERM)
    try:
        with pytest.raises(SystemExit):
            cli.main()
    finally:
        signal.signal(signal.SIGTERM, previous)
    assert closed == [True]
