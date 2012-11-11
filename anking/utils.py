#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

from aqt.qt import *

def keyMatches(event, key):
    if not isinstance(key, QKeySequence):
        key = QKeySequence(key)
        
    # we are lazy, so we just check 1-key sequences
    if key.count() == 1:
        return (event.key() | int(event.modifiers())) == key[0]
    return False