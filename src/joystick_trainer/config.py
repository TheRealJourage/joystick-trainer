import yaml

from .mapper import AxisMap, ButtonMap, Mapping
from .ppm import CHANNEL_MAX_US, MIN_SYNC_US
from .status import DEFAULT_PORT


def load(path):
    with open(path) as handle:
        raw = yaml.safe_load(handle)
    mapping = Mapping(
        channel_count=raw.get("channels", 8),
        axes=[AxisMap(**a) for a in raw.get("axes", [])],
        buttons=[ButtonMap(**b) for b in raw.get("buttons", [])],
        defaults_us={int(k): v for k, v in raw.get("defaults_us", {}).items()},
    )
    for item in mapping.axes + mapping.buttons:
        if not 1 <= item.channel <= mapping.channel_count:
            raise ValueError(f"{item.source}: channel {item.channel} outside 1..{mapping.channel_count}")
    source = raw.get("input", "evdev")
    if source not in ("evdev", "pygame"):
        raise ValueError(f"input: {source!r}, expected evdev or pygame")
    output = raw.get("output", {})
    # Checked here, not per frame: otherwise too many channels only fail once enough sticks are near full.
    frame_us = output.get("frame_us", 22500)
    needed = mapping.channel_count * CHANNEL_MAX_US + MIN_SYNC_US
    if needed > frame_us:
        fit = (frame_us - MIN_SYNC_US) // CHANNEL_MAX_US
        raise ValueError(f"{mapping.channel_count} channels need frame_us >= {needed}; "
                         f"frame_us {frame_us} fits at most {fit}")
    display = {"enabled": True, "host": "127.0.0.1", "port": DEFAULT_PORT, **raw.get("display", {})}
    return {
        "device": raw["device"],
        "input": source,
        "mapping": mapping,
        "output": output,
        "display": display,
        "on_lost": raw.get("on_lost", "stop"),
        "rate_hz": raw.get("rate_hz", 50),
    }
