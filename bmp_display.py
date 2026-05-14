"""
Display Utility Module
Handles raw pixel data loading and display on e-paper
Supports monochrome (1-bit) pixel format: 800x480 = 48,000 bytes
"""

import os
import utime
import gc

class BMPDisplay:
    def __init__(self, epd, timeout_ms=30000):
        """
        Initialize Display utility
        epd: e-paper display instance (EPD_7in5_B)
        timeout_ms: operation timeout in milliseconds
        """
        self.epd = epd
        self.timeout_ms = timeout_ms
        self.last_displayed = None
        self.expected_size = 48000  # 800 * 480 / 8 bytes
    
    def _file_exists(self, path):
        """Helper to check if file or directory exists."""
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def display_file(self, filepath):
        """
        Display raw pixel data or BMP file on the e-paper display
        filepath: path to image file
        Returns True if successful, False otherwise
        """
        try:
            if not self._file_exists(filepath):
                print("[Display] File not found: {}".format(filepath))
                return False
            
            # Check if it's a BMP file (Signature "BM" = 0x42 0x4D)
            is_bmp = False
            file_size = 0
            width = 800
            height = 480
            
            try:
                file_size = os.stat(filepath)[6]
                with open(filepath, 'rb') as f:
                    header = f.read(54)
                    if header[:2] == b'BM':
                        is_bmp = True
                        # Parse width and height from BMP header (little-endian)
                        width = int.from_bytes(header[18:22], 'little')
                        height = int.from_bytes(header[22:26], 'little')
            except Exception as e:
                print("[Display] Error reading header: {}".format(e))

            print("[Display] Loading {} ({} bytes, {}x{})".format(filepath, file_size, width, height))
            
            # Calculate centering offsets
            x_offset = max(0, (800 - width) // 2)
            y_offset = max(0, (480 - height) // 2)
            
            # Always clear the screen before displaying new content
            print("[Display] Clearing screen before rendering...")
            self.wake_display()
            self.epd.clear("white")
            
            start_time = utime.ticks_ms()
            success = False
            
            if is_bmp:
                print("[Display] Detected BMP format, centering at {},{}".format(x_offset, y_offset))
                # Try color display first (supports Black/White/Red)
                print("[Display] Attempting 24-bit color BMP rendering...")
                success = self.epd.display_bmp_color(filepath, x=x_offset, y=y_offset)
                if not success:
                    print("[Display] display_bmp_color failed, trying 1-bit display_bmp...")
                    success = self.epd.display_bmp(filepath, x=x_offset, y=y_offset)
                
                if success:
                    print("[Display] BMP rendering finished, refreshing screen...")
                    self.epd.display()
            else:
                # Fallback to raw pixel data (assumed 800x480)
                print("[Display] Treating as raw pixel data...")
                success = self._load_and_display_raw(filepath)
            
            if not success:
                print("[Display] Failed to display image")
                return False
            
            elapsed = utime.ticks_diff(utime.ticks_ms(), start_time)
            print("[Display] Image displayed successfully ({}ms)".format(elapsed))
            
            # Enter deep sleep after display
            print("[Display] Entering deep sleep mode")
            utime.sleep_ms(500)
            
            try:
                self.epd.sleep()
                self.last_displayed = filepath
                print("[Display] E-paper in deep sleep mode")
            except Exception as e:
                print("[Display] Error entering sleep: {}".format(e))
            
            return True
        
        except Exception as e:
            print("[Display] Error displaying file: {}".format(e))
            return False
    
    def _load_and_display_raw(self, filepath):
        """Load and display raw pixel data file using memory-efficient methods."""
        gc.collect() # Free up memory before allocation
        try:
            with open(filepath, 'rb') as f:
                # Read directly into the existing e-paper buffer to avoid double allocation
                # Use a memoryview for safer and faster access if needed, but readinto works on bytearray
                print("[Display] Reading file into buffer...")
                bytes_read = f.readinto(self.epd.buffer_black)
                
                print("[Display] Read {} bytes into black buffer (expected {})".format(bytes_read, self.expected_size))
                
                # If file was smaller than buffer, fill the remainder with white (1)
                if bytes_read < self.expected_size:
                    print("[Display] Padding remaining {} bytes with white".format(self.expected_size - bytes_read))
                    for i in range(bytes_read, self.expected_size):
                        self.epd.buffer_black[i] = 1 # WHITE
                
                # Ensure red buffer is cleared (0) without re-allocating
                # Using a loop is slower but memory-safe. 
                # Better: self.epd.imagered.fill(0) if imagered is available
                if hasattr(self.epd, 'imagered'):
                    self.epd.imagered.fill(0)
                else:
                    for i in range(len(self.epd.buffer_red)):
                        self.epd.buffer_red[i] = 0
                
                # Display the buffer
                print("[Display] Triggering display refresh...")
                self.epd.display()
                return True
        
        except Exception as e:
            print("[Display] Error loading pixel data: {}".format(e))
            import sys
            if hasattr(sys, 'print_exception'):
                sys.print_exception(e)
            return False
    
    def clear_display(self):
        """Clear the display (white)."""
        try:
            self.epd.clear("white")
            print("[Display] Display cleared")
            return True
        except Exception as e:
            print("[Display] Error clearing display: {}".format(e))
            return False
    
    def wake_display(self):
        """Wake up display from sleep mode."""
        try:
            self.epd.wake_up()
            print("[Display] Display woken up")
            return True
        except Exception as e:
            print("[Display] Error waking display: {}".format(e))
            return False

    def draw_text(self, text, x, y, color="black", is_red=False):
        """Draw text on the display."""
        try:
            # color mapping for the driver
            c = 0x00 if color == "black" else 0xFF
            if is_red:
                self.epd.imagered.text(text, x, y, c)
            else:
                self.epd.imageblack.text(text, x, y, c)
            return True
        except Exception as e:
            print("[Display] Error drawing text: {}".format(e))
            return False

    def draw_error(self, message):
        """Display a full-screen error message."""
        try:
            self.wake_display()
            self.epd.clear("white")
            # Draw a red box at the top
            self.epd.draw_rect(0, 0, 800, 60, 2, fill=True) # 2 = RED
            # Draw white text on red background
            self.epd.imagered.text("SYSTEM ERROR", 330, 25, 1) # 1 = WHITE in imagered context
            
            # Draw the actual error message in black
            # Basic word wrapping or just centering
            self.epd.imageblack.text(message, 100, 150, 0) # 0 = BLACK
            
            print("[Display] Showing error: {}".format(message))
            self.epd.display()
            self.epd.sleep()
            return True
        except Exception as e:
            print("[Display] Error showing error screen: {}".format(e))
            return False
