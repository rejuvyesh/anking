#!/usr/bin/env python3
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

# send card to anki
TCP_IP   = '127.0.0.1'
TCP_PORT = 49666

import json
import socket

def sendToAnki(cmd, data):
    while True: # FIXME use timeout
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((TCP_IP, TCP_PORT))
            msg = {
                "cmd": cmd,
                "data": data,
            }
            s.send(json.dumps(msg))
            # wait for confirmation
            status = s.recv(1024)
            if status != "OK":
                raise Exception("Sending command to Anki failed somehow: %s" % status)
            s.close()
            return
        except:
            # anki probably just hasn't finished loading, so try again later
            time.sleep(1)