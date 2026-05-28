#!/usr/bin/env python3
import argparse
import sys
try:
    from .bulletin_publisher import BulletinPublisher
except ImportError:
    from bulletin_publisher import BulletinPublisher

def main():
    parser = argparse.ArgumentParser(description="Bulletin Publisher")
    parser.add_argument("content", help="Text content or path to an image file")
    parser.add_argument("--image", action="store_true", help="Treat content as an image file path")
    parser.add_argument("--host", help="MQTT Broker Host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port")
    parser.add_argument("--user", help="MQTT Username")
    parser.add_argument("--password", help="MQTT Password")
    parser.add_argument("--topic", help="MQTT Topic to publish to")
    parser.add_argument("--no-publish", action="store_true", help="Generate images only, do not publish to MQTT")

    args = parser.parse_args()
    
    mqtt_config = None
    if args.host and args.topic:
        mqtt_config = {
            "host": args.host,
            "port": args.port,
            "user": args.user,
            "password": args.password,
            "topic": args.topic
        }

    try:
        publisher = BulletinPublisher(mqtt_config=mqtt_config)
        
        if args.no_publish:
            print("Generating images without publishing...")
            img = publisher.generate_image(args.content, is_file_path=args.image)
            
            # Helper to just generate files
            import os
            from datetime import datetime
            base_name = os.path.splitext(os.path.basename(args.content))[0] if args.image else datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            bin_path, bmp_path = publisher._save_bin_and_bmp(img, base_name)
            print(f"Generated {bin_path} and {bmp_path}")
        else:
            print("Generating images and publishing to MQTT...")
            bin_path, bmp_path = publisher.publish(args.content, is_file_path=args.image)
            print(f"Process completed successfully. Files saved as: {bin_path}, {bmp_path}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
