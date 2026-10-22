"""Live status for joystick-trainer-display: the main loop sends what the sink currently emits as a
small UDP datagram. Fire and forget, so a missing or hung display can never stall the PPM output."""

import json
import socket
import time

DEFAULT_PORT = 5600


class StatusPublisher:
    def __init__(self, host="127.0.0.1", port=DEFAULT_PORT, rate_hz=20, frame_us=22500, clock=time.monotonic):
        self._address = (host, port)
        self._interval = 1.0 / rate_hz
        self._frame_us = frame_us
        self._clock = clock
        self._next = 0.0
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setblocking(False)

    def publish(self, sending, channels, joystick):
        """sending: PPM is on the pin; channels: the values in it (or the last ones); joystick: connected."""
        now = self._clock()
        if now < self._next:
            return
        self._next = now + self._interval
        message = {"sending": sending, "joystick": joystick, "channels": list(channels), "frame_us": self._frame_us}
        try:
            self._socket.sendto(json.dumps(message).encode(), self._address)
        except OSError:
            pass

    def close(self):
        self._socket.close()
