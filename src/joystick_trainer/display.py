"""joystick-trainer-display: full-screen bar chart of the PPM channels the trainer is sending, fed by
its status datagrams (status.py). A separate process that only listens, so it cannot disturb the PPM
output. Laid out for landscape 1280x720 (Raspberry Pi Touch Display 2 turned sideways)."""

import argparse
import json
import os
import socket
import time

from .ppm import CHANNEL_MAX_US, CHANNEL_MID_US, CHANNEL_MIN_US
from .status import DEFAULT_PORT

STALE_S = 0.5           # no datagram for this long = the trainer is not running or not reachable

BACKGROUND = (16, 18, 22)
GRID = (60, 64, 72)
TEXT = (230, 232, 236)
MUTED = (120, 124, 132)
BAR = (64, 156, 255)
BAR_IDLE = (80, 84, 92)
OK = (40, 180, 90)
STOPPED = (220, 60, 50)
WARN = (235, 160, 30)


def receive_latest(sock):
    """Drain the socket and return the newest valid status, or None if nothing arrived."""
    latest = None
    while True:
        try:
            data, _ = sock.recvfrom(65536)
        except BlockingIOError:
            return latest
        try:
            message = json.loads(data)
        except ValueError:
            continue
        if isinstance(message, dict) and isinstance(message.get("channels"), list):
            latest = message


def headline(status, stale):
    """(text, colour) for the state banner."""
    if status is None:
        return "WARTE AUF DATEN - joystick-trainer läuft nicht?", MUTED
    if stale:
        return "KEINE DATEN - joystick-trainer gestoppt?", MUTED
    if not status["sending"]:
        return "GESTOPPT - kein PPM-Signal", STOPPED
    if not status["joystick"]:
        return "SENDET NEUTRAL - Joystick getrennt", WARN
    return "SENDET", OK


def render(pygame, size, status, stale):
    width, height = size
    surface = pygame.Surface(size)
    surface.fill(BACKGROUND)
    big = pygame.font.Font(None, max(24, height // 12))
    small = pygame.font.Font(None, max(18, height // 22))

    header = height // 9
    text, colour = headline(status, stale)
    pygame.draw.rect(surface, colour, (0, 0, width, header))
    label = big.render(text, True, BACKGROUND)
    surface.blit(label, (header // 3, (header - label.get_height()) // 2))
    if status is not None:
        info = small.render(f"{len(status['channels'])} Kanäle · Rahmen {status.get('frame_us', 0) / 1000:g} ms",
                            True, BACKGROUND)
        surface.blit(info, (width - info.get_width() - header // 3, (header - info.get_height()) // 2))
    if status is None:
        return surface

    channels = status["channels"]
    active = status["sending"] and not stale
    margin = width // 40
    axis_w = small.size("2000")[0] + margin
    top = header + small.get_height() + margin * 2
    bottom = height - small.get_height() - margin * 2
    span = bottom - top

    def y_of(us):
        return bottom - (us - CHANNEL_MIN_US) / (CHANNEL_MAX_US - CHANNEL_MIN_US) * span

    for us in (CHANNEL_MIN_US, CHANNEL_MID_US, CHANNEL_MAX_US):
        y = int(y_of(us))
        pygame.draw.line(surface, GRID, (axis_w, y), (width - margin, y), 1 if us != CHANNEL_MID_US else 2)
        tick = small.render(str(us), True, MUTED)
        surface.blit(tick, (axis_w - tick.get_width() - margin // 2, y - tick.get_height() // 2))

    slot = (width - margin - axis_w) / max(1, len(channels))
    bar_w = max(4, int(slot * 0.7))
    for i, us in enumerate(channels):
        x = int(axis_w + i * slot + (slot - bar_w) / 2)
        clamped = min(CHANNEL_MAX_US, max(CHANNEL_MIN_US, us))
        y = min(int(y_of(clamped)), bottom - 4)     # a bar at 1000 stays visible
        pygame.draw.rect(surface, BAR if active else BAR_IDLE, (x, y, bar_w, bottom - y))
        value = small.render(str(us), True, TEXT if active else MUTED)
        surface.blit(value, (x + (bar_w - value.get_width()) // 2, top - value.get_height() - margin // 2))
        name = small.render(f"CH{i + 1}", True, TEXT)
        surface.blit(name, (x + (bar_w - name.get_width()) // 2, bottom + margin // 2))
    return surface


def rotation_for(screen_size, rotate):
    if rotate == "auto":
        return 0 if screen_size[0] >= screen_size[1] else 90
    return int(rotate)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="joystick-trainer-display",
                                     description="Show the PPM channels joystick-trainer is sending.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"UDP port (default {DEFAULT_PORT})")
    parser.add_argument("--listen", default="127.0.0.1",
                        help="address to listen on; 0.0.0.0 to show a trainer running on another machine")
    parser.add_argument("--rotate", choices=["auto", "0", "90", "180", "270"], default="auto",
                        help="auto = turn a portrait screen to landscape; try 270 if the picture is upside down")
    parser.add_argument("--window", action="store_true", help="1280x720 window instead of full screen")
    args = parser.parse_args(argv)

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    pygame.display.init()
    pygame.font.init()
    if args.window:
        screen = pygame.display.set_mode((1280, 720))
    else:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
    pygame.display.set_caption("joystick-trainer")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.listen, args.port))
    sock.setblocking(False)

    status, received = None, 0.0
    clock = pygame.time.Clock()
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q)):
                    return
            latest = receive_latest(sock)
            if latest is not None:
                status, received = latest, time.monotonic()
            rotation = rotation_for(screen.get_size(), args.rotate)
            w, h = screen.get_size()
            canvas = render(pygame, (h, w) if rotation in (90, 270) else (w, h), status,
                            time.monotonic() - received > STALE_S)
            screen.blit(pygame.transform.rotate(canvas, rotation) if rotation else canvas, (0, 0))
            pygame.display.flip()
            clock.tick(30)
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()
