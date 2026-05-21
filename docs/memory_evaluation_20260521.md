# MQTT 大檔案接收記憶體安全性評估報告 (Memory Safety Evaluation - 2026-05-21)

本報告評估將 MQTT 接收上限由 65,535 位元組放寬至 96,000 位元組（及以上）時，是否會導致 Raspberry Pi Pico W 出現 `ENOMEM` (記憶體不足) 錯誤。

---

## 1. 歷史限制：為何當初設定 65,535？

在標準的 MicroPython `umqtt.simple` 官方函式庫中，設定 `65535` 限制的主因如下：
1. **記憶體一次性分配**：官方 `umqtt` 原版在接收訊息時，會呼叫 `self.sock.read(sz)` 將整個 Payload 一次性讀入 RAM。
2. **Pico W 的 Heap 限制**：Pico W 的 MicroPython 可用 Heap 通常僅有約 190KB ~ 220KB。若一次性在記憶體中分配 96KB 的 `bytes` 物件，加上既有的驅動程式、WiFi 與系統開銷，極易導致記憶體碎片化並觸發 `ENOMEM` 崩潰。因此設定 `65535` 作為安全邊界是合理的防護措施。

---

## 2. 現狀分析：為何放寬至 96KB 在當前架構下是安全的？

目前我們的專案已經過深度優化，數據的「傳輸」與「顯示」皆採用了 **記憶體高效（Stream/Zero-Allocation）** 的設計：

### A. MQTT 接收階段：分段串流寫入快閃記憶體
在我們修改過的 `lib/umqtt/simple.py` 中，讀取 Payload 的邏輯如下：
```python
temp_file = 'temp_mqtt_msg.bin'
with open(temp_file, 'wb') as f:
    remaining = sz
    while remaining > 0:
        chunk_size = min(remaining, 1024)
        chunk = self.sock.read(chunk_size)
        f.write(chunk)
        remaining -= chunk_size
```
* **記憶體佔用**：此處將數據分成 **1,024 位元組 (1KB)** 的小區塊（Chunks）進行循環讀取並直接寫入 Flash。
* **評估**：不論檔案是 48KB 或是 96KB，在接收期間的 Heap 記憶體分配峰值**恆定為 ~1KB**。這徹底避免了因大檔案接收導致的記憶體溢出。

### B. 檔案更名與回呼階段：零記憶體拷貝
當接收完成後，回呼函式僅執行：
```python
os.rename(msg_file, dest)
```
此動作僅在 MicroPython 的檔案系統中修改 Metadata 節點，不涉及檔案內容的讀寫，記憶體開銷趨近於零。

### C. 畫面顯示階段：直接寫入預分配緩衝區
當主程式呼叫 `BMPDisplay._load_and_display_raw` 渲染時，我們將修改為：
```python
f.readinto(self.epd.buffer_black)
f.readinto(self.epd.buffer_red)
```
* **緩衝區狀態**：`buffer_black` 與 `buffer_red` 是在 EPD 驅動初始化時即**預先分配**的靜態 `bytearray`。
* **評估**：`readinto()` 是 MicroPython 的原生高效 API，它會直接將檔案內容寫入這兩個已存在的驅動緩衝區中，**不會在 Heap 重新分配新的記憶體**。

---

## 3. 評估結論

放寬 `lib/umqtt/simple.py` 的大小限制（例如放寬至 102,400 位元組），**完全不會**增加 Pico W 的 Heap 記憶體負擔。

此修改是**記憶體安全（Memory-Safe）**的，因為系統在傳輸時使用 1KB 串流緩衝，在載入時使用預分配的硬體緩衝區。這使我們能安全地接收與顯示 96KB 的三色二進位影像。
