import pytest

from joystick_trainer.ppm import clamp_us, frame_edges


def test_frame_total_duration_equals_frame_us():
    edges = frame_edges([1500] * 8, frame_us=22500)
    assert sum(d for _, d in edges) == 22500


def test_pulse_start_spacing_equals_channel_width():
    edges = frame_edges([1000, 2000], pulse_us=300, frame_us=22500)
    assert edges[0] == (1, 300) and edges[1] == (0, 700)
    assert edges[2] == (1, 300) and edges[3] == (0, 1700)


def test_inverted_polarity_swaps_levels():
    edges = frame_edges([1500], active_high=False)
    assert edges[0][0] == 0 and edges[1][0] == 1


def test_values_are_clamped():
    assert clamp_us(500) == 1000 and clamp_us(2500) == 2000


def test_too_long_channels_raise():
    with pytest.raises(ValueError):
        frame_edges([2000] * 8, frame_us=18000)
