#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

from aqt.qt import *
from aqt.editor import *

class AnkingEditor(Editor):
    def __init__(self, mw, widget, parentWindow, addMode=False):
        Editor.__init__(self, mw, widget, parentWindow, addMode)
