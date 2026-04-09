VID:PID = `320F:5055`

# Phase 1 Summary

The keyboard exposes two HID interfaces on Linux. Interface `0` looks like the standard typing path. Interface `1` exposes a vendor-defined report on usage page `0xFF1C` and is the strongest RGB-control candidate.

## Candidate Interfaces

- `/dev/hidraw1` interface `0`, subclass `1`, protocol `1` (`Keyboard`): likely standard keyboard input
- `/dev/hidraw2` interface `1`, subclass `1`, protocol `2` (`Mouse`): strongest vendor/RGB candidate

## `lsusb -v -d 320f:5055`

This required elevated access because sandboxed `lsusb` failed with `unable to initialize libusb: -99`.

```text
Bus 001 Device 007: ID 320f:5055 Evision RGB Keyboard
  bcdUSB               2.00
  idVendor           0x320f Evision
  idProduct          0x5055 RGB Keyboard
  bcdDevice            1.06
  iManufacturer           1 Evision
  iProduct                2 RGB Keyboard
  bNumConfigurations      1
  bNumInterfaces          2

Interface 0:
  bInterfaceNumber        0
  bInterfaceClass         3 Human Interface Device
  bInterfaceSubClass      1 Boot Interface Subclass
  bInterfaceProtocol      1 Keyboard
  wDescriptorLength      79

Interface 1:
  bInterfaceNumber        1
  bInterfaceClass         3 Human Interface Device
  bInterfaceSubClass      1 Boot Interface Subclass
  bInterfaceProtocol      2 Mouse
  wDescriptorLength     194
```

## Sysfs / hidraw Evidence

```text
/sys/class/hidraw/hidraw1
  HID_ID=0003:0000320F:00005055
  HID_NAME=Evision RGB Keyboard
  interface=0
  protocol=1

/sys/class/hidraw/hidraw2
  HID_ID=0003:0000320F:00005055
  HID_NAME=Evision RGB Keyboard
  interface=1
  protocol=2
```

### Interface 0 report descriptor

```text
05 01 09 06 a1 01 ... 95 40 75 08 b1 02 c0
```

Interpretation:

- Standard keyboard usage page `0x01/0x06`
- Boot keyboard style descriptor
- Contains a `64`-byte feature report, but no vendor page output report

### Interface 1 report descriptor

```text
05 01 09 06 a1 01 85 01 ...
05 01 09 80 a1 01 85 02 ...
05 0c 09 01 a1 01 85 03 ...
06 1c ff 09 92 a1 01 85 04 ... 95 3f 91 00 ... 95 3f 81 00 ...
05 01 09 02 a1 01 85 05 ...
```

Interpretation:

- Multiple report IDs (`0x01`..`0x05`)
- Vendor-defined usage page `0xFF1C`
- Report ID `0x04`
- `0x3F` (`63`) byte output report and matching `63` byte input report
- This is the best match for a vendor RGB control channel

## `hidapi` Enumeration

Python `hidapi` in the local venv only returned devices when run with elevated device visibility. It reported:

```text
{'path': b'1-4.2:1.0', 'vendor_id': 12815, 'product_id': 20565, 'interface_number': 0}
{'path': b'1-4.2:1.1', 'vendor_id': 12815, 'product_id': 20565, 'interface_number': 1}
```

## Access Blocker

The device nodes are currently root-only:

```text
crw------- root root /dev/hidraw1
crw------- root root /dev/hidraw2
```

That means the protocol can be inspected from sysfs and enumerated, but live packet replay from this environment is blocked until a udev rule or root access is provided.
