import os
import types

from evdev import AbsInfo, ecodes

from joystick_trainer import joystick as joystick_module
from joystick_trainer.cli import Mapper
from joystick_trainer.config import load


class FakeDevice:
    """Hotas X as it is right after plugging in: every axis reads 0 until it is first moved."""

    def __init__(self):
        self.name = "Thrustmaster T.Flight Hotas X"
        self._read_fd, self._write_fd = os.pipe()
        self.fd = self._read_fd
        self.pending = []

    def capabilities(self):
        info = lambda hi: AbsInfo(value=0, min=0, max=hi, fuzz=0, flat=0, resolution=0)
        return {ecodes.EV_ABS: [(ecodes.ABS_X, info(1023)), (ecodes.ABS_Y, info(1023)),
                                (ecodes.ABS_Z, info(255)), (ecodes.ABS_RZ, info(255))]}

    def send(self, code, value):
        self.pending.append(types.SimpleNamespace(type=ecodes.EV_ABS, code=code, value=value))
        os.write(self._write_fd, b"x")

    def read(self):
        os.read(self._read_fd, 4096)
        events, self.pending = self.pending, []
        return events

    def close(self):
        os.close(self._read_fd)
        os.close(self._write_fd)


def test_hotas_does_not_start_at_full_throttle(monkeypatch):
    device = FakeDevice()
    monkeypatch.setattr(joystick_module, "find_device", lambda selector: device)
    cfg = load(os.path.join(os.path.dirname(__file__), "..", "config.hotas-x.yaml"))
    mapping = cfg["mapping"]
    stick = joystick_module.Joystick(cfg["device"], [a.source for a in mapping.axes], [b.source for b in mapping.buttons])
    mapper = Mapper(mapping)
    assert mapper.channels(stick.state)[:4] == [1500, 1500, 1000, 1500]
    device.send(ecodes.ABS_Z, 255)          # throttle moved back to idle: Hotas X idle is raw 255
    stick.poll(0.1)
    assert mapper.channels(stick.state)[:4] == [1500, 1500, 1000, 1500]
    device.send(ecodes.ABS_Z, 0)            # full forward
    stick.poll(0.1)
    assert mapper.channels(stick.state)[2] == 2000
    stick.close()
