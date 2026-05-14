# E-Paper Bulletin Board - Quick Start Guide

## Prerequisites

- Raspberry Pi Pico W with Waveshare 7.5inch e-Paper B V3
- MicroPython firmware installed
- USB connection to development machine
- MQTT broker accessible on network (IP: 172.28.248.138:1883)

## Setup Steps

### 1. Create Required Directories
```bash
cd /home/brandicast/github/experiment/raspberry_pi/pico/prj/epaper_bulletin
mkdir -p ./configs ./resources
```

### 2. Create WiFi Configuration

If you have a saved WiFi config, rshell will automatically find it. If not:

```bash
cat > ./configs/wifi_config.json << 'EOF'
{"ssid": "YOUR_NETWORK_SSID", "password": "YOUR_NETWORK_PASSWORD"}
EOF
```

Or, the app will automatically start WiFi provisioning if:
- No config file exists, OR
- WiFi connection fails after 3 attempts

**WiFi Provisioning (if needed):**
1. App will display "WiFi Provisioning" on the e-paper screen
2. Connect to AP: `Pico-Setup` (password: `password123`)
3. Open browser to the IP shown on display
4. Enter your WiFi credentials
5. Device will automatically connect and restart

### 3. Prepare Initial Image

Create or generate a raw pixel data file (800x480 pixels, monochrome):

**Raw Pixel Data Format:**
- **Size**: Exactly 48,000 bytes (800 × 480 ÷ 8)
- **Format**: 1-bit monochrome (1 = black, 0 = white)
- **Byte order**: MSB first

**Option A: Using Node.js Publisher**

```bash
cd test
npm install
node mqtt_publisher.js --pattern white > ../resources/home.bin
```

**Option B: Using ImageMagick**

```bash
# Create white image
convert -size 800x480 xc:white -monochrome -depth 1 /tmp/white.png

# Convert to raw pixel data using script (see test/README.md)
cd test
npm install
node mqtt_publisher.js /tmp/white.png > ../resources/home.bin
```

**Option C: Using Python with Pillow**

```python
from PIL import Image
import struct

# Create 800x480 white image
img = Image.new('1', (800, 480), 1)  # 1 = white

# Convert to raw bytes
img_bytes = img.tobytes()

# Save to file
with open('resources/home.bin', 'wb') as f:
    f.write(img_bytes)
```

If no home.bin exists, the app will fail on startup.

### 4. Verify MQTT Configuration

Check that `./conf/mqtt.conf` is properly configured:
```bash
cat ./conf/mqtt.conf
```

Should show:
```
mqtt_server=172.28.248.138
mqtt_port=1883
mqtt_topic=epaper/bulletin
```

### 5. Upload Application Files to Pico

Using rshell:
```bash
# Upload main modules
rshell -p /dev/ttyACM0 cp src/epaper_bulletin.py /pyboard/epaper_bulletin.py
rshell -p /dev/ttyACM0 cp src/wifi_manager.py /pyboard/wifi_manager.py
rshell -p /dev/ttyACM0 cp src/mqtt_handler.py /pyboard/mqtt_handler.py
rshell -p /dev/ttyACM0 cp src/bmp_display.py /pyboard/bmp_display.py

# Create directories on Pico if needed
rshell -p /dev/ttyACM0 mkdir /pyboard/configs
rshell -p /dev/ttyACM0 mkdir /pyboard/resources
rshell -p /dev/ttyACM0 mkdir /pyboard/conf

# Upload configuration files
rshell -p /dev/ttyACM0 cp conf/mqtt.conf /pyboard/conf/mqtt.conf
rshell -p /dev/ttyACM0 cp configs/wifi_config.json /pyboard/configs/wifi_config.json
rshell -p /dev/ttyACM0 cp resources/home.bmp /pyboard/resources/home.bmp
```

### 6. Run Application

Connect via rshell and run:
```bash
rshell -p /dev/ttyACM0
```

In rshell REPL:
```python
import epaper_bulletin
epaper_bulletin.main()
```

Monitor the serial output for debug information.

## Publishing Images via MQTT

The `test/mqtt_publisher.js` Node.js application converts images to raw pixel data and publishes to MQTT.

**Installation:**
```bash
cd test
npm install
```

**Send test pattern:**
```bash
node mqtt_publisher.js --pattern checkerboard
```

