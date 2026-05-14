
def create_welcome_bmp(path):
    width = 800
    height = 480
    
    # 1-bit BMP Header
    # File Header (14 bytes)
    file_type = b'BM'
    # 54 (header) + 8 (palette) + (800 * 480 / 8) = 62 + 48000 = 48062
    file_size = (48062).to_bytes(4, 'little')
    reserved = b'\x00\x00\x00\x00'
    offset = (62).to_bytes(4, 'little')
    
    # DIB Header (40 bytes)
    header_size = (40).to_bytes(4, 'little')
    w = (width).to_bytes(4, 'little')
    h = (height).to_bytes(4, 'little')
    planes = (1).to_bytes(2, 'little')
    bit_count = (1).to_bytes(2, 'little')
    compression = (0).to_bytes(4, 'little')
    image_size = (48000).to_bytes(4, 'little')
    x_ppm = (2835).to_bytes(4, 'little')
    y_ppm = (2835).to_bytes(4, 'little')
    colors_used = (2).to_bytes(4, 'little')
    colors_important = (2).to_bytes(4, 'little')
    
    # Palette (8 bytes: Black, White)
    # B G R A
    palette = b'\x00\x00\x00\x00' + b'\xff\xff\xff\x00'
    
    # Pixel data (all white for now, 1 = white)
    # 800 / 8 = 100 bytes per row
    pixels = b'\xff' * 48000
    
    with open(path, 'wb') as f:
        f.write(file_type + file_size + reserved + offset)
        f.write(header_size + w + h + planes + bit_count + compression + image_size + x_ppm + y_ppm + colors_used + colors_important)
        f.write(palette)
        f.write(pixels)

if __name__ == "__main__":
    import os
    if not os.path.exists('resources'):
        os.makedirs('resources')
    create_welcome_bmp('resources/welcome.bmp')
    print("Created simple welcome.bmp")
