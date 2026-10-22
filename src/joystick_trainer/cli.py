import argparse
import signal
import sys
import time

from . import config as config_module
from .joystick import Joystick
from .mapper import Mapper
from .sinks import make_sink


def run(cfg, sink, connect=Joystick):
    mapping = cfg["mapping"]
    mapper = Mapper(mapping)
    axes = [a.source for a in mapping.axes]
    buttons = [b.source for b in mapping.buttons]
    period = 1.0 / cfg["rate_hz"]
    joystick = None
    next_retry = 0.0
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
                else:
                    sink.set_channels(mapper.initial_channels())
            else:
                sink.set_channels(mapper.channels(joystick.state))
        else:
            time.sleep(period)


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
    sink = make_sink(cfg["output"])
    # SIGTERM (systemd stop, timeout) must close the sink too, or the GPIO stays an output.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        run(cfg, sink, connect=joystick_class(cfg["input"]))
    except KeyboardInterrupt:
        pass
    finally:
        sink.close()
