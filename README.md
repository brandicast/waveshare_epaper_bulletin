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

## 📂 專案目錄結構 (Project Tree)

```text
.
├── epaper_bulletin.py      # 主程式入口 (Pico)
├── conf/                   # 配置文件 (Pico)
│   └── mqtt.conf           # MQTT 伺服器設定
├── core/                   # 專案核心邏輯 (Pico)
│   ├── bmp_display.py      # 顯示處理器
│   ├── mqtt_handler.py     # MQTT 訊息處理
│   └── wifi_manager.py     # WiFi 連線管理
├── lib/                    # 硬體驅動與第三方套件 (Pico)
│   ├── epaper_7_5_b.py     # 7.5吋電子紙驅動 (黑/白/紅)
│   ├── wifi_provision.py   # 配網功能邏輯
│   └── umqtt/              # MicroPython MQTT 套件
├── resources/              # 靜態資源檔案 (Pico)
│   ├── welcome.bmp         # 歡迎畫面
│   ├── home.bmp            # 待機畫面
│   ├── starting.bmp        # WiFi 啟動畫面
│   ├── provisioning.bmp    # 配網引導畫面
│   ├── wifi_connected.bmp  # 連線成功畫面
│   └── www/                # 配網網頁模板
│       └── index.html      # RWD 配網網頁
├── tools/                  # 電腦端輔助工具 (Host)
│   ├── bmp_gen.py          # 3色圖片產生器 (支援中文)
│   ├── mqtt_pub.py         # MQTT 圖片發送工具
│   ├── test_3color.bmp     # 三色測試範例圖
│   └── jf-openhuninn-2.1.ttf # 內建粉圓體字型
├── docs/                   # 專案文件與日誌
│   ├── execution_log_20260514.md  # 開發執行日誌
│   ├── lesson_learned_20260514.md # 經驗總結與檢討
│   └── reference/          # 技術參考文件 (規格書與原始碼)
├── todo.md                 # 待辦事項與未來功能
└── README.md
```

## 📤 Pico 上傳清單 (Pico Deployment)

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

### MQTT 測試
MQTT 主題前綴由 `mqtt_topic` 定義。系統會訂閱：
- `<mqtt_topic>/bmp`：接收 BMP 圖片
- `<mqtt_topic>/binary`：接收二進位圖像

可使用 `tools/mqtt_pub.py` 測試：
```bash
python3 tools/mqtt_pub.py tools/test_3color.bmp 192.168.0.96 epaper/bulletin
python3 tools/mqtt_pub.py ./path/to/image.bin 192.168.0.96 epaper/bulletin
```

### WiFi 配置
首次啟動或 WiFi 設定失敗時會自動進入 AP 模式（SSID: `Pico-Setup`）。連線後訪問 `192.168.4.1` 即可進行配網。
WiFi 憑證與收到的 MQTT 圖片檔案都會保存在 `./user_config/` 目錄中。
在系統運行中，長按 Middle Key（GPIO 2）5 秒可清除 `./user_config/`，讓系統回到乾淨狀態並進入 AP 模式。

### 硬體按鍵
- Top Key: GPIO 3
- Middle Key: GPIO 2
- Bottom Key: RUN（硬體重置鍵，無法透過軟體定義）

## 📝 注意事項

- **記憶體限制**：由於 7.5 吋螢幕緩衝區較大，請避免同時開啟過多網路服務。
- **三色渲染**：處理 24-bit BMP 時，系統會自動辨識紅色區域並進行映射。

---
**Designed by BreadSoft**
