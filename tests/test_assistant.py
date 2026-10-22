import types

import pytest

from joystick_trainer import assistant, config, desktop, diagnose
from joystick_trainer.calibrate import Wizard, render_config
from joystick_trainer.mapper import AxisMap, ButtonMap, Mapping
from test_calibrate import CENTRE, NAMES, RANGES, RZ, X, Y, Z, Script

HOTAS_AXES = [("roll", 1, "ABS_X", False, False), ("pitch", 2, "ABS_Y", True, False),
              ("throttle", 3, "ABS_Z", True, True), ("yaw", 4, "ABS_RZ", False, False)]


class ScriptedUi(assistant.Ui):
    def __init__(self, answers):
        self.answers, self.lines = list(answers), []
        super().__init__(ask=self._next, out=self.lines.append, log=None)

    def _next(self, prompt):
        self.lines.append(prompt)
        if not self.answers:
            raise EOFError
        return self.answers.pop(0)


def test_calibration_wizard_speaks_german():
    rest = ({}, ())
    script = Script([rest, ({X: 600}, ()), rest, ({X: 1023}, ()), rest, ({Y: 0}, ()), rest, ({Z: 0}, ()),
                     rest, ({RZ: 255}, ()), rest, ({}, (288,))])
    ui = ScriptedUi([])
    ui._ask = script.ask
    wizard = Wizard(RANGES, lambda: script.axes, lambda: script.keys, NAMES.get, lambda c: "BTN_TRIGGER",
                    ask=ui.ask, say=ui.say)
    axes, buttons = wizard.run(assistant.STEPS_DE)
    assert [a[2] for a in axes] == ["ABS_X", "ABS_Y", "ABS_Z", "ABS_RZ"] and buttons
    text = "\n".join(ui.lines)
    assert "Nicht erkannt" in text and "erkannt: ABS_Y (umgedreht)" in text and "Kanal 3" in text
    for english in ("skipped", "not recognised", "warning", "reach", "channel", "Enter = ok"):
        assert english not in text


def test_every_wizard_message_is_translated():
    for line in ("  warning: rest position is 12% off centre", "  warning: held position reached only 80% of the travel",
                 "  not recognised: two axes moved - move only this one control. Again.",
                 "  not recognised: expected exactly one newly pressed button, got 2. Again.", "  skipped"):
        assert assistant.translate(line) != line


def test_lgpio_config_keeps_the_calibration(tmp_path):
    dry = render_config("T.Flight Hotas X", HOTAS_AXES, [("arm", 5, "BTN_TRIGGER")])
    path = tmp_path / "config.lgpio.yaml"
    path.write_text(assistant.lgpio_config_text(dry))
    cfg = config.load(path)
    assert cfg["output"] == {"sink": "lgpio", "pin": 17, "chip": 0, "pulse_us": 300, "frame_us": 22500, "active_high": False}
    assert [a.source for a in cfg["mapping"].axes] == ["ABS_X", "ABS_Y", "ABS_Z", "ABS_RZ"]
    assert cfg["mapping"].buttons[0].toggle


def test_capture_judgement():
    good = {"channels": 8, "pulse_us_mean": 300.4, "frame_us_mean": 22505}
    assert assistant.judge_capture(good)[0]
    assert not assistant.judge_capture(None)[0]
    ok, text = assistant.judge_capture({**good, "pulse_us_mean": 2200})
    assert not ok and "NICHT weitermachen" in text
    assert not assistant.judge_capture({**good, "channels": 2})[0]


def test_sweep_and_rest_checks():
    mapping = Mapping(axes=[AxisMap("ABS_X", 1), AxisMap("ABS_Z", 3, unipolar=True)],
                      buttons=[ButtonMap("BTN_TRIGGER", 5, toggle=True)])
    low, high = [1000] * 8, [2000] * 8
    assert all(ok for *_, ok in assistant.sweep_result(low, high, mapping))
    high[2] = 1700
    assert [ch for ch, *_, ok in assistant.sweep_result(low, high, mapping) if not ok] == [3]
    assert assistant.rest_problems([1500, 1500, 1000] + [1500] * 5, mapping) == []
    problems = assistant.rest_problems([1600, 1500, 1200] + [1500] * 5, mapping)
    assert len(problems) == 2 and "1600" in problems[0] and "1200" in problems[1]


