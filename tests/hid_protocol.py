import re
import hid
import argparse
from typing import Optional


VID = 0x320F
PID = 0x5055

REPORT_ID = 0x04
PACKET_SIZE = 64

CMD_BEGIN_CONFIGURE = 0x01
CMD_END_CONFIGURE = 0x02
CMD_READ_CONFIG = 0x05
CMD_WRITE_CONFIG = 0x06

OFFSET_CURRENT_PROFILE = 0x00
OFFSET_FIRST_PROFILE = 0x01
PROFILE_SIZE = 0x40

PARAM_MODE = 0x00
PARAM_BRIGHTNESS = 0x01
PARAM_SPEED = 0x02
PARAM_DIRECTION = 0x03
PARAM_RANDOM = 0x04
PARAM_MODE_COLOR = 0x05
PARAM_COLOR_OFFSET = 0x08
PARAM_LED_MODE_COLOR = 0x11

MODE_STATIC = 0x06


def clamp(x: int, low: int = 0, high: int = 255):
    return max(low, min(high, int(x)))


def checksum(buf: bytearray) -> None:
    csum = sum(buf[3:PACKET_SIZE]) & 0xFFFF
    buf[1] = csum & 0xFF
    buf[2] = (csum >> 8) & 0xFF


def choose_path(interface: int = 1, path_override: Optional[str] = None):
    if path_override:
        return path_override.encode()

    devices = list(hid.enumerate(VID, PID))
    if not devices:
        raise SystemExit("[ ERR ] Target keyboard not found")

    for device in devices:
        if device.get("interface_number") == interface:
            return device["path"]

    return devices[0]["path"]


def query(device: hid.device, cmd: int, offset: int = 0, data: bytes = b""):
    buf = bytearray(PACKET_SIZE)
    buf[0] = REPORT_ID
    buf[3] = cmd
    buf[4] = len(data) & 0xFF
    buf[5] = offset & 0xFF
    buf[6] = (offset >> 8) & 0xFF
    buf[8 : 8 + len(data)] = data
    checksum(buf)

    written = device.write(bytes(buf))
    if written != PACKET_SIZE:
        raise SystemExit(
            f"[ ERR ] Failed to write full packet to keyboard (wrote {written} bytes)"
        )

    reply = device.read(PACKET_SIZE, timeout_ms=500)
    if not reply:
        raise SystemExit("[ ERR ] No reply from keyboard")

    reply = bytes(reply)

    if reply[0] != REPORT_ID:
        raise SystemExit(f"[ ERR ] Unexpected report ID: 0x{reply[0]:02X}")
    if reply[3] != cmd:
        raise SystemExit(f"[ ERR ] Unexpected echoed command: 0x{reply[3]:02X}")
    if reply[5] != (offset & 0xFF) or reply[6] != ((offset >> 8) & 0xFF):
        raise SystemExit("[ ERR ] Unexpected echoed offset")
    if reply[7] != 0:
        raise SystemExit(f"[ ERR ] Keyboard returned error status: 0x{reply[7]:02X}")

    return reply


def read_current_profile(device: hid.device):
    reply = query(device, CMD_READ_CONFIG, offset=OFFSET_CURRENT_PROFILE, data=b"\x00")

    if reply[4] < 1:
        raise SystemExit("[ ERR ] Invalid reply length when reading current profile")

    profile = reply[8]
    if profile > 2:
        profile = 0

    return profile


def build_static_config(r: int, g: int, b: int, brightness: int = 4):
    config = bytearray(18)
    config[PARAM_MODE] = MODE_STATIC
    config[PARAM_BRIGHTNESS] = clamp(brightness, 0, 4)
    config[PARAM_SPEED] = 0x03
    config[PARAM_DIRECTION] = 0x00
    config[PARAM_RANDOM] = 0x00

    config[PARAM_MODE_COLOR + 0] = clamp(r)
    config[PARAM_MODE_COLOR + 1] = clamp(g)
    config[PARAM_MODE_COLOR + 2] = clamp(b)

    config[PARAM_COLOR_OFFSET] = 0x00
    config[PARAM_LED_MODE_COLOR] = 0x00

    return bytes(config)


def parse_hex_color(value: str) -> tuple[int, int, int]:
    value = value.strip()
    if value.startswith("#"):
        value = value[1:]

    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise argparse.ArgumentTypeError("Hex color must look like RRGGBB or #RRGGBB")

    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
