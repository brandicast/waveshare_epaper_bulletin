# BreadSoft E-Paper Bulletin Board

這是一個基於 Raspberry Pi Pico W 的電子紙佈告欄系統。它能夠透過 MQTT 協議接收遠端圖片，並顯示在 Waveshare 7.5 吋三色電子紙螢幕上。

## 🚀 核心特性

- **記憶體優化串流**：採用分段 (Chunk-by-chunk) 檔案串流技術接收 MQTT 訊息，並在 24-bit BMP 渲染中加入逐行記憶體回收。
- **三色顯示支援**：支援黑、白、紅三色顯示。
    - **1-bit BMP**：極速顯示（黑白）。
    - **24-bit BMP**：高品質顯示（黑白紅）。
    - **8-bit 索引色 (計畫中)**：平衡速度與顏色的最佳選擇。
- **動態配網 (WiFi Provisioning)**：具備美觀且響應式 (RWD) 的 Web 設定介面，支援密碼顯示/隱藏切換。
- **自動化維護**：主迴圈具備計數器溢位保護與自動錯誤重連機制。

## 🛠️ 硬體需求

- **微控制器**：Raspberry Pi Pico W
- **顯示器**：Waveshare 7.5inch e-Paper (B) V3 (三色：黑/白/紅)
- **解析度**：800 × 480 像素

## 📂 Pico 上傳清單 (Pico Directory Structure)

要讓系統正常運作，您必須將以下目錄與檔案上傳至 Pico：

- `epaper_bulletin.py` (主程式入口)
- `core/` (包含 `bmp_display.py`, `mqtt_handler.py`, `wifi_manager.py`)
- `lib/` (包含 `epaper_7_5_b.py`, `wifi_provision.py`)
- `conf/` (包含 `mqtt.conf`)
- `resources/` (包含 `welcome.bmp`, `home.bmp`, `starting.bmp`, `provisioning.bmp`, `wifi_connected.bmp`)
- `resources/www/` (包含 `index.html` - 配網介面)

*注意：`wifi_config/` 目錄會由系統自動建立，請勿手動上傳包含敏感資訊的設定檔。*

## 🛠️ 電腦端工具使用 (Tools)

建議在電腦上安裝以下套件：
```bash
pip install Pillow paho-mqtt
```
*若無 Pillow，部分工具改由系統 ffmpeg 代勞。*

### 1. 產生自定義 BMP (`tools/bmp_gen.py`)
自動產生適合 800x480 的 3 色 BMP 檔案：
```bash
# 產生黑白文字
python3 tools/bmp_gen.py "歡迎來到 BreadSoft" [輸出路徑]

# 產生包含紅色警告的文字
python3 tools/bmp_gen.py "系統狀態正常" --red "但請注意電源" [輸出路徑]
```

### 2. 傳送圖片到電子紙 (`tools/mqtt_pub.py`)
將圖片透過 MQTT 傳送到 Pico W，內建 10 秒發送逾時保護：
```bash
python3 tools/mqtt_pub.py tools/test_3color.bmp
```

## ⚙️ 配置說明

### MQTT 配置 (`conf/mqtt.conf`)
```ini
mqtt_server=192.168.0.96
mqtt_port=1883
mqtt_topic=epaper/bulletin
```

### WiFi 配置
首次啟動或長按 GPIO 14 (5秒) 會進入 AP 模式（SSID: `Pico-Setup`）。連線後訪問 `192.168.4.1` 即可進行配網。

## 📝 注意事項

- **記憶體限制**：由於 7.5 吋螢幕緩衝區較大，請避免同時開啟過多網路服務。
- **三色渲染**：處理 24-bit BMP 時，系統會自動辨識紅色區域並進行映射。

---
**Designed by BreadSoft**
