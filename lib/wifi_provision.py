import network
import utime
import json
import machine
from machine import Pin
import socket
import os

VERSION = "1.8 - 20260514_235500"
USER_CONFIG_DIR = './user_config'
USER_WIFI_CONFIG_FILE = USER_CONFIG_DIR + '/wifi_config.json'

# Initialize ePaper only when needed
epd = None

def url_decode(s):
    """Simple URL decoder for WiFi credentials."""
    s = s.replace('+', ' ')
    res = ""
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            try:
                res += chr(int(s[i+1:i+3], 16))
                i += 3
            except:
                res += s[i]
                i += 1
        else:
            res += s[i]
            i += 1
    return res

def get_epd(existing_epd=None):
    global epd
    if existing_epd is not None:
        epd = existing_epd
    elif epd is None:
        try:
            print("[Provision] Initializing new EPD instance...")
            from lib.epaper_7_5_b import EPD_7in5_B
            epd = EPD_7in5_B()
        except Exception as e:
            print(f"[Provision] Error creating EPD: {e}")
    return epd

def display_text(lines, y_start=10, existing_epd=None):
    """Fallback text display if images are missing."""
    current_epd = get_epd(existing_epd)
    if not current_epd:
        return
    
    try:
        print(f"[Provision] Displaying on e-paper: {lines}")
        current_epd.wake_up()
        current_epd.imageblack.fill(current_epd.WHITE)
        current_epd.imagered.fill(0)
        
        # Draw black text (centered, slightly larger spacing)
        for i, line in enumerate(lines):
            # Very rough centering
            x_pos = max(10, (800 - (len(line) * 8)) // 2)
            current_epd.imageblack.text(line, x_pos, y_start + i * 40, current_epd.BLACK)
        
        current_epd.display()
    except Exception as e:
        print(f"[Provision] Display error: {e}")

def display_ui_image(filename, existing_epd=None):
    """Use BMPDisplay to show a UI image."""
    current_epd = get_epd(existing_epd)
    if not current_epd:
        return
    try:
        from core.bmp_display import BMPDisplay
        bd = BMPDisplay(current_epd)
        path = 'resources/' + filename
        if bd._file_exists(path):
            print(f"[Provision] Showing image: {path}")
            bd.display_file(path)
            return True
    except Exception as e:
        print(f"[Provision] Image display error: {e}")
    return False

def connect_to_wifi(ssid, password, existing_epd=None):
    """Try to connect to WiFi with given credentials"""
    display_text([f"Connecting to", f"{ssid}"], existing_epd=existing_epd)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    
    for attempt in range(10):  # Try for up to 100 seconds (10 * 10 sec)
        display_text([f"Connecting to", f"{ssid}", f"Attempt {attempt+1}/10"], existing_epd=existing_epd)
        utime.sleep(10)
        if wlan.isconnected():
            display_text([f"Connected to {ssid}!", "Successfully connected"], existing_epd=existing_epd)
            return True
    
    display_text([f"Failed to connect to {ssid}", "Returning to provisioning..."], existing_epd=existing_epd)
    utime.sleep(3)
    return False


def provision_wifi(existing_epd=None):
    """Main provisioning entry point"""
    print(f"Pico WiFi Provisioning {VERSION}")
    
    # Check for WiFi config
    try:
        if os.stat(USER_WIFI_CONFIG_FILE):
            with open(USER_WIFI_CONFIG_FILE, 'r') as f:
                config = json.load(f)
            ssid = config['ssid']
            password = config['password']
            
            display_text(["WiFi config found.", "Connecting..."], y_start=180, existing_epd=existing_epd)
            
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
            wlan.connect(ssid, password)
            for attempt in range(5):
                display_text([f"Connecting...", f"Attempt {attempt+1}/5"], y_start=180, existing_epd=existing_epd)
                utime.sleep(30)
                if wlan.isconnected():
                    display_text(["Connected to WiFi!", "Connected successfully!"], y_start=180, existing_epd=existing_epd)
                    utime.sleep(5)
                    return True
            else:
                display_text(["Failed to connect.", "Starting provisioning..."], y_start=180, existing_epd=existing_epd)
                raise Exception("No connection")
    except:
        # Start provisioning
        while True:
            config_received = False
            
            # 1. Initialize radio
            wlan_ap = network.WLAN(network.AP_IF)
            wlan_ap.config(essid='Pico-Setup', password='password123')
            wlan_ap.active(True)
            ap_ip = wlan_ap.ifconfig()[0]
            
            # 2. Setup Server
            addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(addr)
            s.listen(1)
            s.settimeout(0.5)
            print('Listening on', addr)
            
            # 3. ONLY NOW show instructions
            if not display_ui_image('provisioning.bmp', existing_epd=existing_epd):
                # Fallback if image missing
                display_text([
                    "WiFi Setup Mode",
                    "----------------",
                    "SSID: Pico-Setup",
                    "Pass: password123",
                    f"URL: http://{ap_ip}"
                ], y_start=100, existing_epd=existing_epd)
            
            # Reset button setup (Middle Key)
            reset_button = Pin(2, Pin.IN, Pin.PULL_UP)
            reset_press_start = None
            
            # Inner loop for provisioning server
            while not config_received:
                try:
                    res = s.accept()
                    cl, addr = res
                    print('Client connected from', addr)
                    
                    # Read request headers
                    request = b""
                    while True:
                        chunk = cl.recv(1024)
                        request += chunk
                        if b'\r\n\r\n' in request or not chunk:
                            break
                    
                    req_str = request.decode('utf-8', 'ignore')
                    
                    if 'POST' in req_str and '/submit' in req_str:
                        # Find Content-Length
                        content_length = 0
                        lines = req_str.split('\r\n')
                        for line in lines:
                            if line.lower().startswith('content-length:'):
                                content_length = int(line.split(':')[1].strip())
                                break
                        
                        # Read body
                        parts = req_str.split('\r\n\r\n')
                        body = parts[1] if len(parts) > 1 else ""
                        
                        while len(body.encode('utf-8')) < content_length:
                            chunk = cl.recv(1024)
                            if not chunk: break
                            body += chunk.decode('utf-8', 'ignore')
                        
                        print(f"[Provision] Full body: '{body}'")
                        
                        # Extract SSID and Password
                        ssid = ""
                        password = ""
                        params = body.split('&')
                        for p in params:
                            if '=' in p:
                                key, val = p.split('=', 1)
                                if key == 'ssid': ssid = val
                                if key == 'password': password = val

                        if ssid:
                            ssid = url_decode(ssid)
                            password = url_decode(password)
                            print(f"[Provision] Parsed SSID: '{ssid}', Pass length: {len(password)}")
                            
                            config = {'ssid': ssid, 'password': password}
                            
                            try:
                                if not os.stat(USER_CONFIG_DIR):
                                    os.mkdir(USER_CONFIG_DIR)
                            except Exception:
                                try:
                                    os.mkdir(USER_CONFIG_DIR)
                                except Exception:
                                    pass
                            
                            with open(USER_WIFI_CONFIG_FILE, 'w') as f:
                                json.dump(config, f)
                            
                            # Reply to client
                            html = ""
                            try:
                                with open('/resources/www/index.html', 'r') as f:
                                    html = f.read().replace('id="mainContainer"', 'id="mainContainer" class="success"')
                            except:
                                html = '<html><body><h1>Success</h1><p>Config received.</p></body></html>'
                            
                            # Send headers
                            cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                            
                            # Send body in chunks
                            chunk_size = 512
                            for i in range(0, len(html), chunk_size):
                                cl.send(html[i:i+chunk_size])
                            
                            utime.sleep(1)
                            cl.close()
                            
                            display_text(["Config saved!", "Connecting..."], y_start=180, existing_epd=existing_epd)
                            config_received = True
                        else:
                            cl.send('HTTP/1.1 400 Bad Request\r\n\r\nInvalid data')
                            cl.close()
                    else:
                        # Serve template
                        html = ""
                        try:
                            with open('/resources/www/index.html', 'r') as f:
                                html = f.read()
                        except:
                            html = '<html><body><h1>BreadSoft Setup</h1><form method="post" action="/submit">SSID: <input name="ssid"><br>Pass: <input name="password"><br><input type="submit"></form></body></html>'
                        
                        # Send headers
                        cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                        
                        # Send body in chunks to avoid buffer issues
                        chunk_size = 512
                        for i in range(0, len(html), chunk_size):
                            cl.send(html[i:i+chunk_size])
                        
                        cl.close()
                except OSError as e:
                    # Timeout or other error
                    pass
                
                # Check for manual reset button
                if reset_button.value() == 0:
                    if reset_press_start is None:
                        reset_press_start = utime.time()
                    elif utime.time() - reset_press_start >= 5:
                        try:
                            if os.stat(USER_CONFIG_DIR):
                                for entry in os.listdir(USER_CONFIG_DIR):
                                    path = USER_CONFIG_DIR + '/' + entry
                                    try:
                                        os.remove(path)
                                    except OSError:
                                        try:
                                            for sub in os.listdir(path):
                                                os.remove(path + '/' + sub)
                                            os.rmdir(path)
                                        except Exception:
                                            pass
                                os.rmdir(USER_CONFIG_DIR)
                        except Exception:
                            pass
                        display_text(["Config Cleared", "Rebooting..."], y_start=180, existing_epd=existing_epd)
                        utime.sleep(2)
                        import machine
                        machine.reset()
                else:
                    reset_press_start = None

            # Clean up server
            s.close()
            wlan_ap.active(False)
            if config_received:
                return True
            
            # Try to connect to WiFi
            if connect_to_wifi(ssid, password, existing_epd=existing_epd):
                # Connection successful, exit provisioning
                display_text(["WiFi Setup Complete!", "Connected successfully!"], existing_epd=existing_epd)
                utime.sleep(5)
                break
            # Connection failed, restart provisioning loop
    
    if existing_epd is None and epd:
        try:
            epd.sleep()
        except:
            pass
    return True

if __name__ == "__main__":
    provision_wifi()