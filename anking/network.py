#!/usr/bin/env python3
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

# send card to anki
TCP_IP   = '127.0.0.1'
TCP_PORT = 49666
KEY      = "anki"

import json
import socket
import subprocess, sys, time

from aqt.qt import *

def sendToAnki(cmd, data, timeout=1, retries=10):
    # make sure Anki is actually running
    shmem = QSharedMemory(KEY)
    alreadyRunning = shmem.attach()
    if not alreadyRunning:
        print "starting anki..."
        subprocess.Popen("anki")

    # try to connect; may take a bit if Anki is just starting
    while retries >= 0:
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
            return True
        except:
            # anki probably just hasn't finished loading, so try again later
            retries -= 1
            time.sleep(timeout)
            
    return False