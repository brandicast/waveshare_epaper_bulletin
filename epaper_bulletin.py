"""
E-Paper Bulletin Board Application
Main application for Raspberry Pi Pico W with Waveshare 7.5inch e-Paper

Flow:
1. Initialize e-paper display
2. Try to connect to WiFi (using saved config, max 3 retries)
3. If WiFi fails, start provisioning
4. Display initial image (latest.bin or home.bin)
5. Connect to MQTT and listen for updates
6. Enter main loop: check MQTT, display updates, sleep
"""

import utime
import os
import sys

# Set timeout for operations (avoid hanging)
DEFAULT_TIMEOUT_MS = 30000

def file_exists(path):
    """Helper to check if file or directory exists in MicroPython."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False

def initialize_display():
    """Initialize e-paper display with timeout."""
    print("\n=== Initializing E-Paper Display ===")
    try:
        from lib.epaper_7_5_b import EPD_7in5_B
        
        print("[Init] Creating EPD instance...")
        start = utime.ticks_ms()
        
        epd = EPD_7in5_B(spi_bus=1, rst=12, dc=8, cs=9, busy=13, mode="normal")
        
        elapsed = utime.ticks_diff(utime.ticks_ms(), start)
        print(f"[Init] E-paper initialized ({elapsed}ms)")
        
        return epd
    
    except ImportError as e:
        print(f"[Init] ERROR: Cannot import epaper library: {e}")
        return None
    except Exception as e:
        print(f"[Init] ERROR: Failed to initialize display: {e}")
        return None


def initialize_wifi(timeout_ms=DEFAULT_TIMEOUT_MS):
    """Initialize WiFi manager."""
    print("\n=== Initializing WiFi ===")
    try:
        from wifi_manager import WiFiManager
        
        wm = WiFiManager(timeout_ms=timeout_ms)
        print("[WiFi] WiFi manager created")
        
        return wm
    
    except ImportError as e:
        print(f"[WiFi] ERROR: Cannot import WiFi manager: {e}")
        return None
    except Exception as e:
        print(f"[WiFi] ERROR: Failed to initialize WiFi: {e}")
        return None


def wifi_connection_phase(wifi_manager, epd=None, timeout_ms=DEFAULT_TIMEOUT_MS):
    """Handle WiFi connection with saved config or provisioning."""
    print("\n=== WiFi Connection Phase ===")
    
    if not wifi_manager:
        print("[Main] ERROR: WiFi manager not available")
        return False
    
    # Try to connect with saved configuration
    print("[Main] Attempting to connect with saved WiFi config...")
    start = utime.ticks_ms()
    
    if wifi_manager.try_connect_to_saved_config():
        elapsed = utime.ticks_diff(utime.ticks_ms(), start)
        print(f"[Main] WiFi connected successfully ({elapsed}ms)")
        ip_info = wifi_manager.get_ip_info()
        if ip_info:
            print(f"[Main] IP: {ip_info[0]}")
        return True
    
    # Saved config failed, start provisioning
    print("[Main] Saved WiFi config failed. Starting WiFi provisioning...")
    print("[Main] Please follow instructions on the e-paper display...")
    
    try:
        print("[Main] Importing WiFi provisioning module...")
        from lib.wifi_provision import provision_wifi
        
        if provision_wifi(existing_epd=epd):
            print("[Main] WiFi provisioning completed successfully")
            return True
        else:
            print("[Main] WARNING: WiFi provisioning did not result in connection")
            return False
    
    except Exception as e:
        print(f"[Main] ERROR during provisioning: {e}")
        print("[Main] WARNING: Will continue anyway")
        return False


def display_initial_image(display_handler, timeout_ms=DEFAULT_TIMEOUT_MS):
    """Display initial image (wifi_connected.bmp, latest.bin, etc.)."""
    print("\n=== Displaying Initial Image ===")
    
    if not display_handler:
        print("[Main] ERROR: Display handler not available")
        return False
    
    # Priority list for initial images
    image_paths = [
        './resources/wifi_connected.bmp',
        './resources/home.bmp',
        './resources/received.bmp',
        './resources/latest.bin'
    ]
    
    display_path = None
    for path in image_paths:
        if file_exists(path):
            print(f"[Main] Found image: {path}")
            display_path = path
            break
            
    if not display_path:
        print(f"[Main] WARNING: No initial image found in {image_paths}")
        # Try to show a simple message at least
        display_handler.draw_text("Ready to receive messages...", 100, 240)
        return False
    
    # Display with timeout
    print(f"[Main] Displaying {display_path}...")
    start = utime.ticks_ms()
    
    if display_handler.display_file(display_path):
        elapsed = utime.ticks_diff(utime.ticks_ms(), start)
        print(f"[Main] Image displayed successfully ({elapsed}ms)")
        return True
    else:
        print(f"[Main] ERROR: Failed to display image")
        return False


def initialize_mqtt(timeout_ms=DEFAULT_TIMEOUT_MS):
    """Initialize MQTT handler."""
    print("\n=== Initializing MQTT ===")
    
    try:
        from mqtt_handler import MQTTHandler
        
        mqtt = MQTTHandler(timeout_ms=timeout_ms)
        
        # Load configuration
        print("[MQTT] Loading MQTT configuration...")
        if not mqtt.load_config():
            print("[MQTT] ERROR: Failed to load MQTT configuration")
            return None
        
        # Connect to broker
        print("[MQTT] Connecting to MQTT broker...")
        start = utime.ticks_ms()
        
        if mqtt.connect():
            elapsed = utime.ticks_diff(utime.ticks_ms(), start)
            print(f"[MQTT] Connected successfully ({elapsed}ms)")
            return mqtt
        else:
            print("[MQTT] WARNING: Failed to connect to MQTT broker initially")
            # Return the handler anyway so we can try again in the main loop
            return mqtt
    
    except ImportError as e:
        print(f"[MQTT] ERROR: Cannot import MQTT handler: {e}")
        return None
    except Exception as e:
        print(f"[MQTT] ERROR: Failed to initialize MQTT: {e}")
        return None


def main_loop(epd, display_handler, mqtt_handler, timeout_ms=DEFAULT_TIMEOUT_MS):
    """
    Main application loop.
    Continuously checks for MQTT messages and updates display.
    """
    print("\n=== Starting Main Loop ===")
    
    if not (epd and display_handler and mqtt_handler):
        print("[Main] ERROR: Missing required components for main loop")
        return False
    
    loop_count = 0
    error_count = 0
    max_consecutive_errors = 5
    check_interval_ms = 1000  # Check messages every 1 second
    last_check = utime.ticks_ms()
    
    print("[Main] Entering main loop (checking for MQTT messages)")
    if not mqtt_handler.is_connected:
        print("[Main] Starting loop in DISCONNECTED state, will attempt reconnect...")
    print("[Main] Press Ctrl+C to exit\n")
    
    try:
        while True:
            try:
                current_time = utime.ticks_ms()
                
                # Check for MQTT messages at regular intervals with timeout
                if utime.ticks_diff(current_time, last_check) >= check_interval_ms:
                    start = utime.ticks_ms()
                    
                    if mqtt_handler.is_connected and mqtt_handler.check_messages():
                        # Check if new message was received
                        if mqtt_handler.last_message:
                            print("[Main] New image received from MQTT ({})!".format(mqtt_handler.last_message_type))
                            print("[Main] Waking display and showing new image...")
                            
                            try:
                                # Determine which file to display
                                if mqtt_handler.last_message_type == 'bmp':
                                    update_file = './resources/received.bmp'
                                else:
                                    update_file = './resources/latest.bin'
                                
                                # Wake display from sleep (handled inside display_file now, but good to be safe)
                                display_handler.wake_display()
                                utime.sleep_ms(500)
                                
                                # Display the new image
                                if display_handler.display_file(update_file):
                                    print("[Main] Image updated successfully")
                                    error_count = 0
                                else:
                                    print("[Main] Failed to update image")
                                    error_count += 1
                                
                                mqtt_handler.last_message = None
                                mqtt_handler.last_message_type = None
                            
                            except Exception as e:
                                print(f"[Main] Error updating display: {e}")
                                error_count += 1
                        
                        elapsed = utime.ticks_diff(utime.ticks_ms(), start)
                        loop_count += 1
                        
                        # Print status every 30 checks (~30 seconds)
                        if loop_count % 30 == 0:
                            print(f"[Main] Status: Loop #{loop_count}, Errors: {error_count}, ({elapsed}ms/check)")
                    elif not mqtt_handler.is_connected:
                        # If not connected, just count it as a "waiting" state or minor error
                        if loop_count % 30 == 0:
                            print(f"[Main] Status: MQTT disconnected, Loop #{loop_count}")
                        error_count += 1
                    else:
                        print("[Main] ERROR: MQTT check failed")
                        error_count += 1
                    
                    last_check = current_time
                    
                    # Check if too many errors
                    if error_count >= max_consecutive_errors:
                        print(f"[Main] ERROR: Too many consecutive errors ({error_count})")
                        print("[Main] Attempting to reconnect MQTT...")
                        
                        if mqtt_handler.connect():
                            print("[Main] MQTT reconnected")
                            error_count = 0
                        else:
                            print("[Main] MQTT reconnection failed")
                            # Continue anyway, might recover
                            error_count = max_consecutive_errors - 1
                
                # Small sleep to prevent CPU spinning
                utime.sleep_ms(100)
            
            except KeyboardInterrupt:
                print("\n[Main] Keyboard interrupt received")
                break
            
            except Exception as e:
                print(f"[Main] ERROR in main loop: {e}")
                error_count += 1
                utime.sleep(1)
    
    except Exception as e:
        print(f"[Main] FATAL ERROR: {e}")
        return False
    
    finally:
        print("\n[Main] Shutting down gracefully...")
        try:
            mqtt_handler.disconnect()
            print("[Main] MQTT disconnected")
        except:
            pass
        print("[Main] Application terminated")
    
    return True


def main():
    """Main application entry point."""
    print("\n" + "="*60)
    print("  E-Paper Bulletin Board - Raspberry Pi Pico W")
    print("="*60)
    
    try:
        # Phase 1: Initialize display
        epd = initialize_display()
        if not epd:
            print("[Main] FATAL: Display initialization failed")
            return 1
        
        # Phase 2: Initialize WiFi
        wifi_manager = initialize_wifi(timeout_ms=DEFAULT_TIMEOUT_MS)
        if not wifi_manager:
            print("[Main] FATAL: WiFi initialization failed")
            return 1
        
        # Phase 3: Connect to WiFi
        wifi_ok = wifi_connection_phase(wifi_manager, epd=epd, timeout_ms=DEFAULT_TIMEOUT_MS)
        
        if not wifi_ok:
            print("[Main] WARNING: WiFi connection failed, but continuing anyway")
            print("[Main] App will retry WiFi provisioning and MQTT connection")
        
        # Phase 4: Initialize display handler
        try:
            from bmp_display import BMPDisplay
            display_handler = BMPDisplay(epd, timeout_ms=DEFAULT_TIMEOUT_MS)
        except ImportError as e:
            print(f"[Main] FATAL: Cannot import display handler: {e}")
            return 1
        except Exception as e:
            print(f"[Main] FATAL: Failed to initialize display handler: {e}")
            return 1
        
        # Phase 5: Display initial image
        if not display_initial_image(display_handler, timeout_ms=DEFAULT_TIMEOUT_MS):
            print("[Main] WARNING: Failed to display initial image")
            # Continue anyway
        
        # Phase 6: Initialize MQTT
        mqtt_handler = initialize_mqtt(timeout_ms=DEFAULT_TIMEOUT_MS)
        if not mqtt_handler:
            print("[Main] FATAL: MQTT handler creation failed")
            if display_handler:
                display_handler.draw_error("MQTT Configuration Error\nCheck conf/mqtt.conf")
            return 1
            
        if not mqtt_handler.is_connected:
            print("[Main] WARNING: MQTT connection failed")
            if display_handler:
                # Show error on screen but don't exit
                display_handler.draw_error("MQTT Connection Failed\nWill retry in background...")
                utime.sleep(2)
        
        # Phase 7: Main loop
        print("[Main] All systems initialized successfully!")
        
        # After MQTT success, try to display the home screen specifically
        if mqtt_handler.is_connected:
            print("[Main] MQTT connected, displaying home screen...")
            display_handler.display_file('./resources/home.bmp')
            
        print("[Main] Starting main application loop...")
        
        if main_loop(epd, display_handler, mqtt_handler, timeout_ms=DEFAULT_TIMEOUT_MS):
            return 0
        else:
            return 1
    
    except Exception as e:
        print(f"\n[Main] UNEXPECTED ERROR: {e}")
        import sys
        if hasattr(sys, 'print_exception'):
            sys.print_exception(e)
        return 1


if __name__ == "__main__":
    exit_code = main()
    print(f"\n[Main] Exit code: {exit_code}")
