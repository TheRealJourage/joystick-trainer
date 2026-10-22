import sys
import types

import pytest

from joystick_trainer import cli, config, pygame_input
from joystick_trainer.calibrate import render_config
from joystick_trainer.mapper import Mapper

JOYDEVICEREMOVED, NOEVENT = 0x606, 0


class FakeJoystickDevice:
    def __init__(self, name, axes, buttons, instance_id=7):
        self.name, self.axes, self.buttons, self.instance_id = name, list(axes), list(buttons), instance_id
        self.closed = False

    def get_name(self):
        return self.name

    def get_numaxes(self):
        return len(self.axes)

    def get_numbuttons(self):
        return len(self.buttons)

    def get_axis(self, i):
        return self.axes[i]

    def get_button(self, i):
        return self.buttons[i]

    def get_instance_id(self):
        return self.instance_id

    def quit(self):
        self.closed = True


@pytest.fixture
def fake_pygame(monkeypatch):
    """A stand-in for pygame with one joystick, so the backend runs without SDL or hardware."""
    devices = [FakeJoystickDevice("T.Flight Hotas X", [0.0, 0.0, 1.0, 0.0], [0, 0])]
    queue = []
    module = types.ModuleType("pygame")
    module.JOYDEVICEREMOVED = JOYDEVICEREMOVED
    module.display = types.SimpleNamespace(init=lambda: None)
    module.joystick = types.SimpleNamespace(init=lambda: None, quit=lambda: None,
                                            get_count=lambda: len(devices), Joystick=lambda i: devices[i])

    def wait(timeout_ms):
        return queue.pop(0) if queue else types.SimpleNamespace(type=NOEVENT)

    def get():
        events = list(queue)
        queue.clear()
        return events

    module.event = types.SimpleNamespace(wait=wait, get=get)
    module.devices, module.queue = devices, queue
    monkeypatch.setitem(sys.modules, "pygame", module)
    return module


def test_axes_and_buttons_are_read_by_index(fake_pygame):
    joystick = pygame_input.PygameJoystick("hotas", ["AXIS_0", "AXIS_2"], ["BUTTON_1"])
    device = fake_pygame.devices[0]
    device.axes[0], device.buttons[1] = 1.0, 1
    joystick.poll(0.02)
    assert joystick.state.axis("AXIS_0") == pytest.approx(1.0)
    assert joystick.state.axis("AXIS_2") == pytest.approx(1.0)
    assert joystick.state.button("BUTTON_1") is True
    assert not joystick.lost


def test_unplugging_marks_the_joystick_lost(fake_pygame):
    joystick = pygame_input.PygameJoystick("hotas", ["AXIS_0"], [])
    fake_pygame.queue.append(types.SimpleNamespace(type=JOYDEVICEREMOVED, instance_id=7))
    joystick.poll(0.02)
    assert joystick.lost
    joystick.close()
    assert fake_pygame.devices[0].closed


def test_missing_joystick_or_control_raises_what_the_main_loop_retries_on(fake_pygame):
    with pytest.raises(FileNotFoundError):
        pygame_input.PygameJoystick("xbox", ["AXIS_0"], [])
    with pytest.raises(ValueError, match="no axis AXIS_9"):
        pygame_input.PygameJoystick("hotas", ["AXIS_9"], [])
    with pytest.raises(ValueError, match="not a pygame control name"):
        pygame_input.PygameJoystick("hotas", ["ABS_X"], [])


def test_calibrated_pygame_config_selects_the_pygame_backend(tmp_path, fake_pygame):
    path = tmp_path / "c.yaml"
    path.write_text(render_config("T.Flight Hotas X", [("throttle", 3, "AXIS_2", True, True)],
                                  [("arm", 5, "BUTTON_0")], input_source="pygame"))
    cfg = config.load(path)
    assert cfg["input"] == "pygame"
    assert cli.joystick_class(cfg["input"]) is pygame_input.PygameJoystick
    joystick = pygame_input.PygameJoystick(cfg["device"], ["AXIS_2"], ["BUTTON_0"])
    # Hotas X throttle at idle reads +1.0 here, so the calibrated invert gives 1000 us.
    assert Mapper(cfg["mapping"]).channels(joystick.state)[2] == 1000


def test_evdev_stays_the_default(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text(render_config("x", [("roll", 1, "ABS_X", False, False)], []))
    assert "input:" not in path.read_text()
    assert config.load(path)["input"] == "evdev"
    path.write_text('device: "x"\ninput: sdl\n')
    with pytest.raises(ValueError, match="expected evdev or pygame"):
        config.load(path)
