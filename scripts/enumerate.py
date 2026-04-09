import hid
from pathlib import Path

TARGET_VID = 0x320F
TARGET_PID = 0x5055


def parse_uevent(path: Path):
    data = {}

    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key] = value

    return data


def sysfs_candidates():
    results = []

    for hidraw in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
        uevent_path = hidraw / "device" / "uevent"
        if not uevent_path.exists():
            continue

        uevent = parse_uevent(uevent_path)
        hid_id = uevent.get("HID_ID", "")
        parts = hid_id.split(":")
        if len(parts) != 3:
            continue

        vendor_id = int(parts[1], 16)
        product_id = int(parts[2], 16)
        if vendor_id != TARGET_VID or product_id != TARGET_PID:
            continue

        iface_dir = (hidraw / "device").resolve().parent
        descriptor_path = (hidraw / "device").resolve() / "report_descriptor"
        report_descriptor = (
            descriptor_path.read_bytes() if descriptor_path.exists() else b""
        )

        results.append(
            {
                "devnode": f"/dev/{hidraw.name}",
                "hidraw": hidraw.name,
                "sysfs": str((hidraw / "device").resolve()),
                "vendor_id": vendor_id,
                "product_id": product_id,
                "interface_number": int(
                    (iface_dir / "bInterfaceNumber").read_text().strip(), 16
                ),
                "interface_subclass": int(
                    (iface_dir / "bInterfaceSubClass").read_text().strip(), 16
                ),
                "interface_protocol": int(
                    (iface_dir / "bInterfaceProtocol").read_text().strip(), 16
                ),
                "report_descriptor_size": len(report_descriptor),
                "report_descriptor_prefix": report_descriptor[:32].hex(" "),
                "hid_name": uevent.get("HID_NAME", ""),
            }
        )
    return results


def hidapi_candidates():
    if hid is None:
        return []
    return list(hid.enumerate(TARGET_VID, TARGET_PID))


def main():
    hidapi = hidapi_candidates()
    sysfs = sysfs_candidates()

    if hidapi:
        print("hidapi:")
        for dev in hidapi:
            print("path      :", dev["path"])
            print("vendor_id :", hex(dev["vendor_id"]))
            print("product_id:", hex(dev["product_id"]))
            print("usage_page:", dev.get("usage_page"))
            print("usage     :", dev.get("usage"))
            print("interface :", dev.get("interface_number"))
            print("product   :", dev.get("product_string"))
            print("serial    :", dev.get("serial_number"))
            print("-" * 60)
    else:
        print("hidapi: no accessible 320F:5055 devices found")
        if hid is None:
            print("hint: install hidapi into the venv first")
        else:
            print("hint: this often means hidraw permissions are blocking access")
        print("-" * 60)

    if sysfs:
        print("sysfs:")
        for dev in sysfs:
            print("devnode   :", dev["devnode"])
            print("vendor_id :", hex(int(dev["vendor_id"])))
            print("product_id:", hex(int(dev["product_id"])))
            print("interface :", dev["interface_number"])
            print("subclass  :", dev["interface_subclass"])
            print("protocol  :", dev["interface_protocol"])
            print("product   :", dev["hid_name"])
            print("descriptor:", dev["report_descriptor_size"], "bytes")
            print("desc head :", dev["report_descriptor_prefix"])
            print("-" * 60)
    else:
        print("sysfs: no 320F:5055 devices found")


if __name__ == "__main__":
    main()
