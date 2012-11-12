#!/usr/bin/env python3
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

# send card to anki
TCP_IP   = '127.0.0.1'
TCP_PORT = 49666
KEY      = "anki"

import json
import subprocess, sys, time

from aqt.qt import *
from PyQt4 import QtNetwork

def sendToAnki(cmd, data=None, timeout=1, retries=10):
    # make sure Anki is actually running
    shmem = QSharedMemory(KEY)
    alreadyRunning = shmem.attach()
    if not alreadyRunning:
        print "starting anki..."
        subprocess.Popen("anki")

    # try to connect; may take a bit if Anki is just starting
    while retries >= 0:
        try:
            s = QtNetwork.QTcpSocket()
            s.connectToHost(TCP_IP, TCP_PORT)
            s.waitForConnected(timeout*1000)
            msg = {
                "cmd": cmd,
                "data": data,
            }
            # write data
            s.write(json.dumps(msg))
            s.flush()
            
            # get return data
            s.waitForReadyRead(timeout*1000)
            ret = json.loads(str(s.readAll()))

            # done
            s.close()
            return ret
        except Exception as e:
            # anki probably just hasn't finished loading, so try again later
            # print e
            retries -= 1
            time.sleep(timeout)
    return None