import pytest

from joystick_trainer import config
from joystick_trainer.calibrate import (STEPS, CalibrationError, Wizard, pick_axis, pick_button,
                                        render_config)

# Thrustmaster T.Flight Hotas X as measured 2026-10-15: X/Y 0..1023, Z/RZ/THROTTLE 0..255, hats -1..1
X, Y, Z, RZ, THR, HAT0X = 0, 1, 2, 5, 6, 16
RANGES = {X: (0, 1023), Y: (0, 1023), Z: (0, 255), RZ: (0, 255), THR: (0, 255), HAT0X: (-1, 1)}
CENTRE = {X: 512, Y: 512, Z: 255, RZ: 128, THR: 128, HAT0X: 0}
NAMES = {X: "ABS_X", Y: "ABS_Y", Z: "ABS_Z", RZ: "ABS_RZ", THR: "ABS_THROTTLE", HAT0X: "ABS_HAT0X"}


def moved(**changes):
    values = dict(CENTRE)
    for key, value in changes.items():
        values[globals()[key]] = value
    return values


def test_stick_right_goes_up_no_invert():
    pick = pick_axis(CENTRE, moved(X=1023), RANGES)
    assert (pick.code, pick.invert, pick.warnings) == (X, False, [])
    assert pick.reach == pytest.approx(1.0)


def test_stick_forward_reads_low_so_invert():
    pick = pick_axis(CENTRE, moved(Y=0), RANGES)
    assert (pick.code, pick.invert) == (Y, True)


def test_hotas_throttle_idle_is_255_so_invert():
    pick = pick_axis(CENTRE, moved(Z=0), RANGES, kind="throttle")
    assert (pick.code, pick.invert) == (Z, True)
    assert pick.reach == pytest.approx(1.0)


def test_small_move_is_rejected():
    with pytest.raises(CalibrationError, match="no axis moved"):
        pick_axis(CENTRE, moved(X=600), RANGES)


def test_two_axes_moving_is_rejected():
    with pytest.raises(CalibrationError, match="two axes"):
        pick_axis(CENTRE, moved(X=1023, Y=1000), RANGES)


def test_already_assigned_axis_and_hats_are_ignored():
    with pytest.raises(CalibrationError):
        pick_axis(CENTRE, moved(X=1023, HAT0X=1), RANGES, exclude={X})


def test_partial_reach_and_off_centre_warn():
    rest = moved(X=600)
    pick = pick_axis(rest, moved(X=950), RANGES)
    assert any("off centre" in w for w in pick.warnings)
    assert any("reached only" in w for w in pick.warnings)


def test_pick_button():
    assert pick_button({288}, {288, 289}) == 289
    with pytest.raises(CalibrationError):
        pick_button(set(), {288, 289})


class Script:
    """Feeds the wizard: each prompt answer moves the fake stick into the asked position."""

    def __init__(self, positions):
        self.positions = list(positions)
        self.axes = dict(CENTRE)
        self.keys = set()
        self.output = []

    def ask(self, prompt):
        item = self.positions.pop(0)
        if item == "skip":
            return "s"
        axes, keys = item
        self.axes, self.keys = {**CENTRE, **axes}, set(keys)
        return ""

    def say(self, text):
        self.output.append(text)


def test_wizard_writes_a_loadable_config_matching_the_verified_hotas_config(tmp_path):
    rest = ({}, ())
    script = Script([
        rest, ({X: 1023}, ()),                 # roll right
        rest, ({Y: 0}, ()),                    # pitch forward
        rest, ({Z: 0}, ()),                    # throttle full (Hotas reads 0 at full)
        rest, ({RZ: 255}, ()),                 # yaw right
        rest, ({}, (288,)),                    # arm button
    ])
    wizard = Wizard(RANGES, lambda: script.axes, lambda: script.keys, NAMES.get,
                    lambda code: {288: "BTN_TRIGGER"}[code], ask=script.ask, say=script.say)
    axes, buttons = wizard.run(STEPS)
    assert axes == [("roll", 1, "ABS_X", False, False), ("pitch", 2, "ABS_Y", True, False),
                    ("throttle", 3, "ABS_Z", True, True), ("yaw", 4, "ABS_RZ", False, False)]
    assert buttons == [("arm", 5, "BTN_TRIGGER")]

    path = tmp_path / "config.yaml"
    path.write_text(render_config("T.Flight Hotas X", axes, buttons))
    cfg = config.load(path)
    assert cfg["output"]["sink"] == "print"
    by_source = {a.source: a for a in cfg["mapping"].axes}
    assert by_source["ABS_Z"].unipolar and by_source["ABS_Z"].invert
    assert by_source["ABS_Y"].invert and not by_source["ABS_X"].invert


def test_wizard_retries_until_recognised_and_allows_skip():
    rest = ({}, ())
    script = Script([rest, ({X: 600}, ()), rest, ({X: 1023}, ()), "skip"])
    wizard = Wizard(RANGES, lambda: script.axes, lambda: script.keys, NAMES.get, str,
                    ask=script.ask, say=script.say)
    axes, buttons = wizard.run(STEPS[:2])
    assert axes == [("roll", 1, "ABS_X", False, False)]
    assert any("not recognised" in line for line in script.output)
    assert any("skipped" in line for line in script.output)


def test_lgpio_output_block_has_measured_pocket_values(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text(render_config("x", [("roll", 1, "ABS_X", False, False)], [], output="lgpio"))
    out = config.load(path)["output"]
    assert out == {"sink": "lgpio", "pin": 17, "chip": 0, "pulse_us": 300, "frame_us": 22500, "active_high": False}


def test_code_name_prefers_specific_alias():
    from joystick_trainer.calibrate import code_name
    assert code_name({288: ["BTN_JOYSTICK", "BTN_TRIGGER"]}, 288) == "BTN_TRIGGER"
    assert code_name({0: "ABS_X"}, 0) == "ABS_X"
