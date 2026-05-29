import os
import json
import threading
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

class BulletinPublisher:
    def __init__(self, mqtt_config=None):
        self._lock = threading.Lock()
        
        # Directories setup
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.conf_dir = os.path.join(self.base_dir, 'conf')
        self.output_dir = os.path.join(self.base_dir, 'output')
        self.fonts_dir = os.path.join(self.base_dir, 'fonts')
        
        os.makedirs(self.conf_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.config_file = os.path.join(self.conf_dir, 'mqtt.conf')
        
        with self._lock:
            if mqtt_config is not None:
                self._save_config(mqtt_config)
                self.config = mqtt_config
            else:
                self.config = self._load_config()

    def _save_config(self, config):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
            
    def _load_config(self):
        if not os.path.exists(self.config_file):
            return None
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
            return None

    def _get_font(self, size):
        font_paths = []
        if os.path.exists(self.fonts_dir):
            for f in os.listdir(self.fonts_dir):
                if f.endswith('.ttf') or f.endswith('.ttc'):
                    font_paths.append(os.path.join(self.fonts_dir, f))
        
        # Fallbacks (usually found on linux/raspberry pi)
        font_paths.extend([
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "DejaVuSans.ttf"
        ])
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def _get_fitting_font(self, draw, text, max_w, max_h):
        size = 150
        while size >= 20:
            f = self._get_font(size)
            if f == ImageFont.load_default():
                return f, 20
            l, t, r, b = draw.textbbox((0, 0), text, font=f)
            if (r - l) < max_w and (b - t) < max_h:
                return f, size
            size -= 10
        return self._get_font(20), 20

    def _render_text(self, content, width, height):
        """Render text with optional <red> tags, wrapping to fit the canvas.
        Returns a Pillow Image.
        """
        # Parse colored segments
        # group(1) = text before <red>, group(2) = text inside <red>...</red>
        segments = []
        import re
        pattern = re.compile(r"(.*?)<red>(.*?)</red>", re.DOTALL)
        last_end = 0
        for m in pattern.finditer(content):
            # group(1) contains the text before <red> within this match
            before = m.group(1)
            if before:
                segments.append((before, (0, 0, 0)))
            segments.append((m.group(2), (255, 0, 0)))
            last_end = m.end()
        # Any remaining text after the last </red> (or the whole string if no tags)
        after = content[last_end:]
        if after:
            segments.append((after, (0, 0, 0)))

        # Prepare drawing canvas
        img = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        max_w = width * 0.9
        max_h = height * 0.8

        # Determine suitable font size based on full plain text
        plain_text = ''.join(seg for seg, _ in segments)
        font, _ = self._get_fitting_font(draw, plain_text, max_w, max_h)

        # Build lines by adding segments until width limit
        lines = []  # each line is list of (text, color)
        current_line = []
        line_width = 0
        for seg_text, seg_color in segments:
            seg_w = draw.textbbox((0, 0), seg_text, font=font)[2]
            if line_width + seg_w <= max_w:
                current_line.append((seg_text, seg_color))
                line_width += seg_w
            else:
                # start new line
                lines.append((current_line, line_width))
                current_line = [(seg_text, seg_color)]
                line_width = seg_w
        if current_line:
            lines.append((current_line, line_width))

        # Compute total height
        line_height = draw.textbbox((0, 0), 'Ay', font=font)[3]  # approximate line height
        total_h = len(lines) * line_height + (len(lines) - 1) * 5
        y = (height - total_h) // 2

        # Render each line
        for line_items, line_w in lines:
            x = (width - line_w) // 2
            cursor_x = x
            for txt, color in line_items:
                draw.text((cursor_x, y), txt, font=font, fill=color)
                cursor_x += draw.textbbox((0, 0), txt, font=font)[2]
            y += line_height + 5
        return img

    def generate_image(self, content, is_file_path=False):
        width, height = 800, 480
        
        if is_file_path:
            try:
                original = Image.open(content).convert('RGB')
                # Resize and keep aspect ratio
                orig_w, orig_h = original.size
                ratio = min(width / orig_w, height / orig_h)
                new_size = (int(orig_w * ratio), int(orig_h * ratio))
                resized = original.resize(new_size, Image.Resampling.LANCZOS)
                
                # Create white background and paste centered
                img = Image.new('RGB', (width, height), (255, 255, 255))
                offset_x = (width - new_size[0]) // 2
                offset_y = (height - new_size[1]) // 2
                img.paste(resized, (offset_x, offset_y))
                return img
            except Exception as e:
                raise ValueError(f"Failed to load/process image {content}: {e}")
        else:
            # Text to image with wrapping and color tags
            img = self._render_text(content, width, height)
            return img

    def _save_bin_and_bmp(self, img, base_filename, output_dir=None):
        width, height = 800, 480
        # Determine output directory (default to self.output_dir)
        out_dir = output_dir if output_dir is not None else self.output_dir
        # Ensure directory exists
        os.makedirs(out_dir, exist_ok=True)
        bin_path = os.path.join(out_dir, f"{base_filename}.bin")
        bmp_path = os.path.join(out_dir, f"{base_filename}.bmp")
        
        # 1. Save quantized BMP for preview
        quantized = img.quantize(colors=16, method=Image.Quantize.MAXCOVERAGE)
        quantized.save(bmp_path, format="BMP")
        
        # 2. Save raw 2-bit binary (.bin)
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
                
                # Active-low logic for Waveshare e-paper
                is_black = (r < 128 and g < 128 and b < 128)
                is_red = (r > g + 40 and r > b + 40 and r > 100)
                
                if not is_black:
                    bw_data[byte_idx] |= (1 << bit_pos)
                if is_red:
                    red_data[byte_idx] |= (1 << bit_pos)
                    
        with open(bin_path, 'wb') as f:
            f.write(bw_data)
            f.write(red_data)
            
        return bin_path, bmp_path

    def publish(self, content, is_file_path=False):
        with self._lock:
            if not self.config:
                raise ValueError("MQTT configuration is missing. Cannot publish.")
            
            # Determine base filename
            if is_file_path:
                base_filename = os.path.splitext(os.path.basename(content))[0]
            else:
                base_filename = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            
            # Prepare date-based output directory
            date_dir = os.path.join(self.output_dir, datetime.now().strftime("%Y_%m_%d"))
            os.makedirs(date_dir, exist_ok=True)
            
            # Generate image
            img = self.generate_image(content, is_file_path)
            
            # Generate .bin and .bmp using date_dir
            bin_path, bmp_path = self._save_bin_and_bmp(img, base_filename, date_dir)
            
            # Publish via MQTT
            topic = self.config.get('topic')
            if not topic:
                raise ValueError("MQTT topic is not defined in the configuration.")
                
            # The Pico device subscribes to {topic_prefix}/binary for raw bin files
            if not topic.endswith('/binary'):
                topic = f"{topic}/binary"
            
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 1883)
            user = self.config.get('user')
            password = self.config.get('password')
            
            auth = None
            if user:
                auth = {'username': user, 'password': password}
                
            try:
                with open(bin_path, 'rb') as f:
                    payload = f.read()
                
                publish.single(
                    topic=topic,
                    payload=payload,
                    hostname=host,
                    port=port,
                    auth=auth,
                    qos=1
                )
                print(f"Successfully published {bin_path} to MQTT topic {topic}")
                return bin_path, bmp_path
            except Exception as e:
                raise RuntimeError(f"Failed to publish to MQTT: {e}")
