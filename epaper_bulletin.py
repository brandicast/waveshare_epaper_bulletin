"""
E-Paper Bulletin Board Application
Main application for Raspberry Pi Pico W with Waveshare 7.5inch e-Paper

Flow:
1. Initialize e-paper display
2. Try to connect to WiFi (using saved config, max 3 retries)
3. If WiFi fails, start provisioning
4. Display initial image (`received.bmp`, `received.bin`, or `home.bmp`)
5. Connect to MQTT and listen for updates
6. Enter main loop: check MQTT, display updates, sleep
"""

import utime
import os
import sys
import gc
try:
    from machine import Pin, reset_cause, DEEPSLEEP_RESET, PWRON_RESET, HARD_RESET, WDT_RESET
except ImportError:
    Pin = None
    reset_cause = None
    DEEPSLEEP_RESET = None
    PWRON_RESET = None
    HARD_RESET = None
    WDT_RESET = None

# Set timeout for operations (avoid hanging)
DEFAULT_TIMEOUT_MS = 30000

USER_CONFIG_DIR = './user_config'
USER_WIFI_CONFIG = USER_CONFIG_DIR + '/wifi_config.json'
RECEIVED_BMP_PATH = USER_CONFIG_DIR + '/received.bmp'
RECEIVED_BIN_PATH = USER_CONFIG_DIR + '/received.bin'
MIDDLE_KEY_PIN = 2
MIDDLE_KEY_LONG_PRESS_MS = 5000

def file_exists(path):
    """Helper to check if file or directory exists in MicroPython."""
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def log_memory(stage):
    """Log current GC memory state if available."""
    try:
        free = gc.mem_free()
        alloc = gc.mem_alloc()
        print(f"[Main] {stage} memory: free={free}, alloc={alloc}")
    except AttributeError:
        print(f"[Main] {stage} memory: gc.mem_free unavailable")


def get_reset_cause_name():
    """Return a human-friendly reset cause name if available."""
    if reset_cause is None:
        return "unknown"
    try:
        cause = reset_cause()
        if cause == PWRON_RESET:
            return "PWRON_RESET"
        if cause == HARD_RESET:
            return "HARD_RESET"
        if cause == DEEPSLEEP_RESET:
            return "DEEPSLEEP_RESET"
        if cause == WDT_RESET:
            return "WDT_RESET"
        return str(cause)
    except Exception:
        return "unknown"


def clear_user_config_directory():
    """Remove the entire user_config directory and its contents."""
    try:
        if file_exists(USER_CONFIG_DIR):
            for entry in os.listdir(USER_CONFIG_DIR):
                path = USER_CONFIG_DIR + '/' + entry
                try:
                    os.remove(path)
                except OSError:
                    try:
                        # Fallback for subdirectories
                        for sub in os.listdir(path):
                            os.remove(path + '/' + sub)
                        os.rmdir(path)
                    except Exception:
                        pass
            try:
                os.rmdir(USER_CONFIG_DIR)
            except OSError:
                pass
            print("[Main] Cleared user_config directory")
            return True
    except Exception as e:
        print(f"[Main] WARNING: Failed to clear user_config directory: {e}")
    return False


def initialize_middle_key_button():
    """Initialize the middle key pin for long-press detection."""
    if Pin is None:
        return None
    try:
        return Pin(MIDDLE_KEY_PIN, Pin.IN, Pin.PULL_UP)
    except Exception as e:
        print(f"[Main] WARNING: Could not initialize middle key pin: {e}")
        return None


def is_middle_key_long_pressed(reset_button, hold_ms=MIDDLE_KEY_LONG_PRESS_MS):
    """Detect a long press of the middle key (active-low)."""
    if not reset_button:
        return False
    if reset_button.value() != 0:
        return False

    print("[Main] Middle key press detected, waiting for long press...")
    start = utime.ticks_ms()
    while reset_button.value() == 0:
        if utime.ticks_diff(utime.ticks_ms(), start) >= hold_ms:
            print("[Main] Middle key long press confirmed")
            return True
        utime.sleep_ms(50)
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
        from core.wifi_manager import WiFiManager
        
        wm = WiFiManager(timeout_ms=timeout_ms)
        print("[WiFi] WiFi manager created")
        
        return wm
    
    except ImportError as e:
        print(f"[WiFi] ERROR: Cannot import WiFi manager: {e}")
        return None
    except Exception as e:
        print(f"[WiFi] ERROR: Failed to initialize WiFi: {e}")
        return None


