# The Winfrey Editor

A real-time, multi-user terminal file editor written in Python 3

## Installation:
Run `pip3 install -r requirements.txt` to install all dependencies. Winfrey depends on:
* `ntplib`: Used to query NTP servers
* `urwid`: A GUI library used to create the editor itself
* `pyzmq`: A network abstraction library

## Usage:
Get help messages by running `python3 winfrey.py -h`

Host a file by running `python3 winfrey.py -s <FILE_PATH> <CONNECTION_PORT> <BROADCAST_PORT>`

Connect to a hosted file by running `python3 winfrey.py -c <HOST_IP> <CONNECTION_PORT> <BROADCAST_PORT>`

When editing, the following actions are allowed:
* Insert characters
* Delete/backspace
* Move cursor up/down/left/right with the arrow keys
* Exit by pressing ESC
