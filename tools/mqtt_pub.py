#!/usr/bin/env python3
import sys
import os
import time
import paho.mqtt.client as mqtt

def publish_image(file_path, topic_prefix, server, port=1883):
    """
    Publish a BMP or binary image to the specified MQTT topic.
    Determines topic (/bmp or /binary) based on file extension.
    """
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return False
        
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.bmp':
        topic = f"{topic_prefix}/bmp"
    else:
        topic = f"{topic_prefix}/binary"
        
    print(f"Connecting to {server}:{port}...")
    client = mqtt.Client()
    
    try:
        client.connect(server, port, 60)
        
        with open(file_path, 'rb') as f:
            payload = f.read()
            
        print(f"Publishing {len(payload)} bytes to {topic}...")
        result = client.publish(topic, payload, qos=1)
        result.wait_for_publish(timeout=10)
        
        print("Successfully published!")
        client.disconnect()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def load_config(config_path):
    """Load server info from mqtt.conf"""
    config = {}
    try:
        with open(config_path, 'r') as f:
            for line in f:
                if '=' in line:
                    k, v = line.strip().split('=', 1)
                    config[k] = v
    except:
        pass
    return config

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mqtt_pub.py <file_path> [server] [topic_prefix]")
        sys.exit(1)
        
    file_to_send = sys.argv[1]
    
    # Try to load defaults from conf/mqtt.conf
    conf = load_config('conf/mqtt.conf')
    
    server = sys.argv[2] if len(sys.argv) > 2 else conf.get('mqtt_server', 'localhost')
    topic_pref = sys.argv[3] if len(sys.argv) > 3 else conf.get('mqtt_topic', 'epaper/bulletin')
    port = int(conf.get('mqtt_port', 1883))
    
    publish_image(file_to_send, topic_pref, server, port)
