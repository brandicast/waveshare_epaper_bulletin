"""
MQTT Handler Module
Handles MQTT connection and message receiving for raw pixel data
"""

import os
import sys
import utime
import gc

MQTT_CONFIG_PATH = './conf/mqtt.conf'
USER_CONFIG_DIR = './user_config'
RECEIVED_BMP_PATH = USER_CONFIG_DIR + '/received.bmp'
RECEIVED_BIN_PATH = USER_CONFIG_DIR + '/received.bin'


def _ensure_umqtt_package():
    """Ensure the local lib/umqtt package is loaded first."""
    try:
        # Prefer an absolute lib path if cwd is available.
        base_path = os.getcwd() if hasattr(os, 'getcwd') else None
        lib_dir = base_path + '/lib' if base_path else './lib'
    except Exception:
        lib_dir = './lib'

    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    return lib_dir


def _format_memory():
    try:
        return "free={}, alloc={}".format(gc.mem_free(), gc.mem_alloc())
    except AttributeError:
        return "gc.mem_free unavailable"


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
        
        # Clean up memory before connecting
        self.client = None
        gc.collect()
        
        try:
            _ensure_umqtt_package()
            
            try:
                from umqtt.robust import MQTTClient
            except ImportError:
                from umqtt.simple import MQTTClient

            server = self.config['mqtt_server']
            port = int(self.config['mqtt_port'])
            topic_prefix = self.config['mqtt_topic']
            
            print("[MQTT] Connecting to {}:{}".format(server, port))
            print("[MQTT] {}".format(_format_memory()))
            
            self.client = MQTTClient(self.client_id, server, port)
            self.client.set_callback(self._on_message)
            
            start_time = utime.ticks_ms()
            while utime.ticks_diff(utime.ticks_ms(), start_time) < self.timeout_ms:
                try:
                    print("[MQTT] Attempting broker connect; {}".format(_format_memory()))
                    self.client.connect(clean_session=True)
                    print("[MQTT] Connected to broker")
                    print("[MQTT] After connect; {}".format(_format_memory()))
                    
                    # Subscribe to two topics
                    topic_bmp = "{}/bmp".format(topic_prefix)
                    topic_bin = "{}/binary".format(topic_prefix)
                    
                    self.client.subscribe(topic_bmp)
                    self.client.subscribe(topic_bin)
                    print("[MQTT] Subscribed to: {} and {}".format(topic_bmp, topic_bin))
                    print("[MQTT] After subscribe; {}".format(_format_memory()))
                    
                    self.is_connected = True
                    return True
                except Exception as e:
                    print("[MQTT] Connection attempt failed: {}".format(e))
                    print("[MQTT] Connection attempt memory: {}".format(_format_memory()))
                    utime.sleep_ms(500)
            
            print("[MQTT] Connection timeout")
            return False
        
        except ImportError:
            print("[MQTT] umqtt.robust library not available")
            return False
        except OSError as e:
            if e.args[0] == 12: # ENOMEM
                print("[MQTT] FATAL: Out of memory during connection. Cleaning up...")
                self.client = None
                gc.collect()
            else:
                print("[MQTT] Connection error: {}".format(e))
            return False
        except Exception as e:
            print("[MQTT] Fatal error: {}".format(e))
            return False

    def _recover_connection(self):
        """Recover from MQTT errors by disconnecting and reconnecting."""
        self.is_connected = False
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
            self.client = None
        gc.collect()
        return self.connect()
    
    def _on_message(self, topic, msg_file):
        """Callback function for received messages (file-based)."""
        try:
            topic_str = topic.decode() if isinstance(topic, bytes) else topic
            print("[MQTT] Message received on: {}".format(topic_str))
            print("[MQTT] Message callback memory: {}".format(_format_memory()))
            
            # Ensure resources directory exists
            if not self._file_exists(USER_CONFIG_DIR):
                os.mkdir(USER_CONFIG_DIR)
            
            # Identify topic type
            if topic_str.endswith('/bmp'):
                dest = RECEIVED_BMP_PATH
                self.last_message_type = 'bmp'
            elif topic_str.endswith('/binary'):
                dest = RECEIVED_BIN_PATH
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
                print("[MQTT] After save memory: {}".format(_format_memory()))
                self.last_message = True
            except Exception as e:
                print("[MQTT] Error saving message to {}: {}".format(dest, e))
                print("[MQTT] Error save memory: {}".format(_format_memory()))
                return
        
        except Exception as e:
            print("[MQTT] Error processing message: {}".format(e))
    
    def check_messages(self):
        """Check for incoming MQTT messages (non-blocking)."""
        try:
            if self.client and self.is_connected:
                print("[MQTT] Before check_msg; {}".format(_format_memory()))
                self.client.check_msg()
                print("[MQTT] After check_msg; {}".format(_format_memory()))
                return True
            return False
        except OSError as e:
            print("[MQTT] Connection error during message check: {}".format(e))
            print("[MQTT] check_messages memory: {}".format(_format_memory()))
            self.is_connected = False
            if self._recover_connection():
                print("[MQTT] Reconnected after message check error")
                return True
            return False
        except Exception as e:
            print("[MQTT] Error checking messages: {}".format(e))
            print("[MQTT] check_messages exception memory: {}".format(_format_memory()))
            self.is_connected = False
            self._recover_connection()
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
