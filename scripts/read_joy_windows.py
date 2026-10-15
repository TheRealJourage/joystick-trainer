"""Read Windows joysticks via winmm (no install). Lists devices, or records min/max per axis."""
import ctypes
import sys
import time
from ctypes import wintypes

winmm = ctypes.windll.winmm


class JOYINFOEX(ctypes.Structure):
    _fields_ = [(n, wintypes.DWORD) for n in (
        "dwSize", "dwFlags", "dwXpos", "dwYpos", "dwZpos", "dwRpos", "dwUpos", "dwVpos",
        "dwButtons", "dwButtonNumber", "dwPOV", "dwReserved1", "dwReserved2")]


class JOYCAPSW(ctypes.Structure):
    _fields_ = [("wMid", wintypes.WORD), ("wPid", wintypes.WORD), ("szPname", wintypes.WCHAR * 32),
                ("wXmin", wintypes.UINT), ("wXmax", wintypes.UINT), ("wYmin", wintypes.UINT),
                ("wYmax", wintypes.UINT), ("wZmin", wintypes.UINT), ("wZmax", wintypes.UINT),
                ("wNumButtons", wintypes.UINT), ("wPeriodMin", wintypes.UINT), ("wPeriodMax", wintypes.UINT),
                ("wRmin", wintypes.UINT), ("wRmax", wintypes.UINT), ("wUmin", wintypes.UINT),
                ("wUmax", wintypes.UINT), ("wVmin", wintypes.UINT), ("wVmax", wintypes.UINT),
                ("wCaps", wintypes.UINT), ("wMaxAxes", wintypes.UINT), ("wNumAxes", wintypes.UINT),
                ("wMaxButtons", wintypes.UINT), ("szRegKey", wintypes.WCHAR * 32),
                ("szOEMVxD", wintypes.WCHAR * 260)]


AXES = ["X", "Y", "Z", "R", "U", "V"]


def read(jid):
    info = JOYINFOEX(dwSize=ctypes.sizeof(JOYINFOEX), dwFlags=0xFF)  # JOY_RETURNALL
    if winmm.joyGetPosEx(jid, ctypes.byref(info)) != 0:
        return None
    return [info.dwXpos, info.dwYpos, info.dwZpos, info.dwRpos, info.dwUpos, info.dwVpos]


def devices():
    found = []
    for jid in range(winmm.joyGetNumDevs()):
        caps = JOYCAPSW()
        if winmm.joyGetDevCapsW(jid, ctypes.byref(caps), ctypes.sizeof(caps)) == 0 and read(jid) is not None:
            found.append((jid, caps.szPname, caps.wNumAxes, caps.wMid, caps.wPid))
    return found


if __name__ == "__main__":
    if len(sys.argv) < 3:
        for d in devices():
            print("id=%d name=%r axes=%d vid=%04x pid=%04x now=%s" % (d + (read(d[0]),)))
        sys.exit(0)
    jid, seconds = int(sys.argv[1]), float(sys.argv[2])
    first = read(jid)
    lo, hi = list(first), list(first)
    end = time.time() + seconds
    while time.time() < end:
        v = read(jid)
        if v:
            lo = [min(a, b) for a, b in zip(lo, v)]
            hi = [max(a, b) for a, b in zip(hi, v)]
        time.sleep(0.02)
    last = read(jid)
    for i, n in enumerate(AXES):
        print("%s: start %5d  min %5d  max %5d  end %5d" % (n, first[i], lo[i], hi[i], last[i]))
