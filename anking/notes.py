#!/usr/bin/env python3
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

from anki.utils import fieldChecksum, splitFields

class Note(object):
    def __init__(self, col, model):
        self.model = model
        self.deck = None
        self.fields = [""] * len(model["flds"])
        self.tags = ""
        self.col = col
        self.fmap = self.col.models.fieldMap(self.model)

    def dupeOrEmpty(self):
        val = self.fields[0]
        if not val.strip():
            return True
        # find any matching csums and compare
        csum = fieldChecksum(val)
        mid = self.model["id"]
        for flds in self.col.db.list(
            "select flds from notes where csum = ? and id != ? and mid = ?",
            csum, 0, mid):
            if splitFields(flds)[0] == note["fields"][0]:
                return True
        return False

    def items(self):
        return [(f['name'], self.fields[ord])
                for ord, f in sorted(self.fmap.values())]
