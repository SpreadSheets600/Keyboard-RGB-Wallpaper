import re
import hid
import argparse


VID = 0x320F  # Keyboard vendor ID
PID = 0x5055  # Keyboard product ID

REPORT_ID = 0x04  # HID report ID used by the keyboard
PACKET_SIZE = 64  # Total HID packet size

CMD_BEGIN_CONFIGURE = 0x01  # Begin configuration session
CMD_END_CONFIGURE = 0x02  # End configuration session
CMD_READ_CONFIG = 0x05  # Read configuration block
CMD_WRITE_CONFIG = 0x06  # Write configuration block

OFFSET_CURRENT_PROFILE = 0x00  # Offset used to read current profile
OFFSET_FIRST_PROFILE = 0x01  # Offset where profile data begins
PROFILE_SIZE = 0x40  # Size of one profile block

PARAM_MODE = 0x00  # Lighting mode
PARAM_BRIGHTNESS = 0x01  # Brightness field
PARAM_SPEED = 0x02  # Speed field
PARAM_DIRECTION = 0x03  # Direction field
PARAM_RANDOM = 0x04  # Random-color flag
PARAM_MODE_COLOR = 0x05  # RGB color starts here: R, G, B
PARAM_COLOR_OFFSET = 0x08  # Color offset field
PARAM_LED_MODE_COLOR = 0x11  # Extra mode-color control byte, not raw RGB

MODE_STATIC = 0x06  # Static lighting mode


def clamp(x, low=0, high=255):
    """Clamp a numeric value into the given range."""
    return max(low, min(high, int(x)))


def checksum(buf):
    """Calculate and write the checksum into bytes 1 and 2."""
    csum = sum(buf[3:PACKET_SIZE]) & 0xFFFF
    buf[1] = csum & 0xFF
    buf[2] = (csum >> 8) & 0xFF


def choose_path(interface=1):
    """Find the HID path for the keyboard."""
    devices = list(hid.enumerate(VID, PID))

    if not devices:
        raise SystemExit("[ ERR ] Target keyboard not found")

    for device in devices:
        if device.get("interface_number") == interface:
            return device["path"]

    return devices[0]["path"]


def query(device, cmd, offset=0, data=b""):
    """Send one command packet and read the reply."""
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


def read_current_profile(device):
    """Read the currently active profile number."""
    # Note: sending one dummy byte here is safer for this read path.
    reply = query(device, CMD_READ_CONFIG, offset=OFFSET_CURRENT_PROFILE, data=b"\x00")

    if reply[4] < 1:
        raise SystemExit("[ ERR ] Invalid reply length when reading current profile")

    profile = reply[8]

    # Note: normalize unexpected profile values instead of using them blindly.
    if profile > 2:
        profile = 0

    return profile


def build_config(r, g, b, brightness):
    """Build the profile config block for static RGB mode."""
    config = bytearray(18)

    config[PARAM_MODE] = MODE_STATIC

    # Note: this protocol uses small brightness values, not generic 0..255.
    config[PARAM_BRIGHTNESS] = clamp(brightness, 0, 4)

    # Static mode does not need movement/random settings.
    config[PARAM_SPEED] = 0x03
    config[PARAM_DIRECTION] = 0x00
    config[PARAM_RANDOM] = 0x00

    # Note: the raw RGB bytes belong at PARAM_MODE_COLOR (0x05, 0x06, 0x07).
    config[PARAM_MODE_COLOR + 0] = clamp(r)
    config[PARAM_MODE_COLOR + 1] = clamp(g)
    config[PARAM_MODE_COLOR + 2] = clamp(b)

    config[PARAM_COLOR_OFFSET] = 0x00

    # Note: this is a control byte, not the RGB storage area.
    config[PARAM_LED_MODE_COLOR] = 0x00

    return bytes(config)


def set_rgb(r, g, b, brightness, interface):
    """Open the device, update the current profile, and apply the new static RGB color."""
    path = choose_path(interface)
    device = hid.device()
    device.open_path(path)

    query(device, CMD_BEGIN_CONFIGURE)

    profile = read_current_profile(device)
    base = OFFSET_FIRST_PROFILE + profile * PROFILE_SIZE

    config = build_config(r, g, b, brightness)

    query(device, CMD_WRITE_CONFIG, offset=base, data=config)
    query(device, CMD_END_CONFIGURE)

    device.close()


def get_hex_color(value):
    """Parse a hex color in RRGGBB or #RRGGBB form."""
    value = value.strip()

    if value.startswith("#"):
        value = value[1:]

    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        raise argparse.ArgumentTypeError("Hex color must look like RRGGBB or #RRGGBB")

    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def main():
    parser = argparse.ArgumentParser(description="Set the RGB lighting of the keyboard")
    parser.add_argument(
        "color",
        type=get_hex_color,
        help="Hex color to set (format: RRGGBB or #RRGGBB)",
    )
    parser.add_argument(
        "-b",
        "--brightness",
        type=int,
        default=4,
        help="Brightness level for the keyboard protocol (0-4, default: 4)",
    )
    parser.add_argument(
        "-i",
        "--interface",
        type=int,
        default=1,
        help="HID interface number to use (default: 1)",
    )

    args = parser.parse_args()

    r, g, b = args.color
    set_rgb(r, g, b, args.brightness, args.interface)


if __name__ == "__main__":
    main()
