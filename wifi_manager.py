"""
WiFi Manager Module
Handles WiFi connection, configuration, and provisioning
"""

import network
import json
import os
import utime

MAX_WIFI_RETRIES = 3
WIFI_CONFIG_PATH = './configs/wifi_config.json'

class WiFiManager:
    def __init__(self, timeout_ms=30000):
        """
        Initialize WiFi Manager
        timeout_ms: timeout for connection attempts in milliseconds
        """
        self.timeout_ms = timeout_ms
        self.wlan = None
        self.is_connected = False
    
    def _file_exists(self, path):
        """Helper to check if file or directory exists."""
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def load_config(self):
        """Load WiFi configuration from file. Returns dict or None."""
        try:
            with open(WIFI_CONFIG_PATH, 'r') as f:
                config = json.load(f)
            print("[WiFi] Config loaded successfully")
            return config
        except OSError:
            print("[WiFi] Config file not found")
            return None
        except Exception as e:
            print(f"[WiFi] Error loading config: {e}")
            return None
    
    def save_config(self, ssid, password):
        """Save WiFi configuration to file."""
        try:
            # Ensure configs directory exists
            if not self._file_exists('./configs'):
                os.mkdir('./configs')
            
            config = {'ssid': ssid, 'password': password}
            with open(WIFI_CONFIG_PATH, 'w') as f:
                json.dump(config, f)
            print("[WiFi] Config saved successfully")
            return True
        except Exception as e:
            print(f"[WiFi] Error saving config: {e}")
            return False
    
    def try_connect_to_saved_config(self):
        """Try to connect using saved WiFi configuration."""
        config = self.load_config()
        if not config:
            print("[WiFi] No saved configuration found")
            return False
        
        ssid = config.get('ssid')
        password = config.get('password')
        
        if not ssid:
            print("[WiFi] Invalid configuration")
            return False
        
        return self.try_connect(ssid, password, max_retries=MAX_WIFI_RETRIES)
    
    def try_connect(self, ssid, password, max_retries=3):
        """Try to connect to WiFi with given credentials."""
        print(f"[WiFi] Attempting to connect to '{ssid}' (max {max_retries} retries)")
        
        try:
            self.wlan = network.WLAN(network.STA_IF)
            self.wlan.active(True)
            
            for attempt in range(max_retries):
                try:
                    print(f"[WiFi] Attempt {attempt + 1}/{max_retries}")
                    self.wlan.connect(ssid, password)
                    
                    start_time = utime.ticks_ms()
                    while utime.ticks_diff(utime.ticks_ms(), start_time) < self.timeout_ms:
                        if self.wlan.isconnected():
                            print("[WiFi] Connected successfully!")
                            self.is_connected = True
                            return True
                        utime.sleep_ms(100)
                    
                    print(f"[WiFi] Attempt {attempt + 1} timed out")
                    self.wlan.disconnect()
                    
                except Exception as e:
                    print(f"[WiFi] Connection error: {e}")
                    utime.sleep(1)
            
            print("[WiFi] Failed to connect after all retries")
            return False
        
        except Exception as e:
            print(f"[WiFi] Fatal error: {e}")
            return False
    
    def get_ip_info(self):
        """Get current IP information."""
        try:
            if self.wlan and self.wlan.isconnected():
                return self.wlan.ifconfig()
            return None
        except Exception as e:
            print(f"[WiFi] Error getting IP info: {e}")
            return None
    
    def disconnect(self):
        """Disconnect from WiFi."""
        try:
            if self.wlan:
                self.wlan.disconnect()
                self.wlan.active(False)
                self.is_connected = False
                print("[WiFi] Disconnected")
        except Exception as e:
            print(f"[WiFi] Error disconnecting: {e}")
