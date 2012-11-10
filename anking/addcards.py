#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

from aqt.qt import *
from anki.errors import *
from anki.hooks import addHook, remHook, runHook
from anki.sound import clearAudioQueue
from anki.utils import stripHTML
from anki.utils import stripHTMLMedia
from aqt.utils import showCritical, askUser, shortcut, tooltip

from mock import Mock

import anking.add_form
import anking.deckchooser
import anking.editor
import anking.modelchooser
import anking.network
import anking.notes

class AddCards(QDialog):
    def __init__(self, mw, deck=None, model=None):
        QDialog.__init__(self, None, Qt.Window)
        self.mw = mw
        self.form = anking.add_form.Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowTitle("Anking Off")
        self.setMinimumHeight(300)
        self.setMinimumWidth(400)
        self.setupChoosers()
        self.setupEditor()
        self.setupButtons()
        self.onReset()
        self.forceClose = False

        # starting parameters
        if deck:
            self.deckChooser.changeToDeck(deck)
        if model:
            self.modelChooser.changeToModel(model)
            
        addHook('reset', self.onReset)
        addHook('currentModelChanged', self.onReset)
        self.show()
        self.setupNewNote()

    def setupEditor(self):
        self.editor = anking.editor.AnkingEditor(self.mw, self.modelChooser, self.form.fieldsArea, self)

    def setupChoosers(self):
        self.modelChooser = anking.modelchooser.ModelChooser(
            self.mw, self.form.modelArea)
        self.deckChooser = anking.deckchooser.DeckChooser(
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

        # shortcuts
        # switch to tag / fields
        s = QShortcut(QKeySequence(_("Ctrl+t")), self)
        s.connect(s, SIGNAL("activated()"), self.onTagFocus)
        s = QShortcut(QKeySequence(_("Ctrl+f")), self)
        s.connect(s, SIGNAL("activated()"), self.onFieldFocus)

    def onTagFocus(self):
        self.editor.tags.setFocus()

    def onFieldFocus(self):
        self.editor.focus()
        
    def setupNewNote(self):
        note = anking.notes.Note(self.mw.col, self.modelChooser.currentModel)
        self.editor.setNote(note)
        return note

    def onReset(self, keep=False):
        oldNote = self.editor.note
        note = self.setupNewNote()
        flds = note.model['flds']
        # copy fields from old note
        if oldNote:
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

    def addCards(self):
        self.editor.saveNow()
        
        # grab data
        note = self.editor.note

        # sanity check
        if note.dupeOrEmpty():
            showCritical("Note is a dupe or empty; not adding.")
            return
            
        # check for cloze sanity in case of potential cloze-y notes
        if len(note.fields) == 2:
            # find the highest existing cloze
            highest = note.highestCloze()    
            if highest > 0 and not note.isCloze():
                # clozes used, but wrong model, so switch it to cloze
                self.editor.changeToModel("Cloze")
                note = self.editor.note
            elif note.isCloze() and highest == 0:
                # no clozes, switch to basic
                self.editor.changeToModel("Basic")
                note = self.editor.note
        
        # send data to TCP server in Anki
        data = {
            "model": note.model["name"],
            "deck": note.deck,
            "fields": note.fields,
            "tags": note.tags,
        }
        
        ret = anking.network.sendToAnki("addNote", data)
        if ret:
            self.mw.reset()
            # stop anything playing
            clearAudioQueue()
            self.onReset(keep=True)
        else:
            showCritical("Failed to add card. Is Anki ok?")

    def keyPressEvent(self, evt):
        "Show answer on RET or register answer."
        if (evt.key() in (Qt.Key_Enter, Qt.Key_Return)
            and self.editor.tags.hasFocus()):
            evt.accept()
            return
        return QDialog.keyPressEvent(self, evt)

    def reject(self):
        remHook('reset', self.onReset)
        remHook('currentModelChanged', self.onReset)
        clearAudioQueue()
        self.editor.setNote(None)
        self.modelChooser.cleanup()
        self.deckChooser.cleanup()
        self.mw.reset()
        QDialog.reject(self)