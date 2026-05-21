# 執行日誌 (Execution Log - 2026-05-21)

本執行日誌記錄了修復 MQTT 大檔案接收上限、重連訂閱回復機制以及 E-Paper 雙通道 Raw 二進位影像載入的修改過程。

---

## 1. 修改內容概述

針對 7.5 吋三色 E-Paper 佈告欄系統，完成了以下三項核心修復與功能增強：

| 修改目標 | 涉及檔案 | 變更說明 |
| :--- | :--- | :--- |
| **放寬 MQTT Payload 上限** | [lib/umqtt/simple.py](file:///home/brandicast/github/waveshare_epaper_bulletin/lib/umqtt/simple.py) | 將限制由原先的 `65535` 放寬至 `102400` 位元組，以相容 96,000 位元組的 3-color raw binary 影像檔。 |
| **自動還原訂閱主題** | [lib/umqtt/robust.py](file:///home/brandicast/github/waveshare_epaper_bulletin/lib/umqtt/robust.py) | 1. 覆寫 `subscribe()`，將訂閱主題與 QoS 記錄至實例變數 `self.subscriptions`。<br>2. 修改 `reconnect()`，在每次 Socket 重新連線成功後，自動巡覽並還原所有活躍的訂閱主題。 |
| **支援雙通道 Raw Binary 載入** | [core/bmp_display.py](file:///home/brandicast/github/waveshare_epaper_bulletin/core/bmp_display.py) | 修改 `_load_and_display_raw()`，偵測檔案大小是否達兩倍以上，若是，則將後半段 48,000 位元組讀入紅色緩衝區 `buffer_red`，否則清除紅色通道。 |

---

## 2. 詳細修改比對 (Diffs)

### A. MQTT 接收大小放寬 (`lib/umqtt/simple.py`)
```diff
@@ -210,3 +210,3 @@
         if sz < 0:
             print("[umqtt] ERROR: Invalid message size: {}".format(sz))
             raise OSError(-1) # Connection corrupted
-        if sz > 65535: # Arbitrary limit for Pico safety, adjust if needed
+        if sz > 102400: # Allow up to 100KB for 3-color raw binary files (96,000 bytes)
             print("[umqtt] ERROR: Message too large: {}".format(sz))
             raise OSError(-1)
```

### B. 自動重新訂閱 (`lib/umqtt/robust.py`)
```diff
@@ -20,7 +20,11 @@
     def reconnect(self):
         i = 0
         while 1:
             try:
-                return super().connect(False)
+                res = super().connect(False)
+                if hasattr(self, 'subscriptions'):
+                    for topic, qos in self.subscriptions:
+                        super().subscribe(topic, qos)
+                return res
             except OSError as e:
                 self.log(True, e)
                 i += 1
                 self.delay(i)

+    def subscribe(self, topic, qos=0):
+        if not hasattr(self, 'subscriptions'):
+            self.subscriptions = []
+        sub = (topic, qos)
+        if sub not in self.subscriptions:
+            self.subscriptions.append(sub)
+        return super().subscribe(topic, qos)
```

### C. 支援雙通道 Raw Binary 載入 (`core/bmp_display.py`)
```diff
@@ -116,11 +116,13 @@
     def _load_and_display_raw(self, filepath):
         """Load and display raw pixel data file using memory-efficient methods."""
         gc.collect() # Free up memory before allocation
         try:
+            # Check file size to determine if we have a red channel
+            file_size = os.stat(filepath)[6]
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
                 
-                # Ensure red buffer is cleared (0) without re-allocating
-                # Using a loop is slower but memory-safe. 
-                # Better: self.epd.imagered.fill(0) if imagered is available
-                if hasattr(self.epd, 'imagered'):
-                    self.epd.imagered.fill(0)
-                else:
-                    for i in range(len(self.epd.buffer_red)):
-                        self.epd.buffer_red[i] = 0
+                # If the file contains a red channel (size >= 96KB)
+                if file_size >= self.expected_size * 2:
+                    print("[Display] Reading red channel...")
+                    red_bytes_read = f.readinto(self.epd.buffer_red)
+                    print("[Display] Read {} bytes into red buffer (expected {})".format(red_bytes_read, self.expected_size))
+                else:
+                    # Ensure red buffer is cleared (0) without re-allocating
+                    if hasattr(self.epd, 'imagered'):
+                        self.epd.imagered.fill(0)
+                    else:
+                        for i in range(len(self.epd.buffer_red)):
+                            self.epd.buffer_red[i] = 0
```

---

## 3. 測試與驗證計畫 (Verification Plan)

### A. MQTT 大容量傳輸測試
* **步驟**：啟動 MQTT 代理伺服器（Broker），執行 `epaper_bulletin.py`。
* **動作**：使用 `mqtt_pub.py` 發送一個大於 65,535 bytes（例如 96,000 bytes 的 `.bin` 檔案）至訂閱的主題下。
* **驗證目標**：
  1. Pico 應能順利接收，不觸發 `Message too large` 錯誤。
  2. 檢查 `temp_mqtt_msg.bin` 是否正確寫入且大小為 96,000 bytes。

### B. 連線中斷自動重新訂閱測試
* **步驟**：在大檔案傳輸途中或傳輸完成後，人為斷開/重啟 MQTT Broker，或在 Pico W 端模擬斷開 WiFi。
* **驗證目標**：
  1. `robust.py` 自動觸發 `reconnect()`。
  2. 重連成功後，Broker 應顯示該 Client 已重新 `subscribe` 到 `<topic_prefix>/bmp` 與 `<topic_prefix>/binary` 主題。
  3. 再次發送訊息時，Pico 應能繼續正常接收，無須手動重啟主程式。

### C. 雙通道三色顯示測試
* **步驟**：將含有黑白與紅色資料的 96KB 影像檔案寫入 Pico，呼叫 `display_file()` 顯示。
* **驗證目標**：畫面上黑白區域與紅色區域均能正確且清晰顯示，沒有紅色殘影或缺失。

---
**執行人員**: Antigravity AI  
**日期**: 2026-05-21