def test_input_group_states(monkeypatch):
    group = types.SimpleNamespace(gr_gid=104, gr_mem=["chef"])
    monkeypatch.setattr(assistant.grp, "getgrnam", lambda name: group)
    monkeypatch.setenv("USER", "chef")
    assert assistant.input_group_state([104]) == "ok"
    assert assistant.input_group_state([1000]) == "reboot"
    monkeypatch.setenv("USER", "other")
    assert assistant.input_group_state([1000]) == "missing"


def test_dsi_detection(tmp_path):
    (tmp_path / "card1-HDMI-A-1").mkdir()
    (tmp_path / "card1-HDMI-A-1/status").write_text("disconnected\n")
    assert not assistant.dsi_connected(tmp_path)
    (tmp_path / "card1-DSI-1").mkdir()
    (tmp_path / "card1-DSI-1/status").write_text("connected\n")
    assert assistant.dsi_connected(tmp_path)


def test_pin_left_as_output_is_detected():
    def run(output):
        return lambda *a, **k: types.SimpleNamespace(stdout=output)
    assert assistant.pin_is_output(run=run("17: op dh pd | hi // GPIO17 = output"))
    assert not assistant.pin_is_output(run=run("17: ip    pd | lo // GPIO17 = input"))
    assert not assistant.pin_is_output(run=run("17: no    pd | -- // GPIO17 = none"))


def test_desktop_icons_are_recorded_for_uninstall(tmp_path):
    repo, target = tmp_path / "repo", tmp_path / "Schreibtisch"
    repo.mkdir()
    names = desktop.install_icons(repo, target)
    assert "Joystick-Trainer starten" in names
    state = (repo / ".install-state").read_text().splitlines()
    assert state[0] == f"dir={target}"
    assert sorted(line for line in state if line.startswith("file=")) == sorted(
        f"file={p}" for p in target.glob("*.desktop"))
    entry = (target / "joystick-trainer-kalibrieren.desktop").read_text()
    assert f"Exec={repo}/scripts/keep-open.sh {repo}/scripts/assistent.sh --kalibrieren" in entry
    desktop.install_icons(repo, target)
    assert (repo / ".install-state").read_text().splitlines() == state


class FakeAssistant:
    def __init__(self, ui, results):
        self.ui, self.state, self.results = ui, {"done": ["welcome"]}, results

    def __getattr__(self, key):
        return lambda: self.results[key].pop(0)


def test_run_skips_done_steps_retries_and_saves(monkeypatch, tmp_path):
    monkeypatch.setattr(assistant, "STATE", tmp_path / "state")
    saved = []
    monkeypatch.setattr(assistant, "save_state", lambda state, path=None: saved.append(list(state["done"])))
    ui = ScriptedUi(["", "u"])
    fake = FakeAssistant(ui, {"system": [False, True], "joystick": [False]})
    assistant.run(fake, ["welcome", "system", "joystick"])
    assert fake.state["done"] == ["welcome", "system"]
    assert saved[-1] == ["welcome", "system"]


def test_welcome_aborts_without_consent(tmp_path):
    ui = ScriptedUi(["n"])
    with pytest.raises(assistant.Abort):
        assistant.Assistant(ui, {"done": []}, repo=tmp_path).welcome()


def test_diagnose_report_has_all_sections_and_no_network_data(tmp_path):
    (tmp_path / "config.yaml").write_text('device: "x"\n')
    report = "\n".join(f"{title}\n{body}" for title, body in diagnose.sections(tmp_path))
    for title in ("Gerät", "Joysticks", "GPIO17", "config.yaml", "Tests"):
        assert title in report
    for secret in ("psk", "wpa", "ssid"):
        assert secret not in report.lower()
