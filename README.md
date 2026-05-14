# BreadSoft E-Paper Bulletin Board

這是一個基於 Raspberry Pi Pico W 的電子紙佈告欄系統。它能夠透過 MQTT 協議接收遠端圖片，並顯示在 Waveshare 7.5 吋三色電子紙螢幕上。

## 🚀 核心特性

- **記憶體優化串流**：採用分段 (Chunk-by-chunk) 檔案串流技術接收 MQTT 訊息，即使在只有 264KB RAM 的 Pico W 上也能穩定處理 800x480 的高品質圖片。
- **雙主題支援**：
    - `{topic}/bmp`：支援標準 BMP 格式圖片（自動偵測與置中顯示）。
    - `{topic}/binary`：支援原始 1-bit 像素資料（極速顯示）。
- **快速渲染引擎**：優化後的 BMP 渲染邏輯，能自動跳過白色像素，大幅縮短顯示等待時間。
- **動態配網 (WiFi Provisioning)**：內建 Web 門戶，方便在不同環境下配置 WiFi 連線。
- **電源管理**：支援 Deep Sleep 深度睡眠模式，配合硬體重置喚醒，適合電池供電場景。
- **品牌化設計**：內建 BreadSoft 專屬歡迎畫面與待機畫面。

## 🛠️ 硬體需求

- **微控制器**：Raspberry Pi Pico W
- **顯示器**：Waveshare 7.5inch e-Paper (B) V3 (三色：黑/白/紅)
- **解析度**：800 × 480 像素

## 📂 目錄結構

```text
.
├── epaper_bulletin.py    # 主程式入口
├── bmp_display.py        # 顯示邏輯與圖片處理
├── mqtt_handler.py       # MQTT 連線與訊息處理
├── wifi_manager.py       # WiFi 連線管理
├── lib/
│   ├── epaper_7_5_b.py   # Waveshare 螢幕驅動程式 (已優化)
│   └── wifi_provision.py # 網頁配網邏輯
├── conf/
│   └── mqtt.conf         # MQTT 伺服器配置
├── resources/
│   ├── wifi_connected.bmp# 啟動歡迎圖
│   └── home.bmp          # 系統待機圖
└── umqtt/                # MQTT 核心庫 (已修改支援串流)
```

## ⚙️ 配置說明

### MQTT 配置 (`conf/mqtt.conf`)
編輯該檔案以符合您的伺服器環境：
```ini
mqtt_server=192.168.0.96
mqtt_port=1883
mqtt_topic=epaper/bulletin
```

### WiFi 配置
首次啟動時，若找不到存儲的 WiFi 資訊，Pico W 會進入 AP 模式（名稱通常為 `Pico-Setup`）。連線後打開瀏覽器訪問 `192.168.4.1` 即可進行配網。

## 📤 如何傳送圖片

您可以透過任何 MQTT 客戶端傳送圖片：

1. **傳送標準 BMP**：
   - Topic: `epaper/bulletin/bmp`
   - Payload: BMP 檔案的二進位內容。

2. **傳送原始像素資料**：
   - Topic: `epaper/bulletin/binary`
   - Payload: 48,000 bytes 的原始像素資料 (1-bit)。

## 📝 注意事項

- **螢幕雜點**：系統從 Deep Sleep 喚醒時會自動執行硬體重置，確保畫面不會出現隨機雜訊。
- **渲染時間**：優化後的 1-bit BMP 顯示時間約為 15-20 秒，彩色 24-bit BMP 則較慢。

---
**Designed by BreadSoft**
