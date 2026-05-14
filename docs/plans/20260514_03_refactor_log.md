# Refactor and Review Log - 2026-05-14

## Task Overview
1. Refactor directory structure: Move all Python files from `src/` to root and `src/lib/` to `lib/`.
2. Review and update code to comply with the new structure.
3. Review and ensure MicroPython compliance.

## Analysis of Current Structure
- `src/`: Contains main app and modules (`epaper_bulletin.py`, `bmp_display.py`, `mqtt_handler.py`, `wifi_manager.py`).
- `src/lib/`: Contains libraries (`epaper_7_5_b.py`, `wifi_provision.py`).

## Proposed Structure
- `/`: Main app and modules.
- `/lib/`: Libraries.

## Identified Issues during Review
1. `wifi_provision.py` attempts to import `waveshare` instead of the project-specific `epaper_7_5_b`.
2. Import paths in `epaper_bulletin.py` and other files need to be verified after move.

## Refactor Steps
1. Create `lib/` directory at root.
2. Move contents of `src/lib/` to `lib/`.
3. Move `.py` files from `src/` to root.
4. Remove `src/` directory.
5. Update `wifi_provision.py` to use correct epaper library.
6. Verify all imports.

## MicroPython Compliance Review
- Codes use `utime`, `machine`, `network`, `umqtt.robust`. These are standard MicroPython modules.
- `json` and `os` are standard in MicroPython as well.
- Error handling with `try-except` is present.
- Memory management: Image buffer is large (48KB), but Pico W has 264KB RAM, so it should fit if not too many other things are running.

## Execution
- **Refactor**: All files moved from `src/` to root and `src/lib/` to `lib/`. `src/` directory removed.
- **Import Updates**: 
    - Updated `lib/wifi_provision.py` to import `EPD_7in5_B` from `lib.epaper_7_5_b` instead of `waveshare`.
    - Fixed `config_received` NameError in `lib/wifi_provision.py`.
    - Fixed `sys.print_exception()` call in `epaper_bulletin.py`.
    - Increased `DEFAULT_TIMEOUT_MS` to 30000ms in `epaper_bulletin.py` for better WiFi stability.
- **Compliance Review**: 
    - Verified all modules use MicroPython standard libraries (`utime`, `machine`, `network`, `usocket`, `framebuf`).
    - Verified directory structure is flat at root for main app components, which is standard for MicroPython/Pico projects.
    - Libraries are grouped in `lib/` which is automatically searched by MicroPython.
- **Verification**:
    - Directory structure confirmed.
    - Imports in `epaper_bulletin.py` verified.
    - Resource paths (`./resources/`, `./conf/`, `./configs/`) verified.

## Bug Fixes (2026-05-14)
- **Memory Allocation Error**: Fixed `memory allocation failed` during image loading in `bmp_display.py` by using `f.readinto()` to read data directly into the e-paper's existing buffer. This saves 48KB of RAM by avoiding a redundant copy. Added `gc.collect()` for further stability.
- **MQTT Syntax Error**: Fixed an `invalid syntax` error in `mqtt_handler.py` caused by concatenated f-strings. Replaced all f-strings with `.format()` for better MicroPython compatibility.
- **Display Refresh Logic**: Fixed the `display()` method in `lib/epaper_7_5_b.py`. The original code was incorrectly slicing the image buffer into 100 chunks of 480 bytes, which is incorrect for a row-major `framebuf`. Simplified to send the entire buffer at once.
- **Color Mapping**: Fixed `clear()` and `fill()` color values in the driver and `wifi_provision.py` to use `0` and `1` (standard for 1-bit `framebuf`) instead of `0xFF`.
- **Display Visibility**: Updated `wifi_provision.py` to use black text on a white background for better visibility during the setup process.

## Final Structure
```
/epaper_bulletin/
├── epaper_bulletin.py (Main App)
├── bmp_display.py
├── mqtt_handler.py
├── wifi_manager.py
├── lib/
│   ├── epaper_7_5_b.py
│   └── wifi_provision.py (Refactored to function)
├── conf/
│   └── mqtt.conf
├── configs/
│   └── (wifi_config.json created at runtime)
├── resources/
│   ├── home.bin
│   └── latest.bin
├── plans/
└── test/
```
