# DiscordMatrix

Displays your Discord connection status on a MAX7219 LED Matrix, connected via Arduino.

# Running the source code

To install the dependencies, run `pip install -r requirements.txt`. 

This program runs at 125000 baud, instead of PyFirmata's default 57600 bits/s. When uploading the FirmataStandard sketch
to your Arduino, change line 774 to `Firmata.begin(125000);`.

To start the application, simply run `python discord_matrix.pyw` from the command line.

The default pinout is:
* dataIn = 2
* load = 4
* clock = 3

These values can be changed in your `config.ini` which appears after running the code once. 

# Current Legend

| Status | Icon |
| ------ | :----: |
| Disconnected | 12-Hour Clock Marquee |
| Connected | <img src="./images/connected.png" alt="connected" width="200px" height="200px"/> |
| Muted |  <img src="./images/muted.png" alt="muted" width="200px" height="200px"/> |
| Deafened | <img src="./images/deafened.png" alt="deafened" width="200px" height="200px"/> |
