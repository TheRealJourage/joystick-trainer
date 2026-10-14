import shutil
import subprocess
import sys

import pytest

from joystick_trainer.ppm import frame_edges
from joystick_trainer.sinks import PioSink

NATIVE = "native"


@pytest.fixture(scope="module")
def dump_binary(tmp_path_factory):
    if shutil.which("gcc") is None:
        pytest.skip("gcc missing")
    out = tmp_path_factory.mktemp("bin") / "ppm_pio_dump"
    subprocess.run(["gcc", "-DDUMP_ONLY", "-o", str(out), f"{NATIVE}/ppm_pio.c"], check=True)
    return str(out)


@pytest.mark.parametrize("channels", [[1500] * 8, [1000, 2000, 1234, 1500, 1500, 1100, 1900, 1500]])
@pytest.mark.parametrize("active_high", [True, False])
def test_native_frame_matches_python_frame(dump_binary, channels, active_high):
    command = [dump_binary, "--dump", *map(str, channels)]
    if not active_high:
        command.insert(1, "--active-low")
    out = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    native = [tuple(map(int, line.split())) for line in out.splitlines()]
    assert native == frame_edges(channels, active_high=active_high)


def test_pio_sink_talks_to_helper(tmp_path):
    log = tmp_path / "stdin.log"
    helper = tmp_path / "helper.py"
    helper.write_text(f"#!{sys.executable}\nimport sys\nopen({str(log)!r}, 'w').write(sys.stdin.read())\n")
    helper.chmod(0o755)
    sink = PioSink(pin=18, helper=str(helper))
    sink.set_channels([1500] * 8)
    sink.set_channels([1500] * 8)
    sink.set_channels([1000] + [1500] * 7)
    sink.stop()
    sink.close()
    assert log.read_text().splitlines() == ["1500 " * 7 + "1500", "1000 " + "1500 " * 6 + "1500", "stop", "quit"]
