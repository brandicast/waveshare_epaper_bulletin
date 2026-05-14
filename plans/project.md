# Project Background

This project is based on Raspberry Pi Pico W.  

## Development Environment

- The development envrionment is in WSL of windows.  The configuration of sharing USB device from Windows to WSL is ready. Pico is being connected via USB on /dev/ttyACM0. 

- Working folder is under /home/brandicast/github/experiment/raspberry_pi/pico/prj/epaper_bulletin.  Meaning all the files created by you should be under this folder.

- Read only those specify in "Reference to waveshare epaper devices" and ignore other folders.

## Rules for implemnentation

- Use MicroPython as coding language.  If it is necessary to use native language such as C, please ask.

- Use virtual environment called venv and install necessary packages under.

- Put all source code under ./src/

- Put all planning document under ./plans/

- Put all resource files, including images, display text under ./resources/

- Put epaper (waveshare) display into deepsleep mode whenever the screen has been updated.

- mqtt configuration is store under ./conf/mqtt.conf as key=value format

- try catch any exception around any IO actions to avoid system crash.  

- try catch error of the whole application if run out of memory or system resoruces.

## Communication with Pico

- Use rshell to upload code.  If to use any other tools, please ask.
- Don't rename the main app to main.py.  try to use repl, import app_name instead. 

## Logs

- Keep the planning and implementation sugggestion and plans under .\plans\.  Filename with a date and version id.

## Reference to waveshare epaper devices

- Refer to /home/brandicast/github/experiment/raspberry_pi/pico/README.md for basic knowldge about Pico if necessary.
- refer to /home/brandicast/github/experiment/raspberry_pi/pico/prj/epaper/Summary.md for the specification of the epaper display.
- use /home/brandicast/github/experiment/raspberry_pi/pico/prj/epaper_bulletin/src/lib/epaper_7_5_b.py as epaper display library for this project. If it's not library ready, modify and make it ready for this application.
- use /home/brandicast/github/experiment/raspberry_pi/pico/prj/epaper_bulletin/src/lib/wifi_provision.py as wifi provisioning library for this project.  If it's not library ready, modify and make it ready for this application.
- use library umqtt.robust as MQTTClient.  Refer to /home/brandicast/github/experiment/raspberry_pi/pico/prj/gate_opener/open_gate.py as implementation reference if necessary.

## Implemntation Tasks

- On boot up, check if there's wifi configuration.  If yes, try to connect to WiFi with the configuration.  Max retry 3 times when connection failed.  If there's no wifi configuration or after retry and still unable to connect to wifi, start wifi provision process using the library under lib/wifi_provision.py.
- Once WiFi is connected, 
    - Check if there's latest.bmp under ./resource/lastest.bin.  If yes, display it.  If not, display ./resources/home.bmp
    - Start mqtt client as Subscriber using mqtt configuration stores under ./conf/mqtt.conf 
    - If mqtt client is connected, it is expecting to receive a binary buffer.  Once it is received, check if the binary is too large to display.  If yes, ignore it, and if not, store the binary locally as lastest.bin under ./resources/
