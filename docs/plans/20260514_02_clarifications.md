# Implementation Update - Clarifications Applied
Date: 2026-05-14
Version: 1.1

## Summary of Changes

Based on user clarifications, the following changes have been applied to the implementation:

### 1. Binary Format: BMP → Raw Pixel Data ✅

**Changed:**
- Image format from BMP to raw monochrome pixel data
- File extension from `.bmp` to `.bin`
- File paths updated: `latest.bmp` → `latest.bin`, `home.bmp` → `home.bin`

**New Format Specification:**
- **Resolution**: 800 × 480 pixels
- **Color Depth**: Monochrome (1-bit per pixel)
- **Total Size**: Exactly 48,000 bytes (800 × 480 ÷ 8)
- **Bit Encoding**: 1 = black pixel, 0 = white pixel
- **Byte Order**: MSB first (most significant bit first)

**Modified Files:**
- `src/bmp_display.py` - Completely rewritten to handle raw pixel data
- `src/mqtt_handler.py` - Updated path from `latest.bmp` to `latest.bin`, file size validation to exactly 48KB
- `src/epaper_bulletin.py` - Updated file paths to use `.bin` extension

### 2. MQTT Behavior: Default umqtt ✅

**Status:** Already implemented
- Using `umqtt.robust` with default check_msg() behavior
- Non-blocking message checking every 1 second in main loop
- If MQTT fails (not due to WiFi disconnect), automatically keeps trying
- Default reconnection behavior of umqtt.robust is used

**Code:**
- `src/mqtt_handler.py` line 122: `self.client.check_msg()`
- Main loop: 1-second check interval for messages
- Automatic retry logic on connection failure

### 3. App Lifecycle: Continuous Listening ✅

**Status:** Already implemented
- Application keeps running indefinitely
- Main loop continuously checks for MQTT messages
- No sleep or termination unless interrupted
- Graceful shutdown only on KeyboardInterrupt or fatal error

**Code:**
- `src/epaper_bulletin.py` line 330+: Infinite while loop
- Line 375+: Continuous message checking

### 4. Test Publisher: Node.js for Raw Pixel Data ✅

**Created:**
- `test/mqtt_publisher.js` - Comprehensive Node.js MQTT publisher
- `test/package.json` - npm dependencies (mqtt, jimp)
- `test/README.md` - Complete usage documentation

**Features:**
- Converts images to raw pixel data
- Generates test patterns (checkerboard, gradient, border, text, white, black)
- Supports PNG, JPG, BMP, GIF formats
- Automatic image resizing to 800×480
- Automatic conversion to grayscale and monochrome
- Full MQTT publishing with error handling

**Usage Examples:**
```bash
# Test patterns
node mqtt_publisher.js --pattern checkerboard
node mqtt_publisher.js --pattern text "Hello Pico"

# Image conversion
node mqtt_publisher.js my_image.png

# Custom MQTT settings
node mqtt_publisher.js my_image.png 192.168.1.100 1883 custom/topic
```

### 5. WiFi Configuration Format: JSON (No Change) ✅

**Status:** Kept as-is
- `wifi_provision.py` uses JSON format: `./configs/wifi_config.json`
- Already confirmed in code review
- No changes needed

**Configuration:**
```json
{"ssid": "NETWORK_NAME", "password": "NETWORK_PASSWORD"}
```

## Detailed Changes by File

### src/bmp_display.py (Complete Rewrite)
- Removed: BMP header parsing, DIB header validation
- Added: Raw pixel data direct buffer copy
- Validates file size (48,000 bytes ± padding with white)
- Simplified error handling for pixel data loading
- Updated documentation with binary format specification

### src/mqtt_handler.py (Minor Updates)
- Changed `MAX_BINARY_SIZE = 48000` with exact byte validation
- Changed file path: `LATEST_BMP_PATH` → `LATEST_PIXEL_PATH` (`latest.bmp` → `latest.bin`)
- Updated size validation to warn if not exactly 48KB
- Added documentation about expected raw pixel format

### src/epaper_bulletin.py (Path Updates)
- Changed `latest.bmp` → `latest.bin` (line 256)
- Changed `home.bmp` → `home.bin` (line 257)
- Updated error message to specify raw pixel data format