def wifi_connection_phase(wifi_manager, epd=None, timeout_ms=DEFAULT_TIMEOUT_MS, reset_button=None):
    """Handle WiFi connection with saved config or provisioning."""
    print("\n=== WiFi Connection Phase ===")
    
    if not wifi_manager:
        print("[Main] ERROR: WiFi manager not available")
        return False

    if reset_button and is_middle_key_long_pressed(reset_button):
        print("[Main] Middle key long press detected; clearing user_config and rebooting...")
        clear_user_config_directory()
        try:
            import machine
            machine.reset()
        except Exception as e:
            print(f"[Main] WARNING: Failed to reboot after clearing user_config: {e}")
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
    
    print("[Main] Saved WiFi config failed.")
    
    # Saved config failed, start provisioning
    print("[Main] Starting WiFi provisioning...")
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
    """Display the WiFi-connected image after WiFi is established."""
    print("\n=== Displaying WiFi Connected Image ===")
    
    if not display_handler:
        print("[Main] ERROR: Display handler not available")
        return False
    
    wifi_image_path = './resources/wifi_connected.bmp'
    if not file_exists(wifi_image_path):
        print("[Main] WARNING: wifi_connected.bmp not found; leaving current screen")
        return False

    print(f"[Main] Found image: {wifi_image_path}")
    print(f"[Main] Displaying {wifi_image_path}...")
    start = utime.ticks_ms()
    
    if display_handler.display_file(wifi_image_path):
        elapsed = utime.ticks_diff(utime.ticks_ms(), start)
        print(f"[Main] Image displayed successfully ({elapsed}ms)")
        return True
    else:
        print(f"[Main] ERROR: Failed to display image")
        return False


def display_received_or_home(display_handler):
    """Display the latest received image or fallback to home.bmp."""
    print("\n=== Displaying Received or Home Image ===")
    if not display_handler:
        print("[Main] ERROR: Display handler not available")
        return False

    received_candidates = []
    if file_exists(RECEIVED_BMP_PATH):
        received_candidates.append(RECEIVED_BMP_PATH)
    if file_exists(RECEIVED_BIN_PATH):
        received_candidates.append(RECEIVED_BIN_PATH)

    if received_candidates:
        display_path = max(received_candidates, key=lambda p: os.stat(p)[8])
        print(f"[Main] Using latest received image: {display_path}")
    elif file_exists('./resources/home.bmp'):
        display_path = './resources/home.bmp'
        print(f"[Main] No received image found; using home screen: {display_path}")
    else:
        print("[Main] WARNING: No home image found")
        display_handler.draw_text("Ready to receive messages...", 100, 240)
        return False

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
    
    log_memory("Before MQTT init")
    gc.collect()
    log_memory("After GC before MQTT init")
    
    try:
        from core.mqtt_handler import MQTTHandler
        
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
        try:
            import sys
            sys.print_exception(e)
        except Exception:
            pass
        return None


