# boot.py - 最簡測試版
import time
import json

# boot.py 最開頭
import machine

import time

print("Auto-executing boot.py!")

from gpio import led
led.value(1)



# 記錄重啟原因
reset_cause = machine.reset_cause()
with open('reset_log.txt', 'w') as f:
    f.write(f"{time.ticks_ms()}: Reset cause = {reset_cause}\n")

# 記錄開機計數
try:
    with open('boot_counter.json', 'r') as f:
        data = json.load(f)
        count = data.get('boot_count', 0) + 1
except:
    count = 1

with open('boot_counter.json', 'w') as f:
    json.dump({'boot_count': count}, f)

print(f"Boot count: {count}")
time.sleep(1)  # 短暫延遲，不要 10 秒那麼長

import epaper_bulletin as epaper

epaper.main() 

