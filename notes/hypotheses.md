# EvoFox Ronin RGB Reverse Engineering

## Overview

This document describes the hypothesis, investigation, and final understanding of how the **EvoFox Ronin Wired Mechanical Keyboard (VID: 0x320F, PID: 0x5055)** handles RGB lighting control on Linux.

The goal was to:

- Control RGB lighting from userspace (Python)
- Integrate lighting with wallpaper changes (DMS + Niri)
- Understand the underlying HID protocol without official documentation

---

## Initial Hypothesis

### Assumption 1: OpenRGB Compatibility

The device shares:
- Vendor ID: `0x320F`
- Known association: **EVision-based RGB controllers**

Hypothesis:
> The keyboard uses an **EVision HID protocol**, similar to other keyboards supported by OpenRGB.

---

### Assumption 2: Simple HID Write Model

Initial assumption:
- Send a **single 64-byte HID packet**
- Encode RGB + mode directly
- Keyboard applies immediately

This led to implementing:
- Static packet builder
- Direct `hid.write()` calls

---

## Observations

### Device Enumeration

Two interfaces detected:

| Interface | Purpose |
|----------|--------|
| 0        | Standard keyboard input |
| 1        | Vendor RGB control |

Key findings:

- Vendor interface uses:
  - **Report ID**: `0x04`
  - **Usage Page**: `0xFF1C` (vendor-defined)
  - **Packet Size**: 64 bytes

Conclusion:
> Interface `1` is the correct RGB control endpoint.

---

### HID Descriptor Insight

- Output report length: **63 bytes payload + 1 byte report ID**
- Input report exists → device sends structured replies

Conclusion:
> Protocol is **bidirectional**, not fire-and-forget

---

## Failed Approach (Important)

### V1-Style Packet Model

Tried:

```

[BEGIN]
[SET RGB]
[END]

```

Observed behavior:
- Writes succeed (64 bytes sent)
- Keyboard reacts inconsistently
- Often switches modes instead of color

Conclusion:
> Packet structure is accepted, but **semantics are wrong**

---

## Breakthrough

### EVision V2 Protocol Discovery

From OpenRGB source analysis:

> The device follows **EVision V2 configuration protocol**, NOT V1

---

## Correct Protocol Model

### Packet Structure

| Byte | Meaning |
|------|--------|
| 0    | Report ID (`0x04`) |
| 1-2  | Checksum |
| 3    | Command |
| 4    | Payload length |
| 5-6  | Offset |
| 8+   | Data |

Checksum:
```

sum(bytes[3:63]) & 0xFFFF

```

---

### Command Set

| Command | Value | Purpose |
|--------|------|--------|
| BEGIN_CONFIG | `0x01` | Enter config mode |
| END_CONFIG   | `0x02` | Apply & exit |
| READ_CONFIG  | `0x05` | Read memory |
| WRITE_CONFIG | `0x06` | Write memory |

---

### Profile System

- Keyboard stores multiple profiles
- Active profile must be detected first

```

profile = reply[8]
base_offset = 0x01 + profile * 0x40

```

---

## Configuration Block Layout

18-byte structure:

| Offset | Parameter |
|--------|----------|
| 0x00   | Mode |
| 0x01   | Brightness |
| 0x02   | Speed |
| 0x03   | Direction |
| 0x04   | Random |
| 0x05-0x07 | RGB (R, G, B) |
| 0x08   | Color Offset |
| 0x11   | LED Mode Control |

---

## Key Correction (Critical Insight)

### Incorrect Assumption

```

RGB → PARAM_LED_MODE_COLOR (0x11)

```

Problem:
- Writes outside valid RGB region
- Causes undefined behavior

---

### Correct Mapping

```

RGB → PARAM_MODE_COLOR (0x05, 0x06, 0x07)

```

Conclusion:
> RGB must be written into the **mode color block**, not LED control byte.

---

## Final Working Sequence

```

1. BEGIN_CONFIG
2. READ current profile
3. Compute base offset
4. WRITE 18-byte config block
5. END_CONFIG

```

---

## Validation

Successful behavior observed:

- Immediate color change
- Stable across runs
- No unintended mode switching

Conclusion:
> Protocol implementation is correct

---

## Additional Findings

### Hardware Key Capture

Using `hid-recorder`:

- RGB key emits:
  - Consumer control events (Report ID `0x03`)
- No vendor RGB packets observed

Conclusion:
> Lighting key is handled internally by firmware

---

### WebHID (Browser Tool)

JS files showed:

- Logical config arrays (`a[8]`, `a[9]`, etc.)
- Not raw HID packets

Conclusion:
> JS layer is **abstraction**, not direct protocol mapping

---

## Integration Layer

### RGB Control Script

- Python (`hid`)
- CLI-based (`rgb.py`)
- Accepts RGB + brightness
- Applies via EVision V2 protocol

---

### Wallpaper Integration

Pipeline:

```

DMS → Set Wallpaper
↓
Color Extraction (Python)
↓
RGB Script

```

---

## Color Extraction Strategy

Problem with Matugen:

- Designed for UI palettes
- Often returns muted tones

Solution:

- Custom extractor:
  - Quantization
  - Saturation filtering
  - Brightness boosting
  - Contrast scoring

Goal:
> Pick colors that look good on LEDs, not UI

---

## Remaining Improvements

- udev rule (remove sudo requirement)
- multi-zone RGB (if supported)
- animation modes (wave, breathing)
- color transitions instead of static jumps

---

## Final Conclusion

The EvoFox Ronin keyboard:

- Uses **EVision V2 HID protocol**
- Requires **profile-based configuration writes**
- Cannot be controlled via simple static packets
- Needs full **BEGIN → WRITE → END** sequence

The final implementation:

- Correctly maps RGB parameters
- Uses proper offsets and checksum
- Is stable and reproducible
- Integrates cleanly with Linux workflows