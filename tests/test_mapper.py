from joystick_trainer.mapper import AxisMap, ButtonMap, Mapper, Mapping, shape
from joystick_trainer.state import JoystickState


def state_with(axes=None, buttons=None):
    s = JoystickState()
    for name, value in (axes or {}).items():
        s.set_axis(name, value, -100, 100)
    for name, pressed in (buttons or {}).items():
        s.set_button(name, pressed)
    return s


def test_centered_axis_gives_1500():
    mapper = Mapper(Mapping(axes=[AxisMap("ABS_X", 1)]))
    assert mapper.channels(state_with({"ABS_X": 0}))[0] == 1500


def test_full_deflection_and_invert():
    mapper = Mapper(Mapping(axes=[AxisMap("ABS_X", 1), AxisMap("ABS_Y", 2, invert=True)]))
    out = mapper.channels(state_with({"ABS_X": 100, "ABS_Y": 100}))
    assert out[0] == 2000 and out[1] == 1000


def test_deadzone_swallows_small_values():
    assert shape(0.04, 0.05, 0.0) == 0.0
    assert shape(1.0, 0.05, 0.0) == 1.0


def test_expo_softens_centre_keeps_ends():
    assert abs(shape(0.5, 0.0, 1.0)) == 0.125
    assert shape(1.0, 0.0, 1.0) == 1.0


def test_unipolar_throttle_spans_full_range():
    mapper = Mapper(Mapping(axes=[AxisMap("ABS_Z", 3, unipolar=True)]))
    assert mapper.channels(state_with({"ABS_Z": -100}))[2] == 1000
    assert mapper.channels(state_with({"ABS_Z": 100}))[2] == 2000


def test_toggle_button_flips_on_press_edge():
    mapper = Mapper(Mapping(buttons=[ButtonMap("BTN_TRIGGER", 5, toggle=True)]))
    assert mapper.channels(state_with(buttons={"BTN_TRIGGER": False}))[4] == 1000
    assert mapper.channels(state_with(buttons={"BTN_TRIGGER": True}))[4] == 2000
    assert mapper.channels(state_with(buttons={"BTN_TRIGGER": True}))[4] == 2000
    assert mapper.channels(state_with(buttons={"BTN_TRIGGER": False}))[4] == 2000
    assert mapper.channels(state_with(buttons={"BTN_TRIGGER": True}))[4] == 1000


def test_defaults_apply_to_unmapped_channels():
    mapper = Mapper(Mapping(defaults_us={3: 1000}))
    assert mapper.channels(state_with())[2] == 1000
