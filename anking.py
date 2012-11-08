#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

import os, re, sys, __builtin__, time
import subprocess

from mock import MagicMock

if __name__ == "__main__":
    # use local anki libs
    base = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, os.path.join(base, "libanki"))
    sys.path.insert(0, os.path.join(base, "ankiqt"))

    # load anki libs
    import anki
    from anki.hooks import runHook
    from aqt.qt import *
    from aqt import AnkiApp

    # fake gettext because fuck it
    __builtin__.__dict__['_'] = lambda s: s
    
    # load local libs
    import anking.addcards

    # load anki collection for more convenient reads
    # FIXME read from profile
    cwd = os.getcwd()
    col = anki.storage.Collection("/home/amon/spoiler/anki/muflax/collection.anki2", lock=False)
    # os.chdir(cwd) # go back to old path, not *.media

    # check if anki is already running and if not, start it
    anki_app = AnkiApp(sys.argv)
    if not anki_app.alreadyRunning:
        print "starting anki..."
        subprocess.Popen("anki")

    # our app
    app = QApplication(sys.argv)

    # fake objects for anki parts so we can just steal its code
    mw = MagicMock()
    mw.col = col
    mw.app = app
    def reset():
        # replaces mw.reset()
        runHook("reset")
    mw.reset = reset

    # start app
    form = anking.addcards.AddCards(mw)
    app.exec_()