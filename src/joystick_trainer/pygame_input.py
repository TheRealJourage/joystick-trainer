"""Joystick input through pygame (SDL) as an alternative to evdev (`input: pygame` in the config).
Controls are named by SDL index: AXIS_<n>, BUTTON_<n>. Axes report -32767..32767, from their first motion on."""

import os

from .state import JoystickState

AXIS_SCALE = 32767


def init():
    # No window: SDL's event queue needs a video driver, and joystick events must arrive without focus.
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    pygame.display.init()
    # Re-initialising re-enumerates, so a joystick plugged in after start is found on the next retry.
    pygame.joystick.quit()
    pygame.joystick.init()
    return pygame


def list_joysticks():
    pygame = init()
    return [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]


def find_joystick(selector):
    """selector: a case-insensitive substring of the joystick name."""
    for joystick in list_joysticks():
        if selector.lower() in joystick.get_name().lower():
            return joystick
    raise FileNotFoundError(f"no pygame joystick matching {selector!r}")


def read_axis(device, index):
    return round(device.get_axis(index) * AXIS_SCALE)


def control_index(name, prefix):
    number = name[len(prefix):]
    if not name.startswith(prefix) or not number.isdigit():
        raise ValueError(f"{name!r} is not a pygame control name, expected {prefix}<number>")
    return int(number)


class PygameJoystick:
    def __init__(self, selector, axis_names, button_names):
        self.device = find_joystick(selector)
        import pygame

        self._pygame = pygame
        self.state = JoystickState()
        self.lost = False
        self._reported = set()   # axes SDL has sent motion for; before that its value is a placeholder
        self._axes = {name: control_index(name, "AXIS_") for name in axis_names}
        self._buttons = {name: control_index(name, "BUTTON_") for name in button_names}
        for name, index in self._axes.items():
            if index >= self.device.get_numaxes():
                raise ValueError(f"{self.device.get_name()} has no axis {name}")
        for name, index in self._buttons.items():
            if index >= self.device.get_numbuttons():
                raise ValueError(f"{self.device.get_name()} has no button {name}")
        self._read()

    def _read(self):
        for name, index in self._axes.items():
            if index in self._reported:
                self.state.set_axis(name, read_axis(self.device, index), -AXIS_SCALE, AXIS_SCALE)
        for name, index in self._buttons.items():
            self.state.set_button(name, self.device.get_button(index))

    def poll(self, timeout):
        pygame = self._pygame
        events = [pygame.event.wait(int(timeout * 1000))] + pygame.event.get()
        mine = self.device.get_instance_id()
        for event in events:
            if event.type == pygame.JOYDEVICEREMOVED and event.instance_id == mine:
                self.lost = True
                return
            if event.type == pygame.JOYAXISMOTION and event.instance_id == mine:
                self._reported.add(event.axis)
        self._read()

    def close(self):
        self.device.quit()
