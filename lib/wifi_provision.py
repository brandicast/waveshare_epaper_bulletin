import network
import utime
import json
import machine
from machine import Pin
import socket
import os

VERSION = "1.7 - 20260514_021000"

# Initialize ePaper only when needed
epd = None

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
    current_epd = get_epd(existing_epd)
    if not current_epd:
        print(f"[Provision] No EPD available for display: {lines}")
        return
    
    try:
        print(f"[Provision] Displaying on e-paper: {lines}")
        # Clear to white
        current_epd.imageblack.fill(current_epd.WHITE)
        current_epd.imagered.fill(0)
        
        # Draw black text
        for i, line in enumerate(lines):
            current_epd.imageblack.text(line, 10, y_start + i * 20, current_epd.BLACK)
        
        # Refresh display
        current_epd.display()
        print("[Provision] E-paper refresh triggered")
        utime.sleep(1) # Small pause for refresh to start
    except Exception as e:
        print(f"[Provision] Error during display: {e}")

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
        if os.stat('./configs/wifi_config.json'):
            with open('./configs/wifi_config.json', 'r') as f:
                config = json.load(f)
            ssid = config['ssid']
            password = config['password']
            display_text(["WiFi config found.", "Connecting..."], existing_epd=existing_epd)
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
            wlan.connect(ssid, password)
            for attempt in range(5):
                display_text([f"Connecting...", f"Attempt {attempt+1}/5"], existing_epd=existing_epd)
                utime.sleep(30)
                if wlan.isconnected():
                    display_text(["Connected to WiFi!"], existing_epd=existing_epd)
                    utime.sleep(5)
                    return True
            else:
                display_text(["Failed to connect.", "Starting provisioning..."], existing_epd=existing_epd)
                raise Exception("No connection")
    except:
        # Start provisioning
        while True:  # Outer loop to restart provisioning if WiFi connection fails
            config_received = False
            display_text(["Starting WiFi", "provisioning..."], existing_epd=existing_epd)
            wlan_ap = network.WLAN(network.AP_IF)
            wlan_ap.config(essid='Pico-Setup', password='password123')
            wlan_ap.active(True)
            ap_ip = wlan_ap.ifconfig()[0]
            display_text([f"Pico WiFi Setup {VERSION}", "AP: Pico-Setup", f"IP: {ap_ip}", "Pass: password123", "Open browser to IP"], existing_epd=existing_epd)
            
            # Create configs folder if not exists
            try:
                os.mkdir('./configs')
            except:
                pass
            
            # Start web server
            addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(addr)
            s.listen(1)
            s.settimeout(0.5)  # Set timeout to allow responsive connection handling
            print('Listening on', addr)
            
            # Reset button (GPIO 14, active low)
            reset_button = Pin(14, Pin.IN, Pin.PULL_UP)
            reset_press_start = None
            
            # Inner loop for provisioning server
            while not config_received:
                try:
                    cl, addr = s.accept()
                    print('Client connected from', addr)
                    request = cl.recv(1024)
                    # Properly decode bytes to string
                    try:
                        request_str = request.decode('utf-8')
                    except:
                        request_str = request.decode('latin-1')
                    
                    if 'POST /submit' in request_str:
                        # Parse headers to find Content-Length
                        headers_end = request_str.find('\r\n\r\n')
                        headers = request_str[:headers_end]
                        content_length = 0
                        for line in headers.split('\r\n'):
                            if line.startswith('Content-Length:'):
                                content_length = int(line.split(':')[1].strip())
                                break
                        
                        # Read body
                        body_start_pos = headers_end + 4
                        body = request_str[body_start_pos:]
                        
                        # If we don't have full body yet, read more
                        while len(body) < content_length:
                            more_data = cl.recv(512)
                            if not more_data:
                                break
                            try:
                                body += more_data.decode('utf-8')
                            except:
                                body += more_data.decode('latin-1')
                        
                        params = {}
                        # URL decode helper
                        def url_decode(s):
                            s = s.replace('+', ' ')
                            s = s.replace('%20', ' ')
                            s = s.replace('%21', '!')
                            s = s.replace('%3D', '=')
                            s = s.replace('%26', '&')
                            return s
                        for pair in body.split('&'):
                            if '=' in pair:
                                key, value = pair.split('=', 1)
                                key = url_decode(key)
                                value = url_decode(value)
                                params[key] = value
                        
                        ssid = params.get('ssid', '')
                        password = params.get('password', '')
                        if ssid:
                            config = {'ssid': ssid, 'password': password}
                            print('Received config for:', ssid)
                            with open('./configs/wifi_config.json', 'w') as f:
                                json.dump(config, f)
                            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html><body><h1>Config saved! Device will now connect.</h1></body></html>'
                            cl.send(response)
                            cl.close()
                            display_text(["Config saved!", "Connecting..."], existing_epd=existing_epd)
                            config_received = True
                        else:
                            response = 'HTTP/1.1 400 Bad Request\r\n\r\nInvalid data'
                            cl.send(response)
                            cl.close()
                    else:
                        # Serve form
                        html = '''<!DOCTYPE html>
<html>
<head><title>Pico WiFi Setup</title></head>
<body>
<h1>Enter WiFi Credentials</h1>
<form method="post" action="/submit">
SSID: <input type="text" name="ssid"><br>
Password: <input type="password" name="password"><br>
<input type="submit" value="Submit">
</form>
</body>
</html>'''
                        response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n' + html
                        cl.send(response)
                        cl.close()
                except OSError as e:
                    # No connection yet (socket timeout)
                    if e.errno != 110:  # errno 110 is ETIMEDOUT
                        print('OSError:', e)
                    
                    # Check reset button
                    if reset_button.value() == 0:  # Button pressed (active low)
                        if reset_press_start is None:
                            reset_press_start = utime.time()
                        elif utime.time() - reset_press_start >= 5:
                            # Clear WiFi config
                            try:
                                os.remove('./configs/wifi_config.json')
                                print('WiFi config cleared')
                            except:
                                pass
                            display_text(["WiFi config cleared", "Restarting..."], existing_epd=existing_epd)
                            utime.sleep(2)
                            machine.reset()
                    else:
                        reset_press_start = None
                except Exception as e:
                    print('Error:', e)
            
            # Close server socket
            s.close()
            wlan_ap.active(False)
            
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