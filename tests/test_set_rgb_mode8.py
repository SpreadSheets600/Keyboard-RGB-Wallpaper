import hid
import argparse

from hid_protocol import PACKET_SIZE, REPORT_ID, choose_path, parse_hex_color


def build_static_packet(r: int, g: int, b: int):
    packet = bytearray(PACKET_SIZE)
    packet[0] = REPORT_ID
    packet[1] = 0x1A
    packet[2] = 0x01
    packet[3] = 0x06
    packet[4] = 0x08
    packet[5] = 0x00

    packet[8] = 0x00
    packet[9] = 0x11
    packet[10] = 0x03
    packet[11] = 0x00
    packet[12] = 0x00
    packet[13] = 0x00
    packet[14] = r & 0xFF
    packet[15] = g & 0xFF
    packet[16] = b & 0xFF

    return bytes(packet)


def main():
    parser = argparse.ArgumentParser(description="Send one static-mode test packet")
    parser.add_argument(
        "color", type=parse_hex_color, help="Hex color RRGGBB or #RRGGBB"
    )
    parser.add_argument("-i", "--interface", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    packet = build_static_packet(*args.color)
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
