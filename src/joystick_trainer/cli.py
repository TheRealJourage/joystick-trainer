import argparse
import signal
import sys
import time

from . import config as config_module
from .joystick import Joystick
from .mapper import Mapper
from .sinks import make_sink
from .status import StatusPublisher


class _NoStatus:
    def publish(self, *_):
        pass


def run(cfg, sink, connect=Joystick, status=_NoStatus()):
    mapping = cfg["mapping"]
    mapper = Mapper(mapping)
    axes = [a.source for a in mapping.axes]
    buttons = [b.source for b in mapping.buttons]
    period = 1.0 / cfg["rate_hz"]
    joystick = None
    next_retry = 0.0
    sending, last = False, mapper.initial_channels()

    def emit(channels):
        nonlocal sending, last
        sink.set_channels(channels)
        sending, last = True, channels

    while True:
        started = time.monotonic()
        if joystick is None and started >= next_retry:
            try:
                joystick = connect(cfg["device"], axes, buttons)
            except (FileNotFoundError, OSError, ValueError) as error:
                print(f"joystick unavailable: {error}", flush=True)
                next_retry = started + 1.0
        if joystick is not None:
            joystick.poll(period)
            if joystick.lost:
                print("joystick lost", flush=True)
                joystick.close()
                joystick = None
                if cfg["on_lost"] == "stop":
                    sink.stop()
                    sending = False
                else:
                    emit(mapper.initial_channels())
            else:
                emit(mapper.channels(joystick.state))
        else:
            time.sleep(period)
        status.publish(sending, last, joystick is not None)


def joystick_class(source):
    if source == "pygame":
        from .pygame_input import PygameJoystick

        return PygameJoystick
    return Joystick


def main():
    parser = argparse.ArgumentParser(prog="joystick-trainer")
    parser.add_argument("config")
    args = parser.parse_args()
    cfg = config_module.load(args.config)
    sink = make_sink(cfg["output"], cfg["mapping"].channel_count)
    display = cfg["display"]
    status = (StatusPublisher(display["host"], display["port"], frame_us=cfg["output"].get("frame_us", 22500))
              if display["enabled"] else _NoStatus())
    # SIGTERM (systemd stop, timeout) must close the sink too, or the GPIO stays an output.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        run(cfg, sink, connect=joystick_class(cfg["input"]), status=status)
    except KeyboardInterrupt:
        pass
    finally:
        sink.close()
