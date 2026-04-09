import hid
import argparse
from pathlib import Path
from typing import Iterable, List, Optional


TARGET_VID = 0x320F
TARGET_PID = 0x5055
PACKET_SIZE = 64


def candidates():
    return list(hid.enumerate(TARGET_VID, TARGET_PID))


def find_path(path_override: Optional[str], interface_number: Optional[int]):
    if path_override is not None:
        return path_override.encode()

    matches = candidates()
    for dev in matches:
        print(
            "Candidate:",
            dev["path"],
            "iface=",
            dev.get("interface_number"),
            "usage_page=",
            dev.get("usage_page"),
            "usage=",
            dev.get("usage"),
        )

    if interface_number is None:
        if len(matches) == 1:
            return matches[0]["path"]
        print("Multiple candidate interfaces found; pass --interface or --path")

    for dev in matches:
        if dev.get("interface_number") == interface_number:
            return dev["path"]

    print(f"No candidate found for interface {interface_number}")


def load_frames(payload_path: Path) -> Iterable[bytes]:
    data = payload_path.read_bytes()

    if not data:
        print(f"Payload is empty: {payload_path}")

    if len(data) % PACKET_SIZE != 0:
        print(
            f"Payload length {len(data)} is not a multiple of {PACKET_SIZE}; "
            "store one or more full HID reports"
        )

    for offset in range(0, len(data), PACKET_SIZE):
        yield data[offset : offset + PACKET_SIZE]


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay one or more raw HID reports")
    parser.add_argument(
        "payload", type=Path, help="Binary payload file; one or more 64-byte reports"
    )
    parser.add_argument("--path", help="Exact hidapi path string to open")
    parser.add_argument(
        "--interface", type=int, default=1, help="Candidate interface number"
    )
    parser.add_argument("--method", choices=("output", "feature"), default="output")
    args = parser.parse_args()

    path = find_path(args.path, args.interface)
    frames = list(load_frames(args.payload))

    print("Opening:", path)
    dev = hid.device()

    try:
        dev.open_path(path)

    except OSError as exc:
        print(
            f"open failed for {path!r}: {exc}\n"
            "hint: on this host the hidraw nodes are root-owned; add a udev rule or run with sufficient privileges"
        )

    try:
        for index, frame in enumerate(frames, start=1):
            print(f"Frame {index}: {frame.hex(' ')}")

            if args.method == "output":
                written = dev.write(frame)
            else:
                written = dev.send_feature_report(frame)

            print("Bytes written:", written)
    finally:
        dev.close()


if __name__ == "__main__":
    main()