### test/mqtt_publisher.js (New File)
- 300+ lines of Node.js code
- Full image-to-pixel conversion pipeline
- Test pattern generator
- MQTT publishing with connection handling
- Comprehensive error messages

### test/package.json (New File)
- Dependencies: `mqtt` (5.0.0), `jimp` (0.22.8)
- npm scripts for quick pattern testing
- Version 1.0.0

### test/README.md (New File)
- 300+ lines of complete usage documentation
- Installation instructions
- Usage examples for all features
- Binary format specification
- Image creation guides (ImageMagick, Python PIL, OpenCV)
- Troubleshooting section

### Documentation Updates
- `plans/QUICK_START.md` - Updated image preparation and publishing sections
- `plans/VALIDATION_CHECKLIST.md` - Updated resource file specifications

## Impact on Deployment

### What Changed for End Users

1. **Initial Image Setup**
   - **Before**: Create/provide `home.bmp` (800×480 BMP file)
   - **After**: Create/provide `home.bin` (exactly 48,000 bytes of raw pixel data)
   - **Easy Solution**: Use Node.js publisher to generate: `node mqtt_publisher.js --pattern white > home.bin`

2. **MQTT Publishing**
   - **Before**: Send BMP file directly
   - **After**: Send raw pixel data (use Node.js publisher or convert manually)
   - **Easy Solution**: Use provided Node.js tool

3. **File Locations**
   - `./resources/latest.bmp` → `./resources/latest.bin`
   - `./resources/home.bmp` → `./resources/home.bin`
   - Pico will look for `.bin` files

### What Stayed the Same

- WiFi configuration format (JSON)
- MQTT configuration format (key=value)
- Application flow and boot sequence
- Error handling and timeout protection
- Deep sleep functionality
- Module architecture

## Testing Checklist Updates

Before deployment verify:

- [ ] Node.js test publisher installed and working
- [ ] Can generate test patterns: `node mqtt_publisher.js --pattern checkerboard`
- [ ] Can convert images to raw pixels
- [ ] home.bin created (48,000 bytes exactly)
- [ ] MQTT publisher can send data to broker
- [ ] Pico displays pixel data correctly

## Backward Compatibility

**NOT backward compatible with BMP-based setup**
- Old `home.bmp` files will not work
- Old MQTT BMP publishers will not work
- Migrate by regenerating as raw pixel data

**Migration Path:**
1. Generate raw pixel data using Node.js tool
2. Replace `.bmp` files with `.bin` files
3. Update any custom MQTT publishers to use raw format
4. Redeploy application

## Performance Notes

**Raw Pixel Data Advantages:**
- Smaller final file (no BMP header overhead)
- Faster processing (no BMP parsing)
- Direct buffer copy to display (minimal overhead)
- Exact file size (48,000 bytes always)

**Expected Timings:**
- Image conversion: 100-500ms (on host, Node.js)
- MQTT publish: 50-200ms
- Display update: 10-20 seconds (e-paper refresh)
- Total time: ~11-21 seconds per image

## Verification Commands

Test the implementation:

```bash
# Test Node.js publisher
cd test && npm install
node mqtt_publisher.js --pattern checkerboard

# Generate home.bin
node mqtt_publisher.js --pattern white > ../resources/home.bin
ls -la ../resources/home.bin  # Should be exactly 48000 bytes

# Test MQTT subscription
mosquitto_sub -h 172.28.248.138 -t epaper/bulletin | xxd | head -20

# Check Pico logs
tail -f /dev/ttyACM0
```

## Documentation Alignment

All documentation has been updated:
- ✅ QUICK_START.md - Image preparation and publishing sections
- ✅ VALIDATION_CHECKLIST.md - Resource specifications
- ✅ test/README.md - Complete publisher guide
- ✅ Code comments - Updated file formats and expectations

## Summary

Implementation now fully supports:
1. **Raw pixel data** instead of BMP images
2. **Default umqtt behavior** for MQTT
3. **Continuous running** application
4. **Node.js test publisher** for easy image generation and publishing
5. **JSON WiFi config** (unchanged from wifi_provision.py)

All changes are backward incompatible with BMP version, but significantly simplify the pipeline and improve performance.

---
**Updated By**: Clarification Response
**Date**: 2026-05-14
**Version**: 1.1
