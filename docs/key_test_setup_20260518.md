# 執行日誌：硬體按鍵 (Key1/Key2/Key3) 獨立測試與驗證 (2026-05-18)

## 執行目的
為驗證 Raspberry Pi Pico W 佈告欄系統與實體按鍵 (Key1, Key2, Key3) 之間的 GPIO 硬體映射是否正確，我們在專案下建立了一個獨立的測試資料夾與測試程式，以便快速在實體裝置上運行並驗證。

---

## 分析與實作過程

### 1. 實際硬體按鍵規格對照
經實體裝置運行測試與驗證，這款 Waveshare 7.5inch e-Paper 驅動板上的按鍵實體硬體映射如下：
* **Top Key (GPIO 3)**：可程式化按鍵 1，預計用於手動觸發 MQTT 訊息檢查 / 強制畫面重新整理。
* **Middle Key (GPIO 2)**：可程式化按鍵 2，預計用於切換顯示資訊頁面（例如：天氣 -> 股市 -> 佈告欄）或進入低功耗睡眠。
* **Bottom Key (RUN / Reset)**：硬體重置按鈕，按下會使 Pico W 重新啟動且斷開 USB 連線，此鍵**無法**透過軟體或 Python 程式自定義功能。

### 2. 測試程式設計原理 (`test/test_keys.py`)
我們在專案根目錄下建立了 [test/test_keys.py](file:///home/brandicast/github/waveshare_epaper_bulletin/test/test_keys.py) 獨立指令碼，設計要點如下：

1. **模組路徑標準化**：
   由於測試檔位於 `test/` 子資料夾，我們在引導段加入了 `sys.path.append("")` 與 `sys.path.append("/")`，確保無論是用 Thonny 單獨開啟或是透過 CLI 啟動，均能正確 import [lib/epaper_7_5_b.py](file:///home/brandicast/github/waveshare_epaper_bulletin/lib/epaper_7_5_b.py) 驅動。
2. **硬體中斷與防彈消抖 (Software Debounce)**：
   * 採用內部拉高電阻（`Pin.PULL_UP`），對應 active-low (按下時 value 為 0) 的按鍵電路設計。
   * 迴圈輪詢中加入了 20ms 的消抖延時確認，避免電磁雜訊造成重覆觸發（Double-click）。
   * 觸發後使用 `while pin.value() == 0: sleep` 阻斷，直到使用者釋放按鈕，才進行下一輪掃描，防止畫面重覆刷新。
3. **螢幕快速刷新優化 ("fast" mode)**：
   * 7.5 吋三色電子紙在標準模式下的全刷新需耗時 15 秒以上。為了提供更好的互動式測試體驗，我們將 `EPD_7in5_B` 的初始化模式設為 `fast`（快速模式，約 2-3 秒完成刷新）。
   * 按下按鈕時，螢幕會立即喚醒，將背景清除為純白，並以**大字體與紅色高亮**標示被按下的 Key 名稱、GPIO 針腳以及未來預定功能。
4. **雙重反饋機制**：
   * **終端機輸出 (Serial Console)**：按下按鈕時，立即透過 Serial (USB 虛擬串列埠) 印出按鍵狀態，提供毫秒級的即時回饋。
   * **電子紙顯示 (E-Paper Display)**：將詳細資訊畫在 buffer 上並輸出至螢幕。
5. **資源安全釋放 (Resource Cleanup)**：
   * 使用 `try...finally` 結構，當使用者透過 `Ctrl+C` 結束測試時，程式會自動喚醒螢幕、執行 `clear("white")` 清除畫面殘影，並將電子紙重新送入 `sleep()` 深度睡眠模式（~15μA），防止螢幕長時間供電受損。

---

## 測試程式位置與執行說明

* **程式路徑**：[test/test_keys.py](file:///home/brandicast/github/waveshare_epaper_bulletin/test/test_keys.py)

### 執行步驟：
1. **上傳檔案**：請將 [test/test_keys.py](file:///home/brandicast/github/waveshare_epaper_bulletin/test/test_keys.py) 上傳至 Pico W 的根目錄 `/test/test_keys.py` 下。
2. **運行測試**：
   * **透過 Thonny IDE**：開啟 `/test/test_keys.py` 並按下 `F5` 鍵運行。
   * **透過命令列 (CLI)**：
     ```bash
     mpremote run test/test_keys.py
     ```
3. **操作按鍵**：
   * 螢幕初始化後會顯示「歡迎測試與按鍵說明」畫面。
   * 按下 Pico 擴充板上的 Key1、Key2 或 Key3，觀察電腦 Terminal 輸出的 Log，並等待 3 秒看電子紙上的動態畫面變更。
   * 測試完成後，在 Terminal 按下 `Ctrl+C` 可安全退出並清空螢幕。

---

**紀錄人**: Antigravity AI  
**日期**: 2026-05-18  
