# DiscordMatrix

Displays your Discord connection status on a MAX7219 LED Matrix, connected via Arduino.

# Running the source code

To install the dependencies, run `pip install -r requirements.txt`. 

To start the application, simply run `python discord_matrix.pyw` from the command line.

The default pinout is:
* dataIn = 2
* load = 4
* clock = 3

These values can be changed in your `config.ini` which appears after running the code once. 

# Current Legend

| Status | Icon |
| ------ | :----: |
| Disconnected | <img src="./images/disconnected.png" alt="disconnected" width="200px" height="200px"/> |
| Connected | <img src="./images/connected.png" alt="connected" width="200px" height="200px"/> |
| Muted |  <img src="./images/muted.png" alt="muted" width="200px" height="200px"/> |
