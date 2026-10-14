CHANNEL_MIN_US = 1000
CHANNEL_MAX_US = 2000
CHANNEL_MID_US = 1500


def clamp_us(value: float) -> int:
    return int(min(CHANNEL_MAX_US, max(CHANNEL_MIN_US, round(value))))


def frame_edges(channels_us, pulse_us=300, frame_us=22500, active_high=True):
    """One PPM frame as (level, duration_us) pairs.

    Each channel is a pulse followed by a gap; pulse start to pulse start equals the
    channel width. The last gap is the sync gap that pads the frame to frame_us.
    """
    widths = [clamp_us(c) for c in channels_us]
    used = sum(widths)
    sync = frame_us - used
    if sync < 3000:
        raise ValueError(f"frame_us {frame_us} too short for channels totalling {used} us")
    high, low = (1, 0) if active_high else (0, 1)
    edges = []
    for width in widths:
        edges.append((high, pulse_us))
        edges.append((low, width - pulse_us))
    edges.append((high, pulse_us))
    edges.append((low, sync - pulse_us))
    return edges
