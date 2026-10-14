import ctypes
import multiprocessing
import os
import time

from .ppm import frame_edges


class PrintSink:
    """Dry-run sink for development without a GPIO."""

    def __init__(self, **_):
        self._last = None

    def set_channels(self, channels):
        if channels != self._last:
            print(" ".join(f"{c:4d}" for c in channels), flush=True)
            self._last = channels

    def stop(self):
        print("stop", flush=True)

    def close(self):
        pass


def _output_loop(shared, running, pin, params):
    """Software-timed PPM on one GPIO. Bring-up backend: jitter is not measured."""
    import lgpio

    try:
        os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(50))
    except PermissionError:
        pass
    handle = lgpio.gpiochip_open(params["chip"])
    idle = 0 if params["active_high"] else 1
    lgpio.gpio_claim_output(handle, pin, idle)
    try:
        while True:
            if not running.value:
                lgpio.gpio_write(handle, pin, idle)
                time.sleep(0.01)
                continue
            deadline = time.perf_counter_ns()
            for level, duration in frame_edges(list(shared), **{k: v for k, v in params.items() if k != "chip"}):
                lgpio.gpio_write(handle, pin, level)
                deadline += duration * 1000
                while time.perf_counter_ns() < deadline:
                    pass
    finally:
        lgpio.gpio_write(handle, pin, idle)
        lgpio.gpiochip_close(handle)


class LgpioSink:
    def __init__(self, pin, chip=4, channels=8, pulse_us=300, frame_us=22500, active_high=True):
        self._shared = multiprocessing.Array(ctypes.c_int, [1500] * channels, lock=False)
        self._running = multiprocessing.Value(ctypes.c_bool, False, lock=False)
        params = {"pulse_us": pulse_us, "frame_us": frame_us, "active_high": active_high}
        self._chip = chip
        self._process = multiprocessing.Process(
            target=_output_loop, args=(self._shared, self._running, pin, {**params, "chip": chip}), daemon=True
        )
        self._process.start()

    def set_channels(self, channels):
        for i, value in enumerate(channels):
            self._shared[i] = value
        self._running.value = True

    def stop(self):
        self._running.value = False

    def close(self):
        self.stop()
        self._process.terminate()
        self._process.join()


def make_sink(output):
    kind = output.get("sink", "print")
    options = {k: v for k, v in output.items() if k != "sink"}
    if kind == "print":
        return PrintSink(**options)
    if kind == "lgpio":
        return LgpioSink(**options)
    raise ValueError(f"unknown sink {kind!r}")
