
from PIL import Image, ImageDraw, ImageFont
import os

def create_text_bmp(text_lines, path, font_size=40):
    width = 800
    height = 480
    img = Image.new('1', (width, height), 1)
    draw = ImageDraw.Draw(img)
    
    # Try to find a font
    font = None
    paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf"
    ]
    for p in paths:
        if os.path.exists(p):
            font = ImageFont.truetype(p, font_size)
            break
    if not font:
        font = ImageFont.load_default()

    # Draw lines centered
    y_text = height // 4
    for line in text_lines:
        left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
        w, h = right - left, bottom - top
        draw.text(((width - w) // 2, y_text), line, font=font, fill=0)
        y_text += h + 20

    # Brand at bottom
    try:
        brand_font = ImageFont.truetype(paths[0], 20) if os.path.exists(paths[0]) else ImageFont.load_default()
        brand_text = "Designed by BreadSoft"
        bl, bt, br, bb = draw.textbbox((0, 0), brand_text, font=brand_font)
        draw.text(((width - (br - bl)) // 2, height - 40), brand_text, font=brand_font, fill=0)
    except:
        pass

    img.save(path, format="BMP")
    print(f"Created {path}")

if __name__ == "__main__":
    os.makedirs('resources', exist_ok=True)
    
    # Image 1: Starting
    create_text_bmp(["Starting WiFi", "Provisioning..."], "resources/starting.bmp", font_size=60)
    
    # Image 2: Instructions
    create_text_bmp([
        "WiFi Setup Mode", 
        "",
        "SSID: Pico-Setup", 
        "Password: password123",
        "IP: 192.168.4.1",
        "",
        "Open browser to configure"
    ], "resources/provisioning.bmp", font_size=45)
