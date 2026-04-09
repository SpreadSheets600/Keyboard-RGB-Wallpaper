import sys
import hid
import argparse
from typing import Optional
from dataclasses import dataclass

from hid_protocol import PACKET_SIZE, REPORT_ID, choose_path, clamp, parse_hex_color


@dataclass(frozen=True)
class HidCandidate:
    path: bytes
    usage: Optional[int]
    usage_page: Optional[int]
    product_string: Optional[str]
    interface_number: Optional[int]


def enumerate_candidates():
    candidates: list[HidCandidate] = []
    for dev in hid.enumerate(0x320F, 0x5055):
        candidates.append(
            HidCandidate(
                path=dev["path"],
                interface_number=dev.get("interface_number"),
                usage_page=dev.get("usage_page"),
                usage=dev.get("usage"),
                product_string=dev.get("product_string"),
            )
        )
    return candidates


def print_candidates():
    candidates = enumerate_candidates()
    if not candidates:
        print("No candidates found.")
        return

    for candidate in candidates:
        print(
            f"path={candidate.path!r} iface={candidate.interface_number} "
            f"usage_page={candidate.usage_page} usage={candidate.usage} "
            f"product={candidate.product_string!r}"
        )


def build_static_packet(r: int, g: int, b: int, brightness: int):
    packet = bytearray(PACKET_SIZE)

    packet[0] = REPORT_ID
    packet[1] = 0x1A
    packet[2] = 0x01
    packet[3] = 0x06
    packet[4] = 0x08
    packet[5] = 0x00

    packet[8] = 0x06
    packet[9] = brightness & 0xFF
    packet[10] = 0x03
    packet[11] = 0x00
    packet[12] = 0x00
    packet[13] = clamp(r)
    packet[14] = clamp(g)
    packet[15] = clamp(b)

    return bytes(packet)


def main():
    parser = argparse.ArgumentParser(description="Set static RGB on 320F:5055 keyboard")
    parser.add_argument(
        "color", nargs="?", type=parse_hex_color, help="Hex color RRGGBB"
    )
    parser.add_argument("-i", "--interface", type=int, default=1)
    parser.add_argument("-b", "--brightness", type=int, default=4)
    parser.add_argument("--path", help="Explicit hidapi path")
    parser.add_argument(
        "--list", action="store_true", help="List matching HID candidates"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.list:
        print_candidates()
        return 0

    if args.color is None:
        parser.error("provide COLOR or use --list")

    r, g, b = args.color
    packet = build_static_packet(r, g, b, args.brightness)
    path = choose_path(interface=args.interface, path_override=args.path)

    print(f"Using path: {path!r}")
    print(packet.hex(" "))

    if args.dry_run:
        return 0

    device = hid.device()
    device.open_path(path)
    try:
        print("written:", device.write(packet))
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        device.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
