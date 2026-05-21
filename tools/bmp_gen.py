#!/usr/bin/env python3
import sys
import os
from PIL import Image, ImageDraw, ImageFont

def generate_bmp(text, output_path="resources/welcome.bmp", width=800, height=480, custom_font_path=None, red_text=None):
    """
    Generate a 3-color (Black, White, Red) BMP for e-paper.
    If red_text is provided, it will be rendered in red below the main black text.
    """
    # Create a new white image (RGB mode for 3 colors)
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Font paths
    font_paths = []
    if custom_font_path:
        font_paths.append(custom_font_path)
    font_paths.append("tools/jf-openhuninn-2.1.ttf")
    font_paths.extend([
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "DejaVuSans.ttf"
    ])
    
    font_path = None
    for path in font_paths:
        if os.path.exists(path):
            font_path = path
            break
            
    def get_fitting_font(text, max_w, max_h):
        size = 120
        while size >= 20:
            f = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
            l, t, r, b = draw.textbbox((0, 0), text, font=f)
            if (r - l) < max_w and (b - t) < max_h:
                return f, size
            size -= 5
        return ImageFont.load_default(), 20

    # Draw main text in black
    main_font, main_size = get_fitting_font(text, width * 0.9, height * 0.4 if red_text else height * 0.8)
    l, t, r, b = draw.textbbox((0, 0), text, font=main_font)
    x = (width - (r - l)) // 2
    y = (height // 2 - (b - t)) // 2 if red_text else (height - (b - t)) // 2
    draw.text((x, y), text, font=main_font, fill=(0, 0, 0))

    # Draw red text if provided
    if red_text:
        red_font, red_size = get_fitting_font(red_text, width * 0.9, height * 0.4)
        rl, rt, rr, rb = draw.textbbox((0, 0), red_text, font=red_font)
        rx = (width - (rr - rl)) // 2
        ry = height // 2 + (height // 2 - (rb - rt)) // 2
        draw.text((rx, ry), red_text, font=red_font, fill=(255, 0, 0))

    # Branding
    try:
        brand_f = ImageFont.truetype(font_path, 20) if font_path else ImageFont.load_default()
        bt = "Designed by BreadSoft"
        bl, bt_, br, bb = draw.textbbox((0, 0), bt, font=brand_f)
        draw.text(((width - (br - bl)) // 2, height - 30), bt, font=brand_f, fill=(150, 150, 150))
    except:
        pass

    # Save image based on file extension
    if output_path.endswith('.bin'):
        # Export as 96KB Raw Binary (48,000 bytes Black/White buffer + 48,000 bytes Red buffer)
        img_rgb = img.convert('RGB')
        pixels = img_rgb.load()
        
        bw_data = bytearray(width * height // 8)
        red_data = bytearray(width * height // 8)
        
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                pixel_idx = y * width + x
                byte_idx = pixel_idx // 8
                bit_pos = 7 - (pixel_idx % 8)
                
                # Active-low black buffer: 0 for Black, 1 for White/Red
                is_black = (r < 128 and g < 128 and b < 128)
                is_red = (r > g + 40 and r > b + 40 and r > 100)
                
                if not is_black:
                    bw_data[byte_idx] |= (1 << bit_pos)
                if is_red:
                    red_data[byte_idx] |= (1 << bit_pos)
                    
        with open(output_path, 'wb') as f:
            f.write(bw_data)
            f.write(red_data)
        print(f"Generated Raw 2-bit Binary (.bin): {output_path} ({len(bw_data) + len(red_data)} bytes / 93.75 KB)")
    else:
        # Convert to 16-color palette (Pillow automatically saves it as a highly compressed 4-bit BMP)
        quantized = img.quantize(colors=16, method=Image.Quantize.MAXCOVERAGE)
        quantized.save(output_path, format="BMP")
        print(f"Generated 4-bit 3-color BMP: {output_path} (192.1 KB)")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate a 3-color BMP for e-paper.')
    parser.add_argument('text', help='Main text (Black)')
    parser.add_argument('output', nargs='?', default='resources/welcome.bmp', help='Output file path')
    parser.add_argument('--red', help='Red text to display below')
    parser.add_argument('--font', help='Custom font path')
    
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    generate_bmp(args.text, args.output, red_text=args.red, custom_font_path=args.font)
