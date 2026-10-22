import json
import os
import socket

import pytest

from joystick_trainer import cli, config, display, sinks
from joystick_trainer.mapper import AxisMap, Mapping
from joystick_trainer.status import StatusPublisher


def write_config(tmp_path, text):
    path = tmp_path / "c.yaml"
    path.write_text('device: "x"\n' + text)
    return path


def test_channel_count_is_checked_against_the_frame_at_load(tmp_path):
    assert config.load(write_config(tmp_path, "channels: 9\n"))["mapping"].channel_count == 9
    with pytest.raises(ValueError, match="fits at most 9"):
        config.load(write_config(tmp_path, "channels: 10\n"))
    sixteen = config.load(write_config(tmp_path, "channels: 16\noutput: {frame_us: 35000}\n"))
    assert sixteen["mapping"].channel_count == 16


def test_display_defaults_to_localhost(tmp_path):
    cfg = config.load(write_config(tmp_path, ""))
    assert cfg["display"] == {"enabled": True, "host": "127.0.0.1", "port": 5600}
    cfg = config.load(write_config(tmp_path, "display: {enabled: false}\n"))
    assert cfg["display"]["enabled"] is False


def test_sink_gets_the_configured_channel_count(monkeypatch):
    seen = {}
    monkeypatch.setattr(sinks, "LgpioSink", lambda **kw: seen.update(kw))
    sinks.make_sink({"sink": "lgpio", "pin": 17}, 9)
    assert seen == {"pin": 17, "channels": 9}


@pytest.fixture
def receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.settimeout(1)
    yield sock
    sock.close()


def test_publisher_sends_json_and_limits_the_rate(receiver):
    now = [0.0]
    publisher = StatusPublisher(port=receiver.getsockname()[1], rate_hz=20, clock=lambda: now[0])
    publisher.publish(True, [1500] * 8, True)
    publisher.publish(True, [2000] * 8, True)     # same instant: dropped
    now[0] = 0.06
    publisher.publish(False, [1000] * 8, False)
    first = json.loads(receiver.recv(4096))
    second = json.loads(receiver.recv(4096))
    assert first == {"sending": True, "joystick": True, "channels": [1500] * 8, "frame_us": 22500}
    assert second["sending"] is False and second["channels"] == [1000] * 8


def test_publisher_without_listener_never_raises():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    publisher = StatusPublisher(port=port, clock=iter(range(100)).__next__)
    for _ in range(5):
        publisher.publish(True, [1500] * 8, True)


class Recorder:
    def __init__(self):
        self.calls = []

    def publish(self, sending, channels, joystick):
        self.calls.append((sending, list(channels), joystick))


class StopLoop(Exception):
    pass


def test_main_loop_reports_sending_then_stopped():
    from test_cli import FakeSink, FakeJoystick

    sink, status = FakeSink(), Recorder()
    cfg = {"device": "x", "mapping": Mapping(axes=[AxisMap("ABS_X", 1)]), "on_lost": "stop", "rate_hz": 1000}

    def connect(*_):
        if any(c[0] == "stop" for c in sink.calls):
            raise StopLoop
        return FakeJoystick()

    with pytest.raises(StopLoop):
        cli.run(cfg, sink, connect=connect, status=status)
    assert status.calls[0] == (True, [2000] + [1500] * 7, True)
    assert status.calls[-1] == (False, [2000] + [1500] * 7, False)


@pytest.fixture
def pygame():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    module = pytest.importorskip("pygame")
    module.display.init()
    module.font.init()
    yield module
    module.quit()


@pytest.mark.parametrize("status,stale", [
    (None, True),
    ({"sending": True, "joystick": True, "channels": [1000, 1500, 2000, 1234, 1500, 1500, 1500, 1500], "frame_us": 22500}, False),
    ({"sending": False, "joystick": False, "channels": [1500] * 16, "frame_us": 35000}, False),
    ({"sending": True, "joystick": True, "channels": [900, 2100], "frame_us": 22500}, True),
])
def test_render_draws_any_channel_count(pygame, status, stale):
    surface = display.render(pygame, (1280, 720), status, stale)
    assert surface.get_size() == (1280, 720)


def test_headline_states():
    sending = {"sending": True, "joystick": True, "channels": []}
    assert display.headline(None, True)[0].startswith("WARTE")
    assert display.headline(sending, True)[0].startswith("KEINE DATEN")
    assert display.headline({**sending, "sending": False}, False)[0].startswith("GESTOPPT")
    assert display.headline({**sending, "joystick": False}, False)[0].startswith("SENDET NEUTRAL")
    assert display.headline(sending, False)[0] == "SENDET"


def test_receive_latest_keeps_the_newest_valid_message(receiver):
    receiver.setblocking(False)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    address = receiver.getsockname()
    for payload in (b'{"channels": [1000]}', b"junk", b'{"channels": [2000]}', b'{"no": 1}'):
        sender.sendto(payload, address)
    sender.close()
    import time
    time.sleep(0.05)
    assert display.receive_latest(receiver) == {"channels": [2000]}
    assert display.receive_latest(receiver) is None


def test_portrait_panel_is_turned_to_landscape():
    assert display.rotation_for((720, 1280), "auto") == 90
    assert display.rotation_for((1280, 720), "auto") == 0
    assert display.rotation_for((720, 1280), "270") == 270