**Send real image:**
```bash
node mqtt_publisher.js your_image.png
```

**Send text message:**
```bash
node mqtt_publisher.js --pattern text "Hello Pico"
```

See `test/README.md` for complete usage guide.

**Alternative: Using Python**

```python
import mqtt.client as mqtt
import struct

# Create 48KB raw pixel data (example: all white)
pixel_data = b'\x00' * 48000

# Publish to MQTT
client = mqtt.Client()
client.connect("172.28.248.138", 1883, 60)
client.publish("epaper/bulletin", pixel_data, qos=0)
client.disconnect()

print("Published 48,000 bytes of pixel data")
```

**Alternative: Using mosquitto_pub**

```bash
# Convert image to raw pixel data first, then:
mosquitto_pub -h 172.28.248.138 -t epaper/bulletin -f pixel_data.bin
```

## Troubleshooting

### Display shows nothing
- Check if home.bin exists in ./resources/
- Verify file size is exactly 48,000 bytes
- Create white pattern: `cd test && npm install && node mqtt_publisher.js --pattern white > ../resources/home.bin`
- Try clearing display first: In REPL, `from lib.epaper_7_5_b import EPD_7in5_B; epd = EPD_7in5_B(); epd.clear()`

### WiFi won't connect
- Start WiFi provisioning manually (remove configs/wifi_config.json)
- Check WiFi signal strength
- Verify SSID and password in config
- Monitor logs for error messages

### MQTT not receiving messages
- Verify MQTT broker is running and accessible
- Check topic name in mqtt.conf matches publish topic
- Verify pixel data is exactly 48,000 bytes
- Test MQTT connection: `mosquitto_sub -h 172.28.248.138 -t epaper/bulletin -v`
- Try test pattern: `cd test && node mqtt_publisher.js --pattern checkerboard`

### Image conversion errors (Node.js)
- Verify image format is supported (PNG, JPG, BMP, GIF, etc.)
- Try: `npm install` to ensure dependencies are installed
- Check image has reasonable dimensions (will be resized to 800x480)
- Try test pattern first: `node mqtt_publisher.js --pattern checkerboard`

### App crashes or hangs
- All operations have timeout built-in
- Check Pico has sufficient memory
- Monitor serial logs for error messages
- Try importing modules individually to isolate issues

### Deep sleep not working
- E-paper should enter sleep ~15μA after each display
- Check if epaper library supports sleep() method
- Verify power consumption with multimeter

## Monitoring Application

Watch real-time logs:
```bash
# Monitor serial output
tail -f /dev/ttyACM0

# Or use rshell
rshell -p /dev/ttyACM0  # Then watch output
```

## Power Consumption Expected

- Active display update: ~6-7mA for ~15 seconds
- Deep sleep: ~15μA (extremely low power)
- WiFi connected, idle: ~50-100mA
- WiFi off: <1mA

## File Structure After Deployment

```
/pyboard/
  ├── epaper_bulletin.py      # Main app
  ├── wifi_manager.py         # WiFi module
  ├── mqtt_handler.py         # MQTT module
  ├── bmp_display.py          # Display module
  ├── lib/
  │   ├── epaper_7_5_b.py     # E-paper driver (already there)
  │   └── wifi_provision.py   # WiFi provisioning (already there)
  ├── configs/
  │   └── wifi_config.json    # WiFi credentials
  ├── resources/
  │   ├── home.bmp            # Default image
  │   └── latest.bmp          # Latest received image
  └── conf/
      └── mqtt.conf           # MQTT config (already there)
```

## Next Steps

1. Verify all configuration files are in place
2. Upload application files using rshell
3. Run application and monitor logs
4. Test with a simple MQTT image publish
5. Monitor power consumption and performance

## Support Commands

```bash
# Check if Pico is accessible
lsusb | grep Pico

# Test MQTT broker connectivity
telnet 172.28.248.138 1883

# Monitor MQTT topic
mosquitto_sub -h 172.28.248.138 -t epaper/bulletin -v

# View Pico file system
rshell -p /dev/ttyACM0 ls -la /pyboard/

# Copy files from Pico to host
rshell -p /dev/ttyACM0 cp /pyboard/resources/latest.bmp ./latest_backup.bmp
```

---
For more details, see `20260514_01_implementation.md`
