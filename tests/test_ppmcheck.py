from joystick_trainer.ppm import frame_edges
from joystick_trainer.ppmcheck import analyze, load_edges


def edges_for(frames, jitter=0.0):
    t, out = 0.0, []
    for channels in frames:
        for level, duration in frame_edges(channels):
            out.append((t, level))
            t += (duration + jitter) * 1e-6
    return out


def test_recovers_channels_and_frame_length():
    frames = [[1000, 1500, 2000, 1500, 1500, 1500, 1500, 1500]] * 6
    result = analyze(edges_for(frames))
    assert result["channels"] == 8
    assert [round(c["mean_us"]) for c in result["per_channel"][:3]] == [1000, 1500, 2000]
    assert round(result["frame_us_mean"]) == 22500
    assert round(result["pulse_us_mean"]) == 300


def test_load_edges_skips_header(tmp_path):
    path = tmp_path / "cap.csv"
    path.write_text("Time [s],Channel 0\n0.0,1\n0.0003,0\n")
    assert load_edges(path) == [(0.0, 1), (0.0003, 0)]


def test_empty_capture_gives_none():
    assert analyze([]) is None
