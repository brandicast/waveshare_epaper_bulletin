# E-Paper Bulletin Board - Test & Publisher Tools

This directory contains tools for testing the MQTT image publisher functionality.

## MQTT Publisher (mqtt_publisher.js)

Node.js application to publish raw pixel data (800x480 monochrome) to the MQTT broker.

### Installation

```bash
cd test
npm install
```

This installs:
- `mqtt` - MQTT client library
- `jimp` - Image manipulation library

### Raw Pixel Data Format

The publisher converts images to raw pixel data:
- **Resolution**: 800 × 480 pixels
- **Color Depth**: Monochrome (1-bit per pixel)
- **Total Size**: 48,000 bytes (800 × 480 ÷ 8)
- **Bit Format**: 1 = black pixel, 0 = white pixel
- **Byte Order**: MSB first

### Usage

#### Option 1: Publish Image File

```bash
node mqtt_publisher.js <image_file> [server] [port] [topic]
```

**Examples:**
```bash
# Use defaults (server: 172.28.248.138:1883, topic: epaper/bulletin)
node mqtt_publisher.js my_image.png

# Specify server
node mqtt_publisher.js my_image.png 192.168.1.100

# Specify server and port
node mqtt_publisher.js my_image.png 192.168.1.100 1883

# Specify all parameters
node mqtt_publisher.js my_image.png 192.168.1.100 1883 custom/topic
```

**Supported Image Formats:**
- PNG
- JPG/JPEG
- BMP
- GIF
- And any format supported by Jimp

**Important:** The image will be automatically:
1. Resized to 800×480 pixels
2. Converted to grayscale
3. Dithered to pure black and white
4. Converted to raw pixel data

#### Option 2: Generate Test Patterns

```bash
node mqtt_publisher.js --pattern <pattern_name> [text]
```

**Available Patterns:**

1. **Checkerboard** - Black and white checkerboard
   ```bash
   node mqtt_publisher.js --pattern checkerboard
   ```

2. **Gradient** - Horizontal gradient (white to black)
   ```bash
   node mqtt_publisher.js --pattern gradient
   ```

3. **White** - All white (blank display)
   ```bash
   node mqtt_publisher.js --pattern white
   ```

4. **Black** - All black display
   ```bash
   node mqtt_publisher.js --pattern black
   ```

5. **Border** - Black border with white background
   ```bash
   node mqtt_publisher.js --pattern border
   ```

6. **Text** - Text message on white background
   ```bash
   node mqtt_publisher.js --pattern text "Your Message Here"
   ```

### npm Scripts

Convenient npm scripts are available:

```bash
# Checkerboard pattern
npm run test:checkerboard

# Gradient pattern
npm run test:gradient

# Border pattern
npm run test:border

# Text message
npm run test:text

# Image file (requires test_image.png)
npm run test:image
```

### Environment Variables

Override defaults using environment variables:

```bash
MQTT_SERVER=192.168.1.100 \
MQTT_PORT=1883 \
MQTT_TOPIC=display/image \
node mqtt_publisher.js --pattern checkerboard
```

### Examples

#### Test with Checkerboard
```bash
node mqtt_publisher.js --pattern checkerboard
```

#### Send Custom Text
```bash
node mqtt_publisher.js --pattern text "Welcome to E-Paper!"
```

#### Send Real Image
```bash
# Convert your image to 800x480 first (recommended)
convert your_image.jpg -resize 800x480 -colorspace Gray -auto-level test_image.png

# Publish to Pico
node mqtt_publisher.js test_image.png
```

#### Send to Different Broker
```bash
node mqtt_publisher.js my_image.png broker.example.com 1883 epaper/display
```

### Troubleshooting

#### "Cannot find module 'mqtt'"
```bash
npm install mqtt
```

#### "Cannot find module 'jimp'"
```bash
npm install jimp
```

#### Connection timeout
- Verify MQTT broker is running on specified server/port
- Test connectivity: `telnet 172.28.248.138 1883`
- Check firewall rules

#### Image doesn't appear on display
- Verify image was 800×480 pixels before resizing
- Try a simple pattern first: `node mqtt_publisher.js --pattern checkerboard`
- Check Pico serial logs for errors
- Verify MQTT topic matches configuration

#### Image is upside down or rotated
- Jimp handles most orientations automatically
- For manual image correction, use ImageMagick:
  ```bash
  convert image.jpg -rotate 90 fixed_image.jpg
  node mqtt_publisher.js fixed_image.jpg
  ```

### Performance

- **Connection**: ~1-2 seconds
- **Image Conversion**: ~100-500ms (varies with image complexity)
- **Publish**: ~50-200ms
- **Total Time**: ~1-3 seconds from start to display update on Pico

### Creating Images for E-Paper

#### Using ImageMagick

```bash
# Create 800x480 white canvas
convert -size 800x480 xc:white canvas.png

# Add text
convert canvas.png -fill black -font Arial -pointsize 60 \
  -gravity center -annotate +0+0 "Hello World" output.png

# Convert to monochrome
convert output.png -monochrome final.png

# Publish
node mqtt_publisher.js final.png
```

#### Using Python with Pillow

```python
from PIL import Image, ImageDraw, ImageFont

# Create white image
img = Image.new('L', (800, 480), 255)
draw = ImageDraw.Draw(img)

# Add text
draw.text((400, 240), "Hello E-Paper", fill=0)

# Convert to 1-bit and save
img.convert('1').save('final.png')
```

Then publish:
```bash
node mqtt_publisher.js final.png
```

#### Using Python with OpenCV

```python
import cv2
import numpy as np

# Create white image
img = np.ones((480, 800), dtype=np.uint8) * 255

# Add text
cv2.putText(img, "Hello E-Paper", (300, 240),
            cv2.FONT_HERSHEY_SIMPLEX, 2, 0, 3)

# Convert to binary
_, binary = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY)

# Save
cv2.imwrite('final.png', binary)
```

### Binary Data Format Details

If you need to create raw pixel data programmatically:

```javascript
// Create 48,000 byte buffer
const pixelBuffer = Buffer.alloc(48000);

// Set a pixel (x, y) to black
function setPixel(x, y, black = true) {
    const bitIndex = y * 800 + x;
    const byteIndex = Math.floor(bitIndex / 8);
    const bitPosition = 7 - (bitIndex % 8);
    
    if (black) {
        pixelBuffer[byteIndex] |= (1 << bitPosition);
    } else {
        pixelBuffer[byteIndex] &= ~(1 << bitPosition);
    }
}

// Example: Set a pixel at (100, 50) to black
setPixel(100, 50, true);
```

### Testing Checklist

- [ ] Install dependencies: `npm install`
- [ ] Test checkerboard pattern: `npm run test:checkerboard`
- [ ] Test text pattern: `npm run test:text`
- [ ] Create and send real image
- [ ] Verify image appears on Pico display
- [ ] Check Pico sleeps after display update
- [ ] Verify quick updates work (send pattern immediately after previous)

### Support

For issues:
1. Check Pico serial logs: `tail -f /dev/ttyACM0`
2. Verify MQTT connectivity: `mosquitto_sub -h 172.28.248.138 -t epaper/bulletin`
3. Check file sizes: Images should not exceed 48,000 bytes
4. Try test patterns first to isolate image conversion issues

---

**Version**: 1.0
**Last Updated**: 2026-05-14
