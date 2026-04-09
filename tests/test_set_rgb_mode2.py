import hid
import argparse


from hid_protocol import (
    CMD_BEGIN_CONFIGURE,
    CMD_END_CONFIGURE,
    CMD_WRITE_CONFIG,
    OFFSET_FIRST_PROFILE,
    PROFILE_SIZE,
    build_static_config,
    choose_path,
    parse_hex_color,
    query,
    read_current_profile,
)


def main():
    parser = argparse.ArgumentParser(description="Set static RGB using profile write")
    parser.add_argument(
        "color", type=parse_hex_color, help="Hex color RRGGBB or #RRGGBB"
    )
    parser.add_argument("-b", "--brightness", type=int, default=4)
    parser.add_argument("-i", "--interface", type=int, default=1)
    parser.add_argument(
        "--profile",
        type=int,
        choices=[0, 1, 2],
        help="Override profile index; defaults to current active profile",
    )
    args = parser.parse_args()

    r, g, b = args.color

    device = hid.device()
    device.open_path(choose_path(interface=args.interface))

    try:
        query(device, CMD_BEGIN_CONFIGURE)

        profile = args.profile
        if profile is None:
            profile = read_current_profile(device)

        base = OFFSET_FIRST_PROFILE + profile * PROFILE_SIZE
        config = build_static_config(r, g, b, brightness=args.brightness)

        query(device, CMD_WRITE_CONFIG, offset=base, data=config)
        query(device, CMD_END_CONFIGURE)
    finally:
        device.close()


if __name__ == "__main__":
    main()
