# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
from operator import itemgetter
from anki.hooks import addHook, remHook, runHook
from aqt.utils import isMac, shortcut
import aqt

from anking.network import sendToAnki

class DeckChooser(QHBoxLayout):

    def __init__(self, mw, widget, label=True, start=None):
        QHBoxLayout.__init__(self)
        self.widget = widget
        self.mw = mw
        self.label = label
        self.setMargin(0)
        self.setSpacing(8)
        self.setupDecks()
        self.widget.setLayout(self)
        addHook('currentModelChanged', self.onModelChange)

    def setupDecks(self):
        if self.label:
            self.deckLabel = QLabel(_("Deck"))
            self.addWidget(self.deckLabel)
        # decks box
        self.deck = QPushButton()
        self.deck.setToolTip(shortcut(_("Target Deck (Ctrl+D)")))
        s = QShortcut(QKeySequence(_("Ctrl+D")), self.widget)
        s.connect(s, SIGNAL("activated()"), self.onDeckChange)
        self.addWidget(self.deck)
        self.connect(self.deck, SIGNAL("clicked()"), self.onDeckChange)
        # starting label

        decks = sendToAnki("decks")
        deck_name = "Default"
        for deck in decks:
            if deck['id'] == 1:
                deck_name = deck["name"]
                break
        self.deck.setText(deck_name)
        # layout
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy(7),
            QSizePolicy.Policy(0))
        self.deck.setSizePolicy(sizePolicy)

    def show(self):
        self.widget.show()

    def hide(self):
        self.widget.hide()

    def onModelChange(self):
        pass

    def changeToDeck(self, name):
        self.deck.setText(name)

    def onDeckChange(self):
        from aqt.studydeck import StudyDeck
        current = self.deck.text()
        def nameFunc():
            decks = sendToAnki("decks")
            return sorted([d["name"] for d in decks])
        ret = StudyDeck(
            self.mw, current=current, accept=_("Choose"),
            title=_("Choose Deck"), help="addingnotes",
            cancel=False, parent=self.widget, names=nameFunc)
        self.deck.setText(ret.name)

    def selectedId(self):
        # save deck name
        name = self.deck.text()
        if not name.strip():
            did = 1
        else:
            decks = sendToAnki("decks")
            for deck in decks:
                if deck['name'] == name:
                    did = int(deck["id"])
                    break
        return did

    def cleanup(self):
        remHook('currentModelChanged', self.onModelChange)
