import hid
import argparse

from hid_protocol import PACKET_SIZE, REPORT_ID, checksum, choose_path, parse_hex_color


def build_direct_packet(r: int, g: int, b: int, brightness: int = 4):
    packet = bytearray(PACKET_SIZE)
    packet[0] = REPORT_ID
    packet[3] = 0x06
    packet[4] = 0x08
    packet[5] = 0x00

    packet[8] = 0x01
    packet[9] = brightness & 0xFF
    packet[10] = 0x03
    packet[11] = 0x00
    packet[12] = 0x00
    packet[13] = r & 0xFF
    packet[14] = g & 0xFF
    packet[15] = b & 0xFF

    checksum(packet)
    return bytes(packet)


def main():
    parser = argparse.ArgumentParser(description="Send one direct RGB write packet")
    parser.add_argument(
        "color", type=parse_hex_color, help="Hex color RRGGBB or #RRGGBB"
    )
    parser.add_argument("-b", "--brightness", type=int, default=4)
    parser.add_argument("-i", "--interface", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    r, g, b = args.color
    packet = build_direct_packet(r, g, b, args.brightness)

    print(packet.hex(" "))
    if args.dry_run:
        return

    device = hid.device()
    device.open_path(choose_path(interface=args.interface))
    try:
        written = device.write(packet)
        print("written:", written)
        reply = device.read(PACKET_SIZE, timeout_ms=200)
        if reply:
            print("reply:", bytes(reply).hex(" "))
    finally:
        device.close()


if __name__ == "__main__":
    main()
