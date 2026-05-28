# Background

This document is try to define the spec of bulletin publisher as a standalone app and provide a library for outsider to use.  

# Location

This spec defines a standalone app in the "publisher" directory and will not affect or coupling with any other part of the project.

# Spec

- This app contains a main as an entry point, and a class "BulletinPublisher" as a library for outsider to use.

- The constructor could take parameters as MQTT server settings (host, port, user, password, etc).  If provided, it stores those parameters under ./conf/mqtt.conf.  If not provided, throw excepton on publish function call.  However, the image generation could still work as a standalone utility.

- This app takes various input, including a content which can be a string or a path to a image file path.  if string, convert to image using fonts in ./fonts. 

- The output would be a binary buffer ready to be sent to waveshare epaper display by following the spec defined in docs/bin_format_spec.md. 

- The output should be store under publisher/output/.  Filename can reuse the origin input filename.  Just append .bin

- When generate the output bin file, generate another bmp file 

- When function publish is called, it publishes the bin file to the MQTT server with topic defined in ./conf/mqtt.conf.  If no configuration is found, throw exception.

- Try to make this class a threadsafe class.  Put the thread synchonization logic in constructor. Design as either like singleton or use threading lock mechanism.



