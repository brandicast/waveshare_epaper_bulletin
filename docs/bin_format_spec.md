# Raw 2-bit Binary (.bin) 影像格式規範

本文件定義了專為 **Raspberry Pi Pico W** 與 **Waveshare 7.5inch e-Paper (B) 三色電子紙** 開發的 `.bin` 輕量化影像格式規範。

## 1. 為什麼需要這個格式？（設計背景）

在 MicroPython 環境下處理高解析度 (800x480) 圖片時，我們面臨了兩大物理限制：
1. **Flash 容量極限**：Pico W 在載入 MicroPython 韌體後，內建的 Flash 檔案系統僅剩餘約 **303 KB**。若使用標準 8-bit Indexed BMP (376 KB) 或 24-bit RGB BMP (1.1 MB)，會直接導致「磁碟已滿 (Disk Full)」而無法上傳。
2. **RAM 記憶體碎片化 (ENOMEM)**：Pico W 僅有約 100~140 KB 的可用堆積 (Heap)。若使用 Python 迴圈逐一像素讀取解析 BMP，除了速度極慢（高達 40 秒），不斷建立的變數更會造成嚴重的記憶體碎片化，最終導致 `Memory Allocation Failed (ENOMEM)` 崩潰。

**Raw 2-bit Binary (.bin)** 徹底解決了上述問題：
- **極致壓縮**：檔案大小固定為 **96,000 bytes (93.75 KB)**，完美適應 303 KB 的 Flash 空間。
- **零分配 (Zero Allocation)**：可以直接將二進位資料映射 (Map) 寫入硬體驅動的 Buffer 記憶體中，讀取過程 **0 bytes 額外 RAM 消耗**。
- **極速載入**：無需任何迴圈運算，載入時間從 40 秒暴降至 **18 毫秒**。

---

## 2. 檔案結構規範 (File Structure)

這個 `.bin` 檔案**沒有任何 Header**，完全由純像素資料 (Raw Pixels) 組成，大小為精準的 `96,000 Bytes`。

它被嚴格切分為兩半，以對應電子紙的實體雙緩衝區 (Dual FrameBuffers)：

| 區塊名稱 | 起始偏移 (Offset) | 大小 (Size) | 內容說明 |
| :--- | :--- | :--- | :--- |
| **Black/White Buffer** | `0x00000` (0) | 48,000 bytes | 控制黑白像素的顯示狀態。 |
| **Red Buffer** | `0x0BB80` (48000) | 48,000 bytes | 控制紅色像素的顯示狀態。 |

*註: `800 pixels * 480 pixels / 8 bits_per_byte = 48,000 bytes`*

---

## 3. 像素與位元編碼邏輯 (Bit Encoding Logic)

此格式的位元排列採用 **Horizontal MSB-first (MONO_HLSB)** 佈局：
- 每個 Byte 代表 8 個水平像素。
- Byte 中的 **最高有效位 (Bit 7, MSB)** 代表最左邊的第 1 個像素。
- Byte 中的 **最低有效位 (Bit 0, LSB)** 代表最右邊的第 8 個像素。

### 顏色對應真值表 (Truth Table)

基於 Waveshare 驅動的設計，緩衝區使用的是**特定的高低電平邏輯**：

| 螢幕想顯示的顏色 | Black/White Buffer 的位元值 | Red Buffer 的位元值 |
| :---: | :---: | :---: |
| **黑色 (Black)** | `0` | `0` |
| **白色 (White)** | `1` | `0` |
| **紅色 (Red)** | `1` | `1` |

*(註：若 Black 設為 `0` 且 Red 設為 `1`，在實體面板上會因電壓覆蓋而顯示為紅色或深紅混色，在此規範中視為未定義/避免使用)*

---

## 4. 如何生成與讀取此格式？

### 電腦端生成 (Generation)
您可以使用專案提供的 `tools/bmp_gen.py` 生成此格式。核心演算法如下：
```python
# 遍歷每個像素 (x, y)
pixel_idx = y * width + x
byte_idx = pixel_idx // 8
bit_pos = 7 - (pixel_idx % 8) # MSB-first

is_black = (r < 128 and g < 128 and b < 128)
is_red = (r > g + 40 and r > b + 40 and r > 100)

if not is_black:
    bw_data[byte_idx] |= (1 << bit_pos) # 非黑即白(1)
if is_red:
    red_data[byte_idx] |= (1 << bit_pos) # 紅色設(1)
```

### 微控制器端讀取 (MicroPython Decoding)
讀取時**禁止使用 `read()` 或逐像素迴圈**，必須使用 `readinto()` 進行硬體緩衝區直寫：
```python
# 假設 epd 為已初始化的 EPD_7in5_B 物件
with open("welcome.bin", 'rb') as f:
    # 讀取前 48,000 bytes 直接覆蓋黑白畫布
    f.readinto(epd.buffer_black)
    
    # 讀取後 48,000 bytes 直接覆蓋紅色畫布
    f.readinto(epd.buffer_red)

# 送出實體刷新指令
epd.display()
```
