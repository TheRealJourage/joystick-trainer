from dataclasses import dataclass, field

from .ppm import CHANNEL_MAX_US, CHANNEL_MID_US, CHANNEL_MIN_US, clamp_us


@dataclass
class AxisMap:
    source: str
    channel: int
    invert: bool = False
    deadzone: float = 0.05
    expo: float = 0.0
    unipolar: bool = False


@dataclass
class ButtonMap:
    source: str
    channel: int
    toggle: bool = False
    low_us: int = CHANNEL_MIN_US
    high_us: int = CHANNEL_MAX_US


@dataclass
class Mapping:
    channel_count: int = 8
    axes: list = field(default_factory=list)
    buttons: list = field(default_factory=list)
    defaults_us: dict = field(default_factory=dict)


def shape(value: float, deadzone: float, expo: float) -> float:
    """value in -1..1 -> deadzone and expo applied, still -1..1."""
    magnitude = abs(value)
    if magnitude <= deadzone:
        return 0.0
    scaled = (magnitude - deadzone) / (1.0 - deadzone)
    curved = (1.0 - expo) * scaled + expo * scaled ** 3
    return curved if value > 0 else -curved


class Mapper:
    def __init__(self, mapping: Mapping):
        self.mapping = mapping
        self._toggled = {}
        self._last_pressed = {}

    def initial_channels(self):
        channels = [CHANNEL_MID_US] * self.mapping.channel_count
        for ch, us in self.mapping.defaults_us.items():
            channels[ch - 1] = clamp_us(us)
        return channels

    def channels(self, state):
        out = self.initial_channels()
        for axis in self.mapping.axes:
            raw = state.axis(axis.source)
            if raw is None:
                continue
            if axis.unipolar:
                level = (raw + 1.0) / 2.0
                if axis.invert:
                    level = 1.0 - level
                us = CHANNEL_MIN_US + level * (CHANNEL_MAX_US - CHANNEL_MIN_US)
            else:
                value = shape(-raw if axis.invert else raw, axis.deadzone, axis.expo)
                us = CHANNEL_MID_US + value * (CHANNEL_MAX_US - CHANNEL_MID_US)
            out[axis.channel - 1] = clamp_us(us)
        for button in self.mapping.buttons:
            pressed = state.button(button.source)
            if button.toggle:
                key = button.source
                if pressed and not self._last_pressed.get(key, False):
                    self._toggled[key] = not self._toggled.get(key, False)
                self._last_pressed[key] = pressed
                active = self._toggled.get(key, False)
            else:
                active = pressed
            out[button.channel - 1] = clamp_us(button.high_us if active else button.low_us)
        return out
