"""
7.5inch e-Paper B V3 完整控制程式
支援 BMP 顯示、多種初始化模式、功耗優化

適用於 Raspberry Pi Pico / MicroPython
"""

from machine import Pin, SPI
import framebuf
import utime

# ==================== 顯示解析度 ====================
EPD_WIDTH = 800
EPD_HEIGHT = 480

# ==================== 預設腳位 ====================
RST_PIN = 12
DC_PIN = 8
CS_PIN = 9
BUSY_PIN = 13


class EPD_7in5_B:
    # 顏色常數
    BLACK = 0
    WHITE = 1
    RED = 2
    
    def __init__(self, spi_bus=1, rst=RST_PIN, dc=DC_PIN, cs=CS_PIN, busy=BUSY_PIN, mode="normal"):
        """
        初始化電子紙
        
        參數:
            spi_bus: SPI 匯流排編號 (0 或 1)
            rst, dc, cs, busy: 腳位編號
            mode: "normal" / "fast" / "partial"
        """
        self.rst_pin = Pin(rst, Pin.OUT)
        self.dc_pin = Pin(dc, Pin.OUT)
        self.cs_pin = Pin(cs, Pin.OUT)
        self.busy_pin = Pin(busy, Pin.IN, Pin.PULL_UP)
        
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        
        # SPI 初始化
        self.spi = SPI(spi_bus)
        self.spi.init(baudrate=4000000, polarity=0, phase=0)
        
        # 雙 buffer (黑白 + 紅色)
        self.buffer_black = bytearray(self.height * self.width // 8)
        self.buffer_red = bytearray(self.height * self.width // 8)
        
        # FrameBuffer 輔助繪圖
        self.imageblack = framebuf.FrameBuffer(
            self.buffer_black, self.width, self.height, framebuf.MONO_HLSB)
        self.imagered = framebuf.FrameBuffer(
            self.buffer_red, self.width, self.height, framebuf.MONO_HLSB)
        
        # 根據模式選擇初始化
        if mode == "fast":
            self.init_fast()
        elif mode == "partial":
            self.init_partial()
        else:
            self.init()
        
        print(f"初始化完成 - 模式: {mode}")
    
    # ==================== 底層通訊 ====================
    def _digital_write(self, pin, value):
        pin.value(value)
    
    def _digital_read(self, pin):
        return pin.value()
    
    def _delay_ms(self, ms):
        utime.sleep(ms / 1000.0)
    
    def _send_command(self, cmd):
        self._digital_write(self.dc_pin, 0)
        self._digital_write(self.cs_pin, 0)
        self.spi.write(bytearray([cmd]))
        self._digital_write(self.cs_pin, 1)
    
    def _send_data(self, data):
        self._digital_write(self.dc_pin, 1)
        self._digital_write(self.cs_pin, 0)
        self.spi.write(bytearray([data]))
        self._digital_write(self.cs_pin, 1)
    
    def _send_data_bytes(self, data_bytes):
        self._digital_write(self.dc_pin, 1)
        self._digital_write(self.cs_pin, 0)
        self.spi.write(data_bytes)
        self._digital_write(self.cs_pin, 1)
    
    def _reset(self):
        self._digital_write(self.rst_pin, 1)
        self._delay_ms(200)
        self._digital_write(self.rst_pin, 0)
        self._delay_ms(2)
        self._digital_write(self.rst_pin, 1)
        self._delay_ms(200)
    
    def _wait_until_idle(self):
        while self._digital_read(self.busy_pin) == 0:
            self._delay_ms(10)
        self._delay_ms(10)
    
    def _turn_on_display(self):
        self._send_command(0x12)  # DISPLAY REFRESH
        self._delay_ms(100)
        self._wait_until_idle()
    
    # ==================== 初始化模式 ====================
    def init(self):
        """標準初始化 (Waveshare 官方，最穩定)"""
        self._reset()
        
        self._send_command(0x01)  # POWER SETTING
        self._send_data(0x07)
        self._send_data(0x07)
        self._send_data(0x3f)
        self._send_data(0x3f)
        
        self._send_command(0x06)  # BOOSTER SOFT START
        self._send_data(0x17)
        self._send_data(0x17)
        self._send_data(0x28)
        self._send_data(0x17)
        
        self._send_command(0x04)  # POWER ON
        self._delay_ms(100)
        self._wait_until_idle()
        
        self._send_command(0x00)  # PANEL SETTING
        self._send_data(0x0F)
        
        self._send_command(0x61)  # RESOLUTION (800x480)
        self._send_data(0x03)
        self._send_data(0x20)
        self._send_data(0x01)
        self._send_data(0xE0)
        
        self._send_command(0x50)  # VCOM INTERVAL
        self._send_data(0x11)
        self._send_data(0x07)
        
        self._send_command(0x60)  # TCON
        self._send_data(0x22)
    
    def init_fast(self):
        """快速初始化 (犧牲少許對比度換取速度)"""
        self._reset()
        
        self._send_command(0x00)
        self._send_data(0x0F)
        
        self._send_command(0x04)
        self._delay_ms(100)
        self._wait_until_idle()
        
        self._send_command(0x06)
        self._send_data(0x27)
        self._send_data(0x27)
        self._send_data(0x18)
        self._send_data(0x17)
        
        self._send_command(0xE0)
        self._send_data(0x02)
        self._send_command(0xE5)
        self._send_data(0x5A)
        
        self._send_command(0x50)
        self._send_data(0x11)
        self._send_data(0x07)
        
        self._send_command(0x61)
        self._send_data(0x03)
        self._send_data(0x20)
        self._send_data(0x01)
        self._send_data(0xE0)
        
        self._send_command(0x60)
        self._send_data(0x22)
    
    def init_partial(self):
        """局部更新模式初始化 (僅限黑白，不穩定，不建議使用)"""
        self._reset()
        
        self._send_command(0x00)
        self._send_data(0x1F)
        
        self._send_command(0x04)
        self._delay_ms(100)
        self._wait_until_idle()
        
        self._send_command(0xE0)
        self._send_data(0x02)
        self._send_command(0xE5)
        self._send_data(0x6E)
        
        self._send_command(0x50)
        self._send_data(0xA9)
        self._send_data(0x07)
    
    # ==================== 基本畫面操作 ====================
    def clear(self, color="white"):
        """清除畫面 (white/black/red)"""
        if color == "white":
            self.imageblack.fill(1)
            self.imagered.fill(0)
        elif color == "black":
            self.imageblack.fill(0)
            self.imagered.fill(0)
        elif color == "red":
            self.imageblack.fill(1)
            self.imagered.fill(1)
        self.display()
    
    def display(self):
        """將 buffer 資料刷新到螢幕 (分段發送以提高穩定性)"""
        # 800x480 / 8 = 48000 bytes
        chunk_size = 4000 # 每次發送 4000 bytes
        
        # 發送黑白資料
        self._send_command(0x10)
        for i in range(0, len(self.buffer_black), chunk_size):
            self._send_data_bytes(self.buffer_black[i:i + chunk_size])
        
        # 發送紅色資料
        self._send_command(0x13)
        for i in range(0, len(self.buffer_red), chunk_size):
            self._send_data_bytes(self.buffer_red[i:i + chunk_size])
        
        self._turn_on_display()
    
    def sleep(self):
        """進入深度睡眠 (~15μA)"""
        self._send_command(0x02)  # POWER OFF
        self._wait_until_idle()
        self._send_command(0x07)  # DEEP SLEEP
        self._send_data(0xA5)
    
    def wake_up(self):
        """從深度睡眠喚醒 (必須執行硬體重置與初始化)"""
        print("  [EPD] Waking from deep sleep (Hardware Reset)...")
        self._reset()
        self.init()
        print("  [EPD] Display initialized and ready")
    
    # ==================== 繪圖輔助函式 ====================
    def set_pixel(self, x, y, color):
        """設定單一像素顏色 (0=黑, 1=白, 2=紅)"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        if color == self.BLACK:
            self.imageblack.pixel(x, y, 0)
            self.imagered.pixel(x, y, 0)
        elif color == self.WHITE:
            self.imageblack.pixel(x, y, 1)
            self.imagered.pixel(x, y, 0)
        elif color == self.RED:
            self.imageblack.pixel(x, y, 1)
            self.imagered.pixel(x, y, 1)
    
    def draw_rect(self, x, y, w, h, color, fill=False):
        """繪製矩形"""
        if fill:
            for i in range(x, min(x + w, self.width)):
                for j in range(y, min(y + h, self.height)):
                    self.set_pixel(i, j, color)
        else:
            # 上邊
            for i in range(x, min(x + w, self.width)):
                self.set_pixel(i, y, color)
            # 下邊
            if h > 1:
                for i in range(x, min(x + w, self.width)):
                    self.set_pixel(i, min(y + h - 1, self.height - 1), color)
            # 左邊
            if h > 2:
                for j in range(y + 1, min(y + h - 1, self.height)):
                    self.set_pixel(x, j, color)
            # 右邊
            if w > 1 and h > 2:
                for j in range(y + 1, min(y + h - 1, self.height)):
                    self.set_pixel(min(x + w - 1, self.width - 1), j, color)
    
    def draw_line(self, x0, y0, x1, y1, color):
        """Bresenham 直線演算法"""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        
        while True:
            self.set_pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
    
    def draw_circle(self, xc, yc, r, color, fill=False):
        """繪製圓形"""
        if fill:
            for y in range(-r, r + 1):
                w = int((r * r - y * y) ** 0.5)
                for x in range(-w, w + 1):
                    self.set_pixel(xc + x, yc + y, color)
        else:
            x = 0
            y = r
            d = 3 - 2 * r
            while x <= y:
                self.set_pixel(xc + x, yc + y, color)
                self.set_pixel(xc - x, yc + y, color)
                self.set_pixel(xc + x, yc - y, color)
                self.set_pixel(xc - x, yc - y, color)
                self.set_pixel(xc + y, yc + x, color)
                self.set_pixel(xc - y, yc + x, color)
                self.set_pixel(xc + y, yc - x, color)
                self.set_pixel(xc - y, yc - x, color)
                if d < 0:
                    d = d + 4 * x + 6
                else:
                    d = d + 4 * (x - y) + 10
                    y -= 1
                x += 1
    
    # ==================== BMP 影像顯示 ====================
    def display_bmp(self, filename, x=0, y=0):
        """
        顯示 1-bit 單色 BMP 檔案 (黑白)
        
        參數:
            filename: BMP 檔案名稱
            x, y: 顯示位置 (左上角)
        
        限制:
            - 僅支援 1-bit 單色 BMP
            - 建議尺寸不超過 800x480
        """
        try:
            with open(filename, 'rb') as f:
                # 讀取 BMP 檔頭 (前 54 bytes)
                header = f.read(54)
                
                # 檢查 BMP 簽章 "BM"
                if header[0] != 0x42 or header[1] != 0x4D:
                    print("錯誤：不是有效的 BMP 檔案")
                    return False
                
                # 解析影像資訊
                data_offset = int.from_bytes(header[10:14], 'little')
                width = int.from_bytes(header[18:22], 'little')
                height = int.from_bytes(header[22:26], 'little')
                bit_count = int.from_bytes(header[28:30], 'little')
                
                print(f"BMP 資訊: {width}x{height}, {bit_count} bits/pixel")
                
                # 檢查是否為單色 BMP
                if bit_count != 1:
                    print("警告：建議使用 1-bit 單色 BMP (0=黑, 1=白)")
                    print("彩色 BMP 請使用 display_bmp_color()")
                
                # 計算每行 bytes 和對齊
                row_bytes = (width + 7) // 8
                padding = (4 - (row_bytes % 4)) % 4
                
                # 移動到影像資料
                f.seek(data_offset)
                
                # Optimization: Only process non-white pixels since we already cleared to white
                black = self.BLACK
                for row in range(height):
                    if row % 100 == 0:
                        print(f"  [EPD] Processing row {row}/{height}...")
                    
                    screen_y = y + (height - 1 - row)
                    if screen_y < 0 or screen_y >= self.height:
                        f.read(row_bytes + padding)
                        continue
                    
                    row_data = f.read(row_bytes + padding)
                    
                    for col in range(width):
                        byte_idx = col >> 3 # Equivalent to col // 8
                        bit_pos = 7 - (col & 7) # Equivalent to 7 - (col % 8)
                        
                        # Only call set_pixel if it's a black pixel (0 in 1-bit BMP)
                        if not (row_data[byte_idx] & (1 << bit_pos)):
                            screen_x = x + col
                            if 0 <= screen_x < self.width:
                                self.set_pixel(screen_x, screen_y, black)
            
            print("  [EPD] BMP processing complete")
            return True
            
        except Exception as e:
            print(f"BMP 讀取錯誤: {e}")
            return False
    
    def display_bmp_color(self, filename, x=0, y=0, red_threshold=128):
        """
        顯示 24-bit 彩色 BMP 檔案 (自動轉換為黑/白/紅)
        
        參數:
            filename: BMP 檔案名稱
            x, y: 顯示位置
            red_threshold: 紅色判斷閾值 (0-255, 越高越嚴格)
        
        轉換規則:
            - 若 R > G 且 R > B 且 R > red_threshold → 紅色
            - 否則根據亮度決定黑色或白色
        """
        try:
            with open(filename, 'rb') as f:
                header = f.read(54)
                
                if header[0] != 0x42 or header[1] != 0x4D:
                    print("錯誤：不是有效的 BMP 檔案")
                    return False
                
                data_offset = int.from_bytes(header[10:14], 'little')
                width = int.from_bytes(header[18:22], 'little')
                height = int.from_bytes(header[22:26], 'little')
                bit_count = int.from_bytes(header[28:30], 'little')
                
                print(f"BMP 資訊: {width}x{height}, {bit_count} bits/pixel")
                
                # 僅支援 24-bit RGB BMP
                if bit_count != 24:
                    print(f"警告：建議使用 24-bit BMP，目前為 {bit_count}-bit")
                    if bit_count == 1:
                        return self.display_bmp(filename, x, y)
                
                # 每行 bytes (24-bit = 3 bytes/pixel)
                row_bytes = width * 3
                padding = (4 - (row_bytes % 4)) % 4
                
                f.seek(data_offset)
                
                for row in range(height):
                    if row % 50 == 0:
                        print(f"  [EPD] Processing row {row}/{height}...")
                        
                    screen_y = y + (height - 1 - row)
                    if screen_y < 0 or screen_y >= self.height:
                        f.read(row_bytes + padding)
                        continue
                    
                    row_data = f.read(row_bytes + padding)
                    
                    for col in range(width):
                        screen_x = x + col
                        if screen_x < 0 or screen_x >= self.width:
                            continue
                        
                        # BGR 順序 (Windows BMP)
                        b = row_data[col * 3]
                        g = row_data[col * 3 + 1]
                        r = row_data[col * 3 + 2]
                        
                        # 紅色判斷
                        if r > g and r > b and r > red_threshold:
                            color = self.RED
                        else:
                            # 亮度轉換 (Y = 0.299R + 0.587G + 0.114B)
                            brightness = (r * 299 + g * 587 + b * 114) // 1000
                            color = self.BLACK if brightness < 128 else self.WHITE
                        
                        self.set_pixel(screen_x, screen_y, color)
            
            print("  [EPD] BMP Color processing complete")
            return True
            
        except Exception as e:
            print(f"BMP 讀取錯誤: {e}")
            return False
    
    def display_preconverted(self, bw_data, red_data=None):
        """
        顯示預先轉換好的影像資料 (最快)
        
        參數:
            bw_data: 黑白影像 bytearray (每 bit 代表一個像素, 1=白, 0=黑)
            red_data: 紅色影像 bytearray (可選, 1=紅, 0=無紅)
        
        注意:
            - 資料長度必須為 800*480//8 = 48000 bytes
            - 此方法直接複製到 buffer，不進行任何轉換
        """
        if len(bw_data) != len(self.buffer_black):
            print(f"錯誤：黑白資料長度不符 (需 {len(self.buffer_black)} bytes)")
            return False
        
        # 直接複製到 buffer
        self.buffer_black[:] = bw_data
        
        if red_data:
            if len(red_data) != len(self.buffer_red):
                print(f"錯誤：紅色資料長度不符 (需 {len(self.buffer_red)} bytes)")
                return False
            self.buffer_red[:] = red_data
        else:
            # 沒有紅色資料時，紅色 buffer 全為 0
            for i in range(len(self.buffer_red)):
                self.buffer_red[i] = 0
        
        return True
    
    # ==================== 效能優化 ====================
    def set_spi_speed(self, baudrate):
        """動態調整 SPI 速率 (預設 4MHz，最高可到 10MHz)"""
        self.spi.init(baudrate=baudrate, polarity=0, phase=0)
        print(f"SPI 速率設為 {baudrate} Hz")
    
    def set_voltage(self, vgh="20V", vdh="15V", vdl="-15V"):
        """
        調整驅動電壓 (影響對比度與功耗)
        電壓越低越省電，但對比度較差
        """
        vgh_table = {"9V": 0x00, "10V": 0x01, "11V": 0x02, "12V": 0x03,
                     "17V": 0x04, "18V": 0x05, "19V": 0x06, "20V": 0x07}
        
        vdh_table = {10: 0x28, 11: 0x2C, 12: 0x30, 13: 0x34, 14: 0x38, 15: 0x3C}
        vdl_table = {-10: 0x28, -11: 0x2C, -12: 0x30, -13: 0x34, -14: 0x38, -15: 0x3C}
        
        self._send_command(0x01)  # POWER SETTING
        self._send_data(0x07)
        self._send_data(vgh_table.get(vgh, 0x07))
        self._send_data(vdh_table.get(vdh, 0x3F))
        self._send_data(vdl_table.get(vdl, 0x3F))
        print(f"電壓設定: VGH/VGL={vgh}, VDH={vdh}V, VDL={vdl}V")


# ==================== 範例主程式 ====================
if __name__ == '__main__':
    # 初始化 (可選擇 normal/fast/partial)
    epd = EPD_7in5_B(mode="normal")
    
    print("=== 開始測試 ===\n")
    
    # 測試 1: 基本繪圖
    print("1. 基本繪圖測試...")
    epd.clear("white")
    epd.imageblack.text("Hello Waveshare!", 10, 10, 0x00)
    epd.imagered.text("7.5 inch e-Paper", 10, 40, 0xFF)
    epd.draw_rect(10, 70, 200, 100, epd.BLACK, fill=False)
    epd.draw_rect(20, 80, 180, 80, epd.RED, fill=True)
    epd.display()
    utime.sleep(3)
    
    # 測試 2: BMP 顯示 (需準備 BMP 檔案)
    print("\n2. BMP 顯示測試...")
    epd.clear("white")
    
    # 嘗試顯示單色 BMP (如果檔案存在)
    try:
        epd.display_bmp("/sd/test_bw.bmp", x=0, y=0)
        epd.display()
        utime.sleep(2)
    except:
        print("  找不到 /sd/test_bw.bmp，跳過")
    
    # 嘗試顯示彩色 BMP (如果檔案存在)
    try:
        epd.display_bmp_color("/sd/test_color.bmp", x=0, y=0)
        epd.display()
        utime.sleep(2)
    except:
        print("  找不到 /sd/test_color.bmp，跳過")
    
    # 測試 3: 圓形與線條
    print("\n3. 幾何圖形測試...")
    epd.clear("white")
    epd.draw_circle(400, 240, 100, epd.BLACK, fill=False)
    epd.draw_circle(400, 240, 50, epd.RED, fill=True)
    epd.draw_line(0, 0, 799, 479, epd.BLACK)
    epd.draw_line(0, 479, 799, 0, epd.RED)
    epd.display()
    utime.sleep(3)
    
    # 測試 4: 清除畫面並進入睡眠
    print("\n4. 清除畫面並進入睡眠...")
    epd.clear("white")
    epd.sleep()
    
    print("\n=== 測試完成 ===")