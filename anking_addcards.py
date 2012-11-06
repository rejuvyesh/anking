#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

# anki libs
from aqt.qt import *
from anki.errors import *
from anki.utils import stripHTML
from aqt.utils import showWarning, askUser, shortcut, tooltip
from anki.sound import clearAudioQueue
from anki.utils import stripHTMLMedia, isMac
import aqt.editor, aqt.modelchooser, aqt.deckchooser

from mock import Mock

# form
import anking_form
import anking_editor

class AddCards(QDialog):
    def __init__(self, mw):
        QDialog.__init__(self, None, Qt.Window)
        self.mw = mw
        self.form = anking_form.Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowTitle("Anking Off")
        self.setMinimumHeight(300)
        self.setMinimumWidth(400)
        self.setupChoosers()
        self.setupEditor()
        self.setupButtons()
        self.onReset()
        self.history = []
        self.forceClose = False
        # restoreGeom(self, "add")
        self.show()
        # self.setupNewNote()

    def setupEditor(self):
        self.editor = anking_editor.AnkingEditor(
            self.mw, self.form.fieldsArea, self, True)

    def setupChoosers(self):
        self.modelChooser = aqt.modelchooser.ModelChooser(
            self.mw, self.form.modelArea)
        self.deckChooser = aqt.deckchooser.DeckChooser(
            self.mw, self.form.deckArea)

    def setupButtons(self):
        bb = self.form.buttonBox
        ar = QDialogButtonBox.ActionRole

        # add
        self.addButton = bb.addButton("Add", ar)
        self.addButton.setShortcut(QKeySequence("Ctrl+Return"))
        self.addButton.setToolTip(shortcut("Add (shortcut: ctrl+enter)"))
        self.connect(self.addButton, SIGNAL("clicked()"), self.addCards)

        # close
        self.closeButton = QPushButton("Close")
        self.closeButton.setAutoDefault(False)
        bb.addButton(self.closeButton, QDialogButtonBox.RejectRole)

        # history
        b = bb.addButton("History"+ u" ▾", ar)
        self.connect(b, SIGNAL("clicked()"), self.onHistory)
        b.setEnabled(False)
        self.historyButton = b

    def setupNewNote(self, set=True):
        f = self.mw.col.newNote()
        f.tags = f.model()['tags']
        if set:
            self.editor.setNote(f)
        return f

    def onReset(self, model=None, keep=False):
        oldNote = self.editor.note
        note = self.setupNewNote(set=False)
        flds = note.model()['flds']
        # copy fields from old note
        if oldNote:
            if not keep:
                self.removeTempNote(oldNote)
            for n in range(len(note.fields)):
                try:
                    if not keep or flds[n]['sticky']:
                        note.fields[n] = oldNote.fields[n]
                    else:
                        note.fields[n] = ""
                except IndexError:
                    break
        self.editor.currentField = 0
        self.editor.setNote(note)

    def removeTempNote(self, note):
        if not note or not note.id:
            return
        # we don't have to worry about cards; just the note
        self.mw.col._remNotes([note.id])

    def addHistory(self, note):
        txt = stripHTMLMedia(",".join(note.fields))[:30]
        self.history.insert(0, (note.id, txt))
        self.history = self.history[:15]
        self.historyButton.setEnabled(True)

    def onHistory(self):
        m = QMenu(self)
        for nid, txt in self.history:
            a = m.addAction("Edit %s" % txt)
            a.connect(a, SIGNAL("triggered()"),
                      lambda nid=nid: self.editHistory(nid))
        m.exec_(self.historyButton.mapToGlobal(QPoint(0,0)))

    def editHistory(self, nid):
        browser = aqt.dialogs.open("Browser", self.mw)
        browser.form.searchEdit.lineEdit().setText("nid:%d" % nid)
        browser.onSearch()

    def addNote(self, note):
        note.model()['did'] = self.deckChooser.selectedId()
        ret = note.dupeOrEmpty()
        if ret == 1:
            showWarning("The first field is empty.",
                        help="AddItems#AddError")
            return
        cards = self.mw.col.addNote(note)
        if not cards:
            showWarning("""\
The input you have provided would make an empty \
question on all cards.""", help="AddItems")
            return
        self.addHistory(note)
        self.mw.requireReset()
        return note

    def addCards(self):
        self.editor.saveNow()
        self.editor.saveAddModeVars()
        note = self.editor.note
        note = self.addNote(note)
        if not note:
            return
        tooltip("Added", period=500)
        # stop anything playing
        clearAudioQueue()
        self.onReset(keep=True)
        self.mw.col.autosave()

    def keyPressEvent(self, evt):
        "Show answer on RET or register answer."
        if (evt.key() in (Qt.Key_Enter, Qt.Key_Return)
            and self.editor.tags.hasFocus()):
            evt.accept()
            return
        return QDialog.keyPressEvent(self, evt)

    def reject(self):
        if not self.canClose():
            return
        clearAudioQueue()
        self.removeTempNote(self.editor.note)
        self.editor.setNote(None)
        self.modelChooser.cleanup()
        self.deckChooser.cleanup()
        self.mw.maybeReset()
        # saveGeom(self, "add")
        aqt.dialogs.close("AddCards")
        QDialog.reject(self)

    def canClose(self):
        if (self.forceClose or self.editor.fieldsAreBlank() or
            askUser("Close and lose current input?")):
            return True
        return False

