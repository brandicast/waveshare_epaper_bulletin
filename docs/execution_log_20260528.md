# 執行日誌 (Execution Log - 2026-05-28)

**目的**：Session 任務分析與修正紀錄
**執行人**：Antigravity AI
**日期**：2026-05-28

---

## 任務 1：讀取並理解 Lesson Learned

讀取了 `docs/lesson_learned_20260514.md`，共 13 條教訓。
以下是對本專案未來開發最關鍵的規則提醒：

| 規則 # | 核心教訓 | 確認狀態 |
|--------|---------|---------|
| #3 | 渲染前必須明確清除所有 buffer（imageblack.fill + imagered.fill） | ✅ 已修正（bmp_display.py 改用 fill()） |
| #6 | 三色電子紙絕對不能使用 fast mode | ✅ 主程式使用 mode="normal" |
| #7 | RAM 操作與物理刷新嚴格分離，僅呼叫一次 display() | ✅ 已修正（移除所有 clear() 呼叫） |
| #9 | 所有 _wait_until_idle() 必須有 timeout | ✅ epaper_7_5_b.py 中已加入 40 秒 timeout |
| #11 | MQTT 重連後必須重新 subscribe | ✅ connect() 每次都有完整的 subscribe 流程 |

---

## 任務 2：電子紙噪訊問題修正（已實作）

### 分析結果

對 `docs/reference/epaper/waveshare_epaper_display_spec.md` 和 `lib/epaper_7_5_b.py` 進行了比對分析。

**問題根源**：

1. **雙重物理刷新（最嚴重）**：
   - `core/bmp_display.py` 的 `display_file()` 呼叫 `wake_display()` 後立即呼叫 `epd.clear("white")`
   - `clear()` 底層是 `fill() + display()` → 觸發第一次物理刷新（全白畫面）
   - 接著繪圖完成後再呼叫 `display()` → 第二次物理刷新（真正的圖）
   - 同樣問題存在於 `draw_error()` 方法

2. **Buffer 未初始化**：MicroPython 的 `bytearray` 預設為零（0=黑），而電子紙預設背景應為白（1），第一次顯示前若未明確初始化，可能顯示全黑或亂點。

3. **wake_up() 後缺乏穩定等待**：從 deep sleep 喚醒後 DC-DC 電路升壓需要穩定時間。

### 修正內容

**修改檔案 1**：`core/bmp_display.py`
- `display_file()`：`epd.clear("white")` → `imageblack.fill(1)` + `imagered.fill(0)`
- `draw_error()`：同上

**修改檔案 2**：`lib/epaper_7_5_b.py`
- `__init__()`：在硬體初始化後明確呼叫 `imageblack.fill(1)` + `imagered.fill(0)`
- `wake_up()`：在 `init()` 完成後加入 `_delay_ms(200)` 穩定等待

---

## 任務 3：MQTT 重連後畫面未恢復問題修正

### 問題描述

在 `epaper_bulletin.py` 的 `main_loop()` 函式中，當 MQTT 斷線並重連成功後，畫面停留在「MQTT Connection Failed」錯誤畫面，沒有任何指令讓它回到正常等待畫面或最後收到的圖片。

### 修正內容

**修改檔案**：`epaper_bulletin.py`
**修改位置**：`main_loop()` 函式，MQTT 重連成功的分支

**修改前**：
```python
if mqtt_handler.connect():
    print("[Main] MQTT reconnected")
    error_count = 0
```

**修改後**：
```python
if mqtt_handler.connect():
    print("[Main] MQTT reconnected")
    error_count = 0
    # Restore the screen to last received image or home screen
    print("[Main] Restoring display after MQTT reconnect...")
    try:
        display_received_or_home(display_handler)
    except Exception as e:
        print(f"[Main] WARNING: Failed to restore display after reconnect: {e}")
```

### 影響範圍

- 僅影響 MQTT 重連成功後的畫面行為
- `display_received_or_home()` 函式已在主程式最頂層定義，可直接呼叫
- 使用 try/except 包裝，不影響其他功能的正常運作
- MQTT 重連失敗時畫面保持不變（原有邏輯不受影響）

### 測試建議

1. 啟動系統並等待 MQTT 連線成功，顯示等待/首頁畫面
2. 關閉或中斷 MQTT Broker 連線
3. 確認螢幕顯示錯誤畫面（由原本邏輯觸發）
4. 恢復 MQTT Broker 連線
5. 等待約 5 秒（reconnect_interval_ms），確認系統重連並自動回到正常畫面

---

*紀錄人*：Antigravity AI
