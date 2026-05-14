"""
MQTT Handler Module
Handles MQTT connection and message receiving for raw pixel data
"""

import json
import os
import utime

MAX_BINARY_SIZE = 48000  # Exactly 48000 bytes for 800x480 monochrome display (48000 / 8)
MQTT_CONFIG_PATH = './conf/mqtt.conf'
LATEST_PIXEL_PATH = './resources/latest.bin'

class MQTTHandler:
    def __init__(self, client_id="pico_epaper", timeout_ms=5000):
        """
        Initialize MQTT Handler
        client_id: MQTT client identifier
        timeout_ms: connection timeout in milliseconds
        
        Expects to receive raw pixel data (48,000 bytes for 800x480 monochrome)
        """
        self.client_id = client_id
        self.timeout_ms = timeout_ms
        self.config = None
        self.client = None
        self.is_connected = False
        self.last_message = None
        self.last_message_type = None
    
    def _file_exists(self, path):
        """Helper to check if file or directory exists."""
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def load_config(self):
        """Load MQTT configuration from file."""
        try:
            if not self._file_exists(MQTT_CONFIG_PATH):
                print("[MQTT] Config file not found")
                return False
            
            self.config = {}
            with open(MQTT_CONFIG_PATH, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            self.config[key.strip()] = value.strip()
            
            # Validate required fields
            if not all(k in self.config for k in ['mqtt_server', 'mqtt_port', 'mqtt_topic']):
                print("[MQTT] Missing required config fields")
                return False
            
            # Use .format() instead of concatenated f-strings for better compatibility
            msg = "[MQTT] Config loaded: server={}, port={}, topic={}".format(
                self.config['mqtt_server'], self.config['mqtt_port'], self.config['mqtt_topic'])
            print(msg)
            return True
        
        except Exception as e:
            print("[MQTT] Error loading config: {}".format(e))
            return False
    
    def connect(self):
        """Connect to MQTT broker."""
        if not self.config:
            print("[MQTT] No configuration loaded")
            return False
        
        try:
            from umqtt.robust import MQTTClient
            
            server = self.config['mqtt_server']
            port = int(self.config['mqtt_port'])
            topic_prefix = self.config['mqtt_topic']
            
            print("[MQTT] Connecting to {}:{}".format(server, port))
            
            self.client = MQTTClient(self.client_id, server, port)
            self.client.set_callback(self._on_message)
            
            start_time = utime.ticks_ms()
            while utime.ticks_diff(utime.ticks_ms(), start_time) < self.timeout_ms:
                try:
                    self.client.connect(clean_session=True)
                    print("[MQTT] Connected to broker")
                    
                    # Subscribe to two topics
                    topic_bmp = "{}/bmp".format(topic_prefix)
                    topic_bin = "{}/binary".format(topic_prefix)
                    
                    self.client.subscribe(topic_bmp)
                    self.client.subscribe(topic_bin)
                    print("[MQTT] Subscribed to: {} and {}".format(topic_bmp, topic_bin))
                    
                    self.is_connected = True
                    return True
                except Exception as e:
                    print("[MQTT] Connection attempt failed: {}".format(e))
                    utime.sleep_ms(500)
            
            print("[MQTT] Connection timeout")
            return False
        
        except ImportError:
            print("[MQTT] umqtt.robust library not available")
            return False
        except Exception as e:
            print("[MQTT] Fatal error: {}".format(e))
            return False
    
    def _on_message(self, topic, msg_file):
        """Callback function for received messages (file-based)."""
        try:
            topic_str = topic.decode() if isinstance(topic, bytes) else topic
            print("[MQTT] Message received on: {}".format(topic_str))
            
            # Ensure resources directory exists
            if not self._file_exists('./resources'):
                os.mkdir('./resources')
            
            # Identify topic type
            if topic_str.endswith('/bmp'):
                dest = './resources/received.bmp'
                self.last_message_type = 'bmp'
            elif topic_str.endswith('/binary'):
                dest = './resources/latest.bin'
                self.last_message_type = 'binary'
            else:
                print("[MQTT] Unknown topic suffix: {}".format(topic_str))
                return

            # Move temp file to destination
            try:
                if self._file_exists(dest):
                    os.remove(dest)
                os.rename(msg_file, dest)
                print("[MQTT] Saved to {}".format(dest))
                self.last_message = True
            except Exception as e:
                print("[MQTT] Error saving message to {}: {}".format(dest, e))
                return
        
        except Exception as e:
            print("[MQTT] Error processing message: {}".format(e))
    
    def check_messages(self):
        """Check for incoming MQTT messages (non-blocking)."""
        try:
            if self.client and self.is_connected:
                self.client.check_msg()
                return True
            return False
        except OSError as e:
            print("[MQTT] Connection lost: {}".format(e))
            self.is_connected = False
            return False
        except Exception as e:
            print("[MQTT] Error checking messages: {}".format(e))
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        try:
            if self.client:
                self.client.disconnect()
                self.is_connected = False
                print("[MQTT] Disconnected from broker")
        except Exception as e:
            print("[MQTT] Error disconnecting: {}".format(e))
