#!/usr/bin/env bash
set -euo pipefail

SCREEN=""
if [[ "${1:-}" == "--screen" ]]; then
    SCREEN="${2:-}"
    shift 2
fi

WALL="${1:-}"
RGB_PY="${RGB_PY:-/home/spreadsheets600/scripts/rgb.py}"
EXTRACT_PY="${EXTRACT_PY:-/home/spreadsheets600/scripts/extract_color.py}"

if [[ -z "$SCREEN" ]]; then
    echo "Usage: $0 --screen MONITOR /path/to/wallpaper"
    exit 1
fi

if [[ -z "$WALL" || ! -f "$WALL" ]]; then
    echo "Wallpaper not found: $WALL"
    exit 1
fi

if [[ ! -f "$RGB_PY" ]]; then
    echo "rgb.py not found: $RGB_PY"
    exit 1
fi

if [[ ! -f "$EXTRACT_PY" ]]; then
    echo "extract_color.py not found: $EXTRACT_PY"
    exit 1
fi

dms ipc call wallpaper setFor "$SCREEN" "$WALL"

read -r R G B < <(python "$EXTRACT_PY" "$WALL" --format rgb)

HEX=$(printf '#%02x%02x%02x' "$R" "$G" "$B")

sudo python "$RGB_PY" --rgb "$R" "$G" "$B"

printf 'screen:    %s\n' "$SCREEN"
printf 'wallpaper: %s\n' "$WALL"
printf 'keyboard:  %s -> rgb(%d, %d, %d)\n' "$HEX" "$R" "$G" "$B"
