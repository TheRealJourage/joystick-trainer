class JoystickState:
    """Latest normalised axis values (-1..1) and button states, keyed by evdev code name."""

    def __init__(self):
        self._axes = {}
        self._buttons = {}

    def set_axis(self, name, value, minimum, maximum):
        self._axes[name] = 2.0 * (value - minimum) / (maximum - minimum) - 1.0

    def set_button(self, name, pressed):
        self._buttons[name] = bool(pressed)

    def axis(self, name):
        return self._axes.get(name)

    def button(self, name):
        return self._buttons.get(name, False)
