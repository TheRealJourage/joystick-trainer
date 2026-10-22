import select

from .state import JoystickState


def find_device(selector):
    """selector: a /dev/input path, or a case-insensitive substring of the device name."""
    from evdev import InputDevice, list_devices

    if selector.startswith("/dev/"):
        return InputDevice(selector)
    for path in list_devices():
        device = InputDevice(path)
        if selector.lower() in device.name.lower():
            return device
        device.close()
    raise FileNotFoundError(f"no input device matching {selector!r}")


class Joystick:
    def __init__(self, selector, axis_names, button_names):
        from evdev import ecodes

        self.device = find_device(selector)
        self.state = JoystickState()
        self.lost = False
        self._axis_by_code = {}
        self._button_by_code = {}
        absinfo = dict(self.device.capabilities().get(ecodes.EV_ABS, []))
        for name in axis_names:
            code = ecodes.ecodes[name]
            if code not in absinfo:
                raise ValueError(f"{self.device.name} has no axis {name}")
            # The value at open is not used: the Hotas X reports 0 on every axis until it is first moved,
            # which with its inverted throttle meant full throttle at start. An axis counts once it reports.
            self._axis_by_code[code] = (name, absinfo[code].min, absinfo[code].max)
        for name in button_names:
            self._button_by_code[ecodes.ecodes[name]] = name
        self._ecodes = ecodes

    def poll(self, timeout):
        try:
            ready, _, _ = select.select([self.device.fd], [], [], timeout)
            if not ready:
                return
            for event in self.device.read():
                if event.type == self._ecodes.EV_ABS and event.code in self._axis_by_code:
                    name, lo, hi = self._axis_by_code[event.code]
                    self.state.set_axis(name, event.value, lo, hi)
                elif event.type == self._ecodes.EV_KEY and event.code in self._button_by_code:
                    self.state.set_button(self._button_by_code[event.code], event.value != 0)
        except OSError:
            self.lost = True

    def close(self):
        self.device.close()
