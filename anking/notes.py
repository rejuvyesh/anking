#!/usr/bin/env python3
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

from anki.utils import fieldChecksum, splitFields
import re
from anking.network import sendToAnki

class Note(object):
    def __init__(self, model):
        self.model = model
        self.deck = None
        self.fields = [""] * len(model["flds"])
        self.tags = ""
        self.fmap = dict((f['name'], (f['ord'], f)) for f in self.model['flds']) 

    def dupeOrEmpty(self):
        val = self.fields[0]
        if not val.strip():
            return 1
        # find any matching csums and compare
        if sendToAnki("isDupe",
                      {"field": self.fields[0],
                       "model": self.model["name"]}):
            return 2
        return False

    def items(self):
        return [(f['name'], self.fields[ord])
                for ord, f in sorted(self.fmap.values())]

    def isCloze(self):
        return '{{cloze:' in self.model['tmpls'][0]['qfmt']

    def highestCloze(self):
        highest = 0
        for name, val in self.items():
            m = re.findall("\{\{c(\d+)::", val)
            if m:
                highest = max(highest, sorted([int(x) for x in m])[-1])
        return highest