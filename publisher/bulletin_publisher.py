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
            # Text to image
            img = Image.new('RGB', (width, height), (255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            main_font, _ = self._get_fitting_font(draw, content, width * 0.9, height * 0.8)
            l, t, r, b = draw.textbbox((0, 0), content, font=main_font)
            x = (width - (r - l)) // 2
            y = (height - (b - t)) // 2
            draw.text((x, y), content, font=main_font, fill=(0, 0, 0))
            return img

    def _save_bin_and_bmp(self, img, base_filename):
        width, height = 800, 480
        bin_path = os.path.join(self.output_dir, f"{base_filename}.bin")
        bmp_path = os.path.join(self.output_dir, f"{base_filename}.bmp")
        
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
                
            # Generate image
            img = self.generate_image(content, is_file_path)
            
            # Generate .bin and .bmp
            bin_path, bmp_path = self._save_bin_and_bmp(img, base_filename)
            
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
