import hid
import argparse
from hid_protocol import PACKET_SIZE, REPORT_ID, choose_path, clamp, parse_hex_color


def build_mode16_packet(
    r: int,
    g: int,
    b: int,
    p8: int,
    mode: int,
    brightness: int,
    p11: int,
    p12: int,
):
    packet = bytearray(PACKET_SIZE)
    packet[0] = REPORT_ID
    packet[1] = 0x1A
    packet[2] = 0x01
    packet[3] = 0x06
    packet[4] = 0x08
    packet[5] = 0x00

    packet[8] = p8 & 0xFF
    packet[9] = mode & 0xFF
    packet[10] = brightness & 0xFF
    packet[11] = p11 & 0xFF
    packet[12] = p12 & 0xFF
    packet[13] = clamp(r)
    packet[14] = clamp(g)
    packet[15] = clamp(b)
    return bytes(packet)


def main():
    parser = argparse.ArgumentParser(description="Send custom mode16 RGB packet")
    parser.add_argument(
        "color", type=parse_hex_color, help="Hex color RRGGBB or #RRGGBB"
    )
    parser.add_argument("-i", "--interface", type=int, default=1)
    parser.add_argument("--p8", type=lambda x: int(x, 0), default=0x00)
    parser.add_argument("--mode", type=lambda x: int(x, 0), default=0x11)
    parser.add_argument("--brightness", type=lambda x: int(x, 0), default=0x03)
    parser.add_argument("--p11", type=lambda x: int(x, 0), default=0x00)
    parser.add_argument("--p12", type=lambda x: int(x, 0), default=0x00)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    r, g, b = args.color
    packet = build_mode16_packet(
        r,
        g,
        b,
        p8=args.p8,
        mode=args.mode,
        brightness=args.brightness,
        p11=args.p11,
        p12=args.p12,
    )

    print(packet.hex(" "))
    if args.dry_run:
        return

    device = hid.device()
    device.open_path(choose_path(interface=args.interface))
    try:
        print("written:", device.write(packet))
    finally:
        device.close()


if __name__ == "__main__":
    main()
