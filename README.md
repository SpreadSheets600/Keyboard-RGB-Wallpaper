# EvoFox Ronin RGB Control

Minimal userspace control for **EvoFox Ronin (VID: 320F, PID: 5055)** using raw HID (EVision V2 protocol).

## Working

![](.github/Video.gif)


## Features

- Static RGB control via Python (`hidapi`)
- Wallpaper → color → keyboard pipeline
- Works on Wayland (Niri, DMS)
- No OpenRGB required

## Usage

```bash
python rgb.py #00ffcc
````

With wallpaper sync:

```bash
./setwall.sh --screen eDP-1 /path/to/wallpaper.jpg
```

## Requirements

* Python + `hid` (`hidapi`)
* (Optional) Pillow for color extraction
* Access to `/dev/hidraw*` (udev rule recommended)

## Architecture

```mermaid
flowchart TD
    A[Wallpaper Change] --> B[setwall.sh]
    B --> C[Color Extractor]
    C --> D[RGB Values]
    D --> E[rgb.py]
    E --> F[HID Packet Builder]
    F --> G[EVision V2 Protocol]
    G --> H[Keyboard RGB]
```

## Protocol

```mermaid
sequenceDiagram
    participant App
    participant Keyboard

    App->>Keyboard: BEGIN_CONFIG (0x01)
    App->>Keyboard: READ_CONFIG (profile)
    App->>Keyboard: WRITE_CONFIG (RGB + mode)
    App->>Keyboard: END_CONFIG (0x02)
```

## Special Thanks

- [EvoFox Ronin WebHID Controller](https://evofox.rdmctmzt.com/)
- [OpenRGB](https://openrgb.org/) (For Protocol Hints)