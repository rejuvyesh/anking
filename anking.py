#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

import os, os.path, re, sys, __builtin__, subprocess, optparse, time
import json, yaml
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

    # fake gettext because fuck it
    __builtin__.__dict__['_'] = lambda s: s
    
    # load local libs
    import anking.addcards

    # options
    parser = optparse.OptionParser()
    parser.usage = "%prog [OPTIONS]"

    parser.add_option("-d", "--deck",    help="start with deck")
    parser.add_option("-m", "--model",   help="start with model")

    opts, args = parser.parse_args(sys.argv[1:])

    # our app
    app = QApplication(sys.argv)

    # load our preferences
    config = {
        # defaults
    }
    config_path = os.path.expanduser("~/.ankingrc")
    force_write = False
    if os.path.exists(config_path):
        config.update(yaml.load(file(config_path, 'r')))
    else:
        force_write = True
        
    # fake objects for anki parts so we can just steal its code
    mw = MagicMock()
    mw.app = app
    def reset():
        # replaces mw.reset()
        runHook("reset")
    mw.reset = reset

    # prepare app
    anking_form = anking.addcards.AddCards(mw, deck=opts.deck, model=opts.model)
    if "geom" in config:
        (w, h) = config["geom"]
        anking_form.resize(w, h)
    
    # start app
    anking_form.show()    
    app.exec_()

    # done, write our preferences if they changed
    size = [anking_form.size().width(), anking_form.size().height()]
    new_config = {
        "geom": size,
    }
    if config != new_config or force_write:
        yaml.dump(new_config, file(config_path, 'w+'))