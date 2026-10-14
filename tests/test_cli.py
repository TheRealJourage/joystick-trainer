import pytest

from joystick_trainer import cli
from joystick_trainer.mapper import AxisMap, Mapping
from joystick_trainer.state import JoystickState


class FakeSink:
    def __init__(self):
        self.calls = []

    def set_channels(self, channels):
        self.calls.append(("set", list(channels)))

    def stop(self):
        self.calls.append(("stop",))


class FakeJoystick:
    def __init__(self, *_):
        self.state = JoystickState()
        self.state.set_axis("ABS_X", 100, -100, 100)
        self.lost = False
        self.polls = 0

    def poll(self, timeout):
        self.polls += 1
        if self.polls == 2:
            self.lost = True

    def close(self):
        pass


class StopLoop(Exception):
    pass


def test_lost_joystick_stops_output(monkeypatch):
    sink = FakeSink()
    cfg = {"device": "x", "mapping": Mapping(axes=[AxisMap("ABS_X", 1)]), "on_lost": "stop", "rate_hz": 1000}

    def failing_connect(*_):
        if any(c[0] == "stop" for c in sink.calls):
            raise StopLoop
        return FakeJoystick()

    with pytest.raises(StopLoop):
        cli.run(cfg, sink, connect=failing_connect)
    assert sink.calls[0] == ("set", [2000] + [1500] * 7)
    assert sink.calls[-1] == ("stop",)
