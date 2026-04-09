# EvoFox Ronin RGB Reverse Engineering – Observations

## Environment

- OS: Linux (Wayland, Niri compositor)
- Shell: zsh
- Tools used:
  - `hidapi` (Python)
  - `hid-recorder`
  - `evtest` / sysfs inspection
  - OpenRGB source code
  - WebHID (browser-based controller JS)
  - DMS (Dank Material Shell)

---

## Device Identification

- Vendor ID: `0x320F`
- Product ID: `0x5055`
- Device Name (sysfs): `Evision RGB Keyboard`

### Enumeration Results

Multiple HID interfaces detected:

| Device | Interface | Usage | Notes |
|--------|----------|------|------|
| `/dev/hidraw1` | 0 | Keyboard | Standard input |
| `/dev/hidraw2` | 1 | Vendor | RGB control |

Observation:

- Interface `1` exposes multiple usage pages
- One vendor-defined usage:
  - Usage Page: `0xFF1C`
  - Usage: `0x92`

Conclusion:
> RGB control is implemented on **interface 1 vendor endpoint**

---

## HID Descriptor Observations

From `hid-recorder`:

- Report ID: `0x04`
- Output report size: `63 bytes`
- Total packet size: `64 bytes`
- Input report also exists

Key detail:

> Device expects **bidirectional communication**

---

## Transport Layer Behavior

### Write Behavior

- `hid.write()` always returns `64`
- No partial writes observed
- Device does not reject packets at transport level

Observation:
> Transport is reliable and not the source of issues

---

### Read Behavior

- Device responds after each command
- Reply format:
  - `reply[0]` → report ID
  - `reply[3]` → echoed command
  - `reply[5:6]` → echoed offset
  - `reply[7]` → status code

Status:

| Value | Meaning |
|------|--------|
| `0x00` | Success |
| Non-zero | Error |

Observation:
> Protocol is **stateful and validated by device**

---

## Early Packet Experiments

### Static Packet Attempt

Tried:

- BEGIN packet
- SET packet
- END packet

Result:

- Keyboard responds
- Behavior inconsistent:
  - Sometimes switches mode
  - Sometimes ignores RGB

Conclusion:
> Packet accepted structurally but not semantically correct

---

## Mode Testing

Manual brute-force:

- Iterated over possible values for mode field
- Observed different lighting behaviors

Findings:

- Certain values trigger:
  - Wave
  - Ripple
  - Breathing
- One value resembled "static"

Observation:
> Mode field is correct but **RGB still not applied properly**

---

## Hardware Key Recording

Using:

```

sudo hid-recorder /dev/hidraw2

```

Observed output:

- Report ID: `0x03`
- Values:
  - `03 6a 05`
  - `03 6a 06`

Interpretation:

- These are **consumer control events**
- Not vendor RGB commands

Conclusion:
> RGB key is handled by firmware, not exposed as HID RGB packets

---

## WebHID Analysis

From browser controller JS:

Observed structure:

```

a[8]  → mode
a[9]  → brightness
a[10] → speed
a[14-16] → RGB

```

Important observation:

- This array is **not raw HID packet**
- It is transformed before sending

Conclusion:
> JS mapping is **logical config layer**, not direct protocol

---

## OpenRGB Source Analysis

Two controller types identified:

### EVision V1

- Direct parameter packet
- Single write operation
- RGB stored inline

### EVision V2

- Configuration memory model
- Profile-based
- Requires command sequence

Observation:

> Device behavior matches **V2, not V1**

---

## Configuration Workflow Observed

Correct sequence:

1. `BEGIN_CONFIG`
2. `READ_CONFIG (current profile)`
3. Compute base offset
4. `WRITE_CONFIG`
5. `END_CONFIG`

Observation:
> Without this sequence, changes are ignored or unstable

---

## Profile System Behavior

- Device stores multiple profiles
- Active profile must be read before writing

Observed:

```

profile = reply[8]

```

Edge case:

- Sometimes profile > expected range
- Needed normalization

Conclusion:
> Profile system is mandatory for correct writes

---

## Parameter Mapping Observations

### Incorrect Mapping (Initial)

- RGB written to:
  - `PARAM_LED_MODE_COLOR (0x11)`

Result:
- No proper color change
- Sometimes undefined behavior

---

### Correct Mapping

- RGB written to:
  - `PARAM_MODE_COLOR (0x05, 0x06, 0x07)`

Result:
- Stable RGB control
- Immediate visible effect

Conclusion:
> Correct parameter offset is critical

---

## Brightness Behavior

Observed:

- Using full range (0–255) produces no meaningful scaling
- Small values (0–4) map to real brightness levels

Conclusion:
> Brightness is **protocol-specific**, not linear RGB scaling

---

## Checksum Behavior

- Required for every packet
- Computed over bytes `[3..63]`
- Stored in bytes `[1,2]`

Observation:

- Incorrect checksum → silent failure

Conclusion:
> Checksum is mandatory

---

## Permissions

Observed error:

```

OSError: open failed

```

Cause:

- `/dev/hidraw*` owned by root

Workaround:

- Run with `sudo`

Side effect:

- `$HOME` changes → script path issues

Conclusion:
> Needs udev rule for proper user access

---

## Matugen Observations

- JSON structure inconsistent across versions
- Requires `--source-color-index` to avoid prompt
- Returns UI-oriented palette

Problems:

- Colors often muted
- Not ideal for keyboard LEDs

Conclusion:
> Better replaced with custom extractor

---

## Custom Color Extraction Observations

Approach:

- Quantize image
- Count color frequency
- Filter low saturation
- Score based on:
  - brightness
  - saturation
  - contrast

Result:

- More vibrant colors
- Better keyboard aesthetics

---

## Integration Observations

### DMS Integration

Command:

```

dms ipc call wallpaper setFor <screen> <path>

```

Works reliably.

---

### Final Pipeline

```

Set Wallpaper → Extract Color → Apply RGB

```

Stable and repeatable.

---

## Key Observations Summary

- Device uses **EVision V2 protocol**
- RGB control requires **configuration workflow**
- Hardware RGB key is **firmware-driven**
- JS tools use **abstraction layer**
- Correct offsets are essential
- Checksum must be valid
- Profile system must be respected
- Matugen is not optimal for LED color