def main_loop(epd, display_handler, mqtt_handler, timeout_ms=DEFAULT_TIMEOUT_MS, reset_button=None):
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
    reconnect_interval_ms = 5000  # Try reconnect every 5 seconds when disconnected
    last_check = utime.ticks_ms()
    last_reconnect_attempt = utime.ticks_ms()
    
    print("[Main] Entering main loop (checking for MQTT messages)")
    if not mqtt_handler.is_connected:
        print("[Main] Starting loop in DISCONNECTED state, will attempt reconnect...")
    print("[Main] Press Ctrl+C to exit\n")
    
    try:
        while True:
            try:
                current_time = utime.ticks_ms()

                if reset_button and is_middle_key_long_pressed(reset_button):
                    print("[Main] Middle key long press detected during runtime; clearing user_config and rebooting...")
                    clear_user_config_directory()
                    try:
                        import machine
                        machine.reset()
                    except Exception as e:
                        print(f"[Main] WARNING: Failed to reboot: {e}")
                    return False
                
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
                                    update_file = RECEIVED_BMP_PATH
                                else:
                                    update_file = RECEIVED_BIN_PATH
                                
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
                        
                        # Print status every 60 checks (~60 seconds)
                        if loop_count % 60 == 0:
                            print(f"[Main] Status: Loop #{loop_count}, Errors: {error_count}, ({elapsed}ms/check)")
                            
                            # Prevent overflow (reset every 1 million loops)
                            if loop_count > 1000000:
                                loop_count = 0
                                
                    elif not mqtt_handler.is_connected:
                        if utime.ticks_diff(current_time, last_reconnect_attempt) >= reconnect_interval_ms:
                            print("[Main] MQTT disconnected, attempting reconnect...")
                            if mqtt_handler.connect():
                                print("[Main] MQTT reconnected")
                                error_count = 0
                            else:
                                print("[Main] MQTT reconnect failed")
                            last_reconnect_attempt = current_time

                        if loop_count % 60 == 0:
                            print(f"[Main] Status: MQTT disconnected, Loop #{loop_count}")
                    else:
                        print("[Main] ERROR: MQTT check failed")
                        error_count += 1

                    loop_count += 1
                    last_check = current_time
                    
                    # Check if too many errors
                    if error_count >= max_consecutive_errors:
                        print(f"[Main] ERROR: Too many consecutive errors ({error_count})")
                        print("[Main] Attempting to reconnect MQTT...")
                        
                        log_memory("Before reconnect attempt")
                        if mqtt_handler.connect():
                            print("[Main] MQTT reconnected")
                            log_memory("After reconnect success")
                            error_count = 0
                        else:
                            print("[Main] MQTT reconnection failed")
                            log_memory("After reconnect failure")
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
    print("[Boot] main() entered")
    print(f"[Boot] reset cause: {get_reset_cause_name()}")
    print("\n" + "="*60)
    print("  E-Paper Bulletin Board - Raspberry Pi Pico W")
    print("="*60)
    
    try:
        # Phase 0: System Welcome & Initial Display Setup
        print("\n" + "="*40)
        print("BreadSoft E-Paper Bulletin System Starting")
        print("="*40)
        
        # Initialize display hardware immediately
        try:
            from lib.epaper_7_5_b import EPD_7in5_B
            epd = EPD_7in5_B()
            epd.init() # Ensure it's ready
            print("[Main] Display initialized successfully")
        except Exception as e:
            print(f"[Main] FATAL: Display initialization failed: {e}")
            import sys
            if hasattr(sys, 'print_exception'):
                sys.print_exception(e)
            return 1
        
        try:
            from core.bmp_display import BMPDisplay
            display_handler = BMPDisplay(epd, timeout_ms=DEFAULT_TIMEOUT_MS)
            log_memory("After BMPDisplay creation")
        except Exception as e:
            print(f"[Main] FATAL: BMPDisplay creation failed: {e}")
            import sys
            if hasattr(sys, 'print_exception'):
                sys.print_exception(e)
            return 1
        
        # Show Welcome Screen before anything else
        try:
            if file_exists('./resources/welcome.bmp'):
                print("[Main] Displaying welcome screen...")
                display_handler.display_file('./resources/welcome.bmp')
            else:
                print("[Main] Welcome screen not found, drawing text...")
                display_handler.draw_text("BreadSoft Bulletin\nStarting system...", 50, 200)
        except Exception as e:
            print(f"[Main] WARNING: Failed to display welcome screen: {e}")
            import sys
            if hasattr(sys, 'print_exception'):
                sys.print_exception(e)

        # Phase 1: Initialize WiFi
        wifi_manager = initialize_wifi(timeout_ms=DEFAULT_TIMEOUT_MS)
        if not wifi_manager:
            print("[Main] FATAL: WiFi initialization failed")
            return 1
        
        # Phase 3: Connect to WiFi
        reset_button = initialize_middle_key_button()
        wifi_ok = wifi_connection_phase(wifi_manager, epd=epd, timeout_ms=DEFAULT_TIMEOUT_MS, reset_button=reset_button)
        
        if not wifi_ok:
            print("[Main] WARNING: WiFi connection failed, but continuing anyway")
            print("[Main] App will retry WiFi provisioning and MQTT connection")
        
        # Phase 4: Initialize display handler
        try:
            from core.bmp_display import BMPDisplay
            display_handler = BMPDisplay(epd, timeout_ms=DEFAULT_TIMEOUT_MS)
        except ImportError as e:
            print(f"[Main] FATAL: Cannot import display handler: {e}")
            return 1
        except Exception as e:
            print(f"[Main] FATAL: Failed to initialize display handler: {e}")
            return 1
        
        # Phase 5: Display wifi connected image
        if wifi_ok:
            if not display_initial_image(display_handler, timeout_ms=DEFAULT_TIMEOUT_MS):
                print("[Main] WARNING: Failed to display wifi connected image")
        else:
            print("[Main] Skipping wifi connected image because WiFi is not connected")

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
        
        if mqtt_handler.is_connected:
            print("[Main] MQTT connected, displaying latest received image or home screen...")
            display_received_or_home(display_handler)
        
        print("[Main] Starting main application loop...")
        
        if main_loop(epd, display_handler, mqtt_handler, timeout_ms=DEFAULT_TIMEOUT_MS, reset_button=reset_button):
            return 0
        else:
            return 1
    
    except Exception as e:
        print(f"\n[Main] UNEXPECTED ERROR: {e}")
        import sys
        if hasattr(sys, 'print_exception'):
            sys.print_exception(e)
        # Try to display error on screen if possible
        try:
            if 'display_handler' in locals() and display_handler:
                display_handler.draw_error(f"System Error\n{str(e)[:40]}")
        except:
            pass
        return 1


if __name__ == "__main__":
    exit_code = main()
    print(f"\n[Main] Exit code: {exit_code}")
