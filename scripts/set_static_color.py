import hid
import argparse
from pathlib import Path
from typing import List, Optional


TARGET_VID = 0x320F
TARGET_PID = 0x5055

PACKET_SIZE = 64
REPORT_ID = 0x04

CMD_BEGIN = 0x01
CMD_END = 0x02
CMD_SET_PARAMETER = 0x06

MODE_STATIC = 0x06
BRIGHTNESS_HIGHEST = 0x04
SPEED_NORMAL = 0x03

# This sequence is derived from OpenRGB's EVisionKeyboardController for sibling 320F:* boards.
# It matches the live Linux descriptor shape (report ID 4 on vendor page 0xFF1C), but it is not
# yet capture-verified on 320F:5055 in this environment.


def clamp(x: int):
    return max(0, min(255, int(x)))


def checksum(frame: bytearray):
    total = sum(frame[3:PACKET_SIZE]) & 0xFFFF
    frame[1] = total & 0xFF
    frame[2] = (total >> 8) & 0xFF


def blank_packet():
    packet = bytearray(PACKET_SIZE)
    packet[0] = REPORT_ID
    return packet


def make_begin_packet():
    packet = blank_packet()
    packet[1] = CMD_BEGIN
    packet[2] = 0x00
    packet[3] = CMD_BEGIN
    return bytes(packet)


def make_end_packet():
    packet = blank_packet()
    packet[1] = CMD_END
    packet[2] = 0x00
    packet[3] = CMD_END
    return bytes(packet)


def make_static_packet(r: int, g: int, b: int):
    packet = blank_packet()
    packet[3] = CMD_SET_PARAMETER
    packet[4] = 0x08
    packet[5] = 0x00
    packet[8:16] = bytes(
        [
            MODE_STATIC,
            BRIGHTNESS_HIGHEST,
            SPEED_NORMAL,
            0x00,
            0x00,
            clamp(r),
            clamp(g),
            clamp(b),
        ]
    )
    checksum(packet)
    return bytes(packet)


def make_sequence(r: int, g: int, b: int):
    return [
        make_begin_packet(),
        make_static_packet(r, g, b),
        make_end_packet(),
    ]


def find_path(path_override: Optional[str], interface_number: int):
    if path_override is not None:
        return path_override.encode()

    matches = list(hid.enumerate(TARGET_VID, TARGET_PID))
    for dev in matches:
        print("Candidate:", dev["path"], "iface=", dev.get("interface_number"))
        if dev.get("interface_number") == interface_number:
            return dev["path"]

    raise SystemExit(
        f"No accessible 320F:5055 device found for interface {interface_number}; "
        "if sysfs sees the keyboard but hidapi does not, fix hidraw permissions first"
    )


def write_payload_file(path: Path, frames: List[bytes]):
    path.write_bytes(b"".join(frames))
    print("Wrote payload:", path)


def set_static_color(
    r: int, g: int, b: int, path_override: Optional[str], interface_number: int
):
    path = find_path(path_override, interface_number)
    frames = make_sequence(r, g, b)

    print("Opening:", path)
    dev = hid.device()
    try:
        dev.open_path(path)
    except OSError as exc:
        raise SystemExit(
            f"open failed for {path!r}: {exc}\n"
            "hint: on this host the hidraw nodes are root-owned; add a udev rule or run with sufficient privileges"
        ) from exc

    writes: List[int] = []
    try:
        for frame in frames:
            print("Sending:", frame.hex(" "))
            writes.append(dev.write(frame))
    finally:
        dev.close()
    return writes


def try_sequence(name, frames):
    print(f"=== {name} ===")
    for i, frame in enumerate(frames, 1):
        print(i, frame.hex(" "))


def main():
    parser = argparse.ArgumentParser(
        description="Send a candidate EVision static-color sequence"
    )
    parser.add_argument("r", type=int)
    parser.add_argument("g", type=int)
    parser.add_argument("b", type=int)
    parser.add_argument("--path", help="Exact hidapi path string to open")
    parser.add_argument("--interface", type=int, default=1)
    parser.add_argument(
        "--write-payload",
        type=Path,
        help="Write the generated report sequence instead of sending it",
    )
    args = parser.parse_args()

    frames = make_sequence(args.r, args.g, args.b)
    if args.write_payload is not None:
        write_payload_file(args.write_payload, frames)
        return

    writes = set_static_color(args.r, args.g, args.b, args.path, args.interface)
    print("Writes:", writes)


if __name__ == "__main__":
    try_sequence("Generated sequence", make_sequence(255, 0, 255))
    main()
