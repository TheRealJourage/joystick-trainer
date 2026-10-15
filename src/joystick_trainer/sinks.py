import ctypes
import multiprocessing
import os
import signal
import subprocess
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


def _output_loop(shared, running, shutdown, pin, params):
    """Software-timed PPM on one GPIO. Bring-up backend: jitter is not measured.

    Exits via the `shutdown` flag (set by close() or SIGTERM) instead of an exception, so the cleanup
    below always runs: raising from a signal handler inside the timing loop skipped it in tests.
    """
    import lgpio

    signal.signal(signal.SIGTERM, lambda *_: setattr(shutdown, "value", True))
    try:
        os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(50))
    except PermissionError:
        pass
    handle = lgpio.gpiochip_open(params["chip"])
    idle = 0 if params["active_high"] else 1
    lgpio.gpio_claim_output(handle, pin, idle)
    try:
        while not shutdown.value:
            if not running.value:
                lgpio.gpio_write(handle, pin, idle)
                time.sleep(0.01)
                continue
            deadline = time.perf_counter_ns()
            for level, duration in frame_edges(list(shared), **{k: v for k, v in params.items() if k != "chip"}):
                if shutdown.value:
                    break
                lgpio.gpio_write(handle, pin, level)
                deadline += duration * 1000
                while time.perf_counter_ns() < deadline:
                    pass
    finally:
        lgpio.gpio_write(handle, pin, idle)
        # Releasing the line keeps it an output at its last level on the Pi 5; hand it back as input.
        lgpio.gpio_claim_input(handle, pin)
        lgpio.gpiochip_close(handle)


class LgpioSink:
    def __init__(self, pin, chip=4, channels=8, pulse_us=300, frame_us=22500, active_high=True):
        self._shared = multiprocessing.Array(ctypes.c_int, [1500] * channels, lock=False)
        self._running = multiprocessing.Value(ctypes.c_bool, False, lock=False)
        self._shutdown = multiprocessing.Value(ctypes.c_bool, False, lock=False)
        params = {"pulse_us": pulse_us, "frame_us": frame_us, "active_high": active_high}
        self._chip = chip
        self._process = multiprocessing.Process(
            target=_output_loop, args=(self._shared, self._running, self._shutdown, pin, {**params, "chip": chip}),
            daemon=True,
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
        self._shutdown.value = True
        self._process.join(1)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join()


class PioSink:
    """PPM from the RP1 PIO through the native helper (native/ppm_pio, built on the Pi)."""

    def __init__(self, pin, helper="native/ppm_pio", channels=8, pulse_us=300, frame_us=22500,
                 active_high=True, pio_hz=None):
        command = [helper, "--gpio", str(pin), "--channels", str(channels),
                   "--pulse-us", str(pulse_us), "--frame-us", str(frame_us)]
        if not active_high:
            command.append("--active-low")
        if pio_hz is not None:
            command += ["--pio-hz", str(pio_hz)]
        self._process = subprocess.Popen(command, stdin=subprocess.PIPE, text=True, bufsize=1)
        self._last = None

    def _send(self, line):
        try:
            self._process.stdin.write(line + "\n")
            self._process.stdin.flush()
        except BrokenPipeError:
            raise RuntimeError("ppm_pio helper exited") from None

    def set_channels(self, channels):
        if channels != self._last:
            self._send(" ".join(str(c) for c in channels))
            self._last = list(channels)

    def stop(self):
        self._send("stop")
        self._last = None

    def close(self):
        try:
            self._send("quit")
        except RuntimeError:
            pass
        self._process.stdin.close()
        self._process.wait(timeout=2)


def make_sink(output):
    kind = output.get("sink", "print")
    options = {k: v for k, v in output.items() if k != "sink"}
    if kind == "print":
        return PrintSink(**options)
    if kind == "pio":
        return PioSink(**options)
    if kind == "lgpio":
        return LgpioSink(**options)
    raise ValueError(f"unknown sink {kind!r}")
