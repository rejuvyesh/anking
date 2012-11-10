#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright muflax <mail@muflax.com>, 2012
# License: GNU GPL 3 <http://www.gnu.org/copyleft/gpl.html>

from aqt.qt import *
import re, os, sys, urllib2, ctypes, traceback
from anki.utils import stripHTML, namedtmp, json
from anki.sound import play
from anki.hooks import addHook, remHook, runHook, runFilter
from aqt.sound import getAudio
from aqt.webview import AnkiWebView
from aqt.utils import shortcut, showInfo, showWarning, getBase, getFile, \
    openHelp
import aqt
import anki.js
from BeautifulSoup import BeautifulSoup

# fixme: when tab order returns to the webview, the previously focused field
# is focused, which is not good when the user is tabbing through the dialog
# fixme: set rtl in div css

# fixme: commit from tag area causes error

pics = ("jpg", "jpeg", "png", "tif", "tiff", "gif", "svg")
audio =  ("wav", "mp3", "ogg", "flac")

_html = """
<html><head>%s<style>
.field {
  border: 1px solid #aaa; background:#fff; color:#000; padding: 5px;
}
/* prevent floated images from being displayed outside field */
.field:after {
    content: ".";
    display: block;
    height: 0;
    clear: both;
    visibility: hidden;
}
.fname { vertical-align: middle; padding: 0; }
img { max-width: 90%%; }
body { margin: 5px; }
</style><script>
%s

var currentField     = null;
var changeTimer      = null;
var dropTarget       = null;

String.prototype.format = function() {
    var args = arguments;
    return this.replace(/\{\d+\}/g, function(m){
            return args[m.match(/\d+/)]; });
};

function saveSelection() {
    py.run("focus:" + currentField.id.substring(1));
    var s = window.getSelection();
    var r = s.getRangeAt(0);
    py.run("selection:" + r.startOffset + ":" + r.endOffset);
}

function setSelection(field, start, end) {
    focusField(field);
    var s = window.getSelection();
    var r = s.getRangeAt(0);
    r.collapse(false);
    r.setStart(r.startContainer, start);
    r.setEnd(r.endContainer, end);
    s.removeAllRanges();
    s.addRange(r);
}

function log(msg) {
    throw new Error("log: "+msg);
}

function onKey() {
    // esc clears focus, allowing dialog to close
    if (window.event.which == 27) {
        currentField.blur();
        return;
    }
    clearChangeTimer();
    if (currentField.innerHTML == "<div><br></div>") {
        // fix empty div bug. slight flicker, but must be done in a timer
        changeTimer = setTimeout(function () {
            currentField.innerHTML = "<br>";
            sendState();
            saveField("key"); }, 1);
    } else {
        changeTimer = setTimeout(function () {
            sendState();
            saveField("key"); }, 600);
    }
};

function sendState() {
    var r = {
        'bold': document.queryCommandState("bold"),
        'italic': document.queryCommandState("italic"),
        'under': document.queryCommandState("underline"),
        'super': document.queryCommandState("superscript"),
        'sub': document.queryCommandState("subscript"),
        'col': document.queryCommandValue("forecolor")
    };
    py.run("state:" + JSON.stringify(r));
};

function setFormat(cmd, arg, nosave) {
    document.execCommand(cmd, false, arg);
    if (!nosave) {
        saveField('key');
    }
};

function clearChangeTimer() {
    if (changeTimer) {
        clearTimeout(changeTimer);
        changeTimer = null;
    }
};

function onFocus(elem) {
    currentField = elem;
    py.run("focus:" + currentField.id.substring(1));
    // don't adjust cursor on mouse clicks
    if (mouseDown) { return; }

    // do this twice so that there's no flicker on newer versions
    //caretToEnd();
    // need to do this in a timeout for older qt versions
    //setTimeout(function () { caretToEnd() }, 1);

    // scroll if bottom of element off the screen
    function pos(obj) {
    	var cur = 0;
        do {
          cur += obj.offsetTop;
         } while (obj = obj.offsetParent);
    	return cur;
    }
    var y = pos(elem);
    if ((window.pageYOffset+window.innerHeight) < (y+elem.offsetHeight) ||
        window.pageYOffset > y) {
        window.scroll(0,y+elem.offsetHeight-window.innerHeight);
    }
}

function focusField(n) {
    $("#f"+n).focus();
}

function onDragOver(elem) {
    // if we focus the target element immediately, the drag&drop turns into a
    // copy, so note it down for later instead
    dropTarget = elem;
}

function caretToEnd() {
    var r = document.createRange()
    r.selectNodeContents(currentField);
    r.collapse(false);
    var s = document.getSelection();
    s.removeAllRanges();
    s.addRange(r);
};

function onBlur() {
    if (currentField) {
        saveField("blur");
    }
    clearChangeTimer();
    // if we lose focus, assume the last field is still targeted
    //currentField = null;
};

function saveField(type) {
    if (!currentField) {
        // no field has been focused yet
        return;
    }
    // type is either 'blur' or 'key'
    py.run(type + ":" + currentField.innerHTML);
    clearChangeTimer();
};

function wrappedExceptForWhitespace(text, front, back) {
    var match = text.match(/^(\s*)([^]*?)(\s*)$/);
    return match[1] + front + match[2] + back + match[3];
};

function wrap(front, back) {
    var s = window.getSelection();
    var r = s.getRangeAt(0);
    var content = r.cloneContents();
    var span = document.createElement("span")
    span.appendChild(content);
    var new_ = wrappedExceptForWhitespace(span.innerHTML, front, back);
    setFormat("inserthtml", new_);
    if (!span.innerHTML) {
        // run with an empty selection; move cursor back past postfix
        r = s.getRangeAt(0);
        r.setStart(r.startContainer, r.startOffset - back.length);
        r.collapse(true);
        s.removeAllRanges();
        s.addRange(r);
    }
};

function setFields(fields, focusTo) {
    var txt = "";
    for (var i=0; i<fields.length; i++) {
        var n = fields[i][0];
        var f = fields[i][1];
        if (!f) {
            f = "<br>";
        }
        txt += "<tr><td class=fname>{0}</td></tr><tr><td width=100%%>".format(n);
        txt += "<div id=f{0} onkeydown='onKey();' onmouseup='onKey();'".format(i);
        txt += " onfocus='onFocus(this);' onblur='onBlur();' class=field ";
        txt += "ondragover='onDragOver(this);' ";
        txt += "contentEditable=true class=field>{0}</div>".format(f);
        txt += "</td></tr>";
    }
    $("#fields").html("<table cellpadding=0 width=100%%>"+txt+"</table>");
    if (!focusTo) {
        focusTo = 0;
    }
    if (focusTo >= 0) {
        $("#f"+focusTo).focus();
    }
};

function setBackgrounds(cols) {
    for (var i=0; i<cols.length; i++) {
        $("#f"+i).css("background", cols[i]);
    }
}

function setFonts(fonts) {
    for (var i=0; i<fonts.length; i++) {
        $("#f"+i).css("font-family", fonts[i][0]);
        $("#f"+i).css("font-size", fonts[i][1]);
        $("#f"+i)[0].dir = fonts[i][2] ? "rtl" : "ltr";
    }
}

function showDupes() {
$("#dupes").show();
}

function hideDupes() {
$("#dupes").hide();
}

var mouseDown = 0;

$(function () {
document.body.onmousedown = function () {
    mouseDown++;
}

document.body.onmouseup = function () {
    mouseDown--;
}

document.onclick = function (evt) {
    var src = window.event.srcElement;
    if (src.tagName == "IMG") {
        // image clicked; find contenteditable parent
        var p = src;
        while (p = p.parentNode) {
            if (p.className == "field") {
                $("#"+p.id).focus();
                break;
            }
        }
    }
}

});

</script></head><body>
<div id="fields"></div>
</body></html>
"""

def _filterHTML(html):
    doc = BeautifulSoup(html)
    # filter out implicit formatting from webkit
    for tag in doc("span", "Apple-style-span"):
        preserve = ""
        for item in tag['style'].split(";"):
            try:
                k, v = item.split(":")
            except ValueError:
                continue
            if k.strip() == "color" and not v.strip() == "rgb(0, 0, 0)":
                preserve += "color:%s;" % v
        if preserve:
            # preserve colour attribute, delete implicit class
            tag.attrs = ((u"style", preserve),)
            del tag['class']
        else:
            # strip completely
            tag.replaceWithChildren()
    for tag in doc("font", "Apple-style-span"):
        # strip all but colour attr from implicit font tags
        if 'color' in dict(tag.attrs):
            tag.attrs = ((u"color", tag['color']),)
            # and apple class
            del tag['class']
        else:
            # remove completely
            tag.replaceWithChildren()
    # turn file:/// links into relative ones
    for tag in doc("img"):
        try:
            if tag['src'].lower().startswith("file://"):
                tag['src'] = os.path.basename(tag['src'])
        except KeyError:
            # for some bizarre reason, mnemosyne removes src elements
            # from missing media
            pass
    # strip superfluous elements
    for elem in "html", "head", "body", "meta":
        for tag in doc(elem):
            tag.replaceWithChildren()
    html = unicode(doc)
    return html

# caller is responsible for resetting note on reset
class AnkingEditor(object):
    def __init__(self, mw, modelChooser, widget, parentWindow):
        self.mw = mw
        self.modelChooser = modelChooser
        self.widget = widget
        self.parentWindow = parentWindow
        self.note = None
        self._loaded = False
        self.currentField = 0
        self.currentSelection = (0, 0)
        self.setupOuter()
        self.setupButtons()
        self.setupWeb()
        self.setupTags()

    # Initial setup
    ############################################################

    def setupOuter(self):
        l = QVBoxLayout()
        l.setMargin(0)
        l.setSpacing(0)
        self.widget.setLayout(l)
        self.outerLayout = l

    def setupWeb(self):
        self.web = EditorWebView(self.widget, self)
        self.web.allowDrops = True
        self.web.setBridge(self.bridge)
        self.outerLayout.addWidget(self.web, 1)
        # pick up the window colour
        p = self.web.palette()
        p.setBrush(QPalette.Base, Qt.transparent)
        self.web.page().setPalette(p)
        self.web.setAttribute(Qt.WA_OpaquePaintEvent, False)

    # Top buttons
    ######################################################################

    def _addButton(self, name, func, key=None, tip=None, size=True, text="",
                   check=False, native=False, canDisable=True):
        b = QPushButton(text)
        if check:
            b.connect(b, SIGNAL("clicked(bool)"), func)
        else:
            b.connect(b, SIGNAL("clicked()"), func)
        if size:
            b.setFixedHeight(20)
            b.setFixedWidth(20)
        if not native:
            b.setStyle(self.plastiqueStyle)
            b.setFocusPolicy(Qt.NoFocus)
        else:
            b.setAutoDefault(False)
        if not text:
            b.setIcon(QIcon(":/icons/%s.png" % name))
        if key:
            b.setShortcut(QKeySequence(key))
        if tip:
            b.setToolTip(shortcut(tip))
        if check:
            b.setCheckable(True)
        self.iconsBox.addWidget(b)
        if canDisable:
            self._buttons[name] = b
        return b

    def setupButtons(self):
        self._buttons = {}
        # button styles for mac
        self.plastiqueStyle = QStyleFactory.create("plastique")
        self.widget.setStyle(self.plastiqueStyle)
        # icons
        self.iconsBox = QHBoxLayout()
        self.iconsBox.setMargin(6)
        self.iconsBox.setSpacing(0)
        self.outerLayout.addLayout(self.iconsBox)
        b = self._addButton
        # align to right
        self.iconsBox.addItem(QSpacerItem(20,1, QSizePolicy.Expanding))
        b("text_bold", self.toggleBold, _("Ctrl+B"), _("Bold text (Ctrl+B)"),
          check=True)
        b("text_italic", self.toggleItalic, _("Ctrl+I"), _("Italic text (Ctrl+I)"),
          check=True)
        b("text_under", self.toggleUnderline, _("Ctrl+U"),
          _("Underline text (Ctrl+U)"), check=True)
        b("text_super", self.toggleSuper, _("Ctrl+="),
          _("Superscript (Ctrl+=)"), check=True)
        b("text_sub", self.toggleSub, _("Ctrl+Shift+="),
          _("Subscript (Ctrl+Shift+=)"), check=True)
        b("text_clear", self.removeFormat, _("Ctrl+R"),
          _("Remove formatting (Ctrl+R)"))
        but = b("foreground", self.onForeground, _("F7"), text=" ")
        but.setToolTip(_("Set foreground colour (F7)"))
        self.setupForegroundButton(but)
        but = b("change_colour", self.onChangeCol, _("F8"),
          _("Change colour (F8)"), text=u"▾")
        but.setFixedWidth(12)
        but = b("cloze", self.onClozeInsert, _("Ctrl+Shift+C"),
                _("Cloze deletion (Ctrl+Shift+C)"), text="[...]")
        but.setFixedWidth(24)
        s = self.clozeShortcut2 = QShortcut(
            QKeySequence(_("Alt+C")), self.parentWindow)
        s.connect(s, SIGNAL("activated()"), self.onClozeInsert)
        # fixme: better image names
        b("mail-attachment", self.onAddMedia, _("F3"),
          _("Attach pictures/audio/video (F3)"))

        but = b("latex", self.insertLatex, _("Ctrl+L"),
                _("LaTeX (Ctrl+L)"), text="LaTeX")
        but.setFixedWidth(50)
        but = b("latex-equation", self.insertLatexEqn, _("Ctrl+M"),
                _("LaTeX Equation (Ctrl+M)"), text="Eq.")
        but.setFixedWidth(30)
        but = b("latex-math", self.insertLatexMathEnv, _("Ctrl+Shift+M"),
                _("LaTeX Math Environment (Ctrl+Shift+M)"), text="Math")
        but.setFixedWidth(35)
        but = b("html", self.onHtmlEdit, _("Ctrl+Shift+H"),
                _("Edit HTML (Ctrl+Shift+H)"), text="HTML")
        but.setFixedWidth(45)
        
        runHook("setupEditorButtons", self)

    def enableButtons(self, val=True):
        for b in self._buttons.values():
            b.setEnabled(val)

    def disableButtons(self):
        self.enableButtons(False)

    # JS->Python bridge
    ######################################################################

    def bridge(self, str):
        if not self.note or not runHook:
            # shutdown
            return
        # focus lost or key/button pressed?
        if str.startswith("blur") or str.startswith("key"):
            (type, txt) = str.split(":", 1)
            txt = self.mungeHTML(txt)
            # misbehaving apps may include a null byte in the text
            txt = txt.replace("\x00", "")
            # reverse the url quoting we added to get images to display
            txt = unicode(urllib2.unquote(
                txt.encode("utf8")), "utf8", "replace")
            self.note.fields[self.currentField] = txt
            if type == "blur":
                self.disableButtons()
                # run any filters
                if runFilter(
                    "editFocusLost", False, self.note, self.currentField):
                    # something updated the note; schedule reload
                    def onUpdate():
                        self.loadNote()
                        self.checkValid()
                else:
                    self.checkValid()
            else:
                runHook("editTimer", self.note)
                self.checkValid()
        # focused into field?
        elif str.startswith("focus"):
            (type, num) = str.split(":", 1)
            self.enableButtons()
            self.currentField = int(num)
        # state buttons changed?
        elif str.startswith("state"):
            (cmd, txt) = str.split(":", 1)
            r = json.loads(txt)
            self._buttons['text_bold'].setChecked(r['bold'])
            self._buttons['text_italic'].setChecked(r['italic'])
            self._buttons['text_under'].setChecked(r['under'])
            self._buttons['text_super'].setChecked(r['super'])
            self._buttons['text_sub'].setChecked(r['sub'])
        elif str.startswith("dupes"):
            self.showDupes()
        # save current selection
        elif str.startswith("selection"):
            (type, start, end) = str.split(":", 2)
            self.currentSelection = (int(start), int(end))
        else:
            print str

    def mungeHTML(self, txt):
        if txt == "<br>":
            txt = ""
        return _filterHTML(txt)

    def focus(self):
        self.web.setFocus()

    def fonts(self):
        return [(f['font'], f['size'], f['rtl'])
                for f in self.note.model['flds']]

    def checkValid(self):
        cols = []
        err = None
        for f in self.note.fields:
            cols.append("#fff")
        err = self.note.dupeOrEmpty()
        if err == 2:
            cols[0] = "#fcc"
            self.web.eval("showDupes();")
        else:
            self.web.eval("hideDupes();")
        self.web.eval("setBackgrounds(%s);" % json.dumps(cols))

    def showDupes(self):
        contents = self.note.fields[0]
        # browser = aqt.dialogs.open("Browser", self.mw)
        # browser.form.searchEdit.lineEdit().setText(
        #     "'note:%s' '%s:%s'" % (
        #         self.note.model['name'],
        #         self.note.model['flds'][0]['name'],
        #         contents))
        # browser.onSearch()
        
    # Write / load note data
    def _loadFinished(self, w):
        self._loaded = True
        if self.note:
            self.loadNote()
        
    def setNote(self, note):
        "Make NOTE the current note."
        self.note = note
        self.currentField = 0
        # change timer
        if self.note:
            self.web.setHtml(_html % (getBase(self.mw.col), anki.js.jquery),
                             loadCB=self._loadFinished)
            self.updateTags()
        else:
            self.hideCompleters()

    def loadNote(self):
        if not self.note:
            return
        field = self.currentField
        if not self._loaded:
            # will be loaded when page is ready
            return
        data = []
        for fld, val in self.note.items():
            data.append((fld, self.mw.col.media.escapeImages(val)))
        self.web.eval("setFields(%s, %d);" % (
            json.dumps(data), field))
        self.web.eval("setFonts(%s);" % (
            json.dumps(self.fonts())))
        self.checkValid()
        self.widget.show()
        self.web.setFocus()

    def saveNow(self):
        "Must call this before adding cards, closing dialog, etc."
        if not self.note:
            return
        self.saveTags()
        if self.mw.app.focusWidget() != self.web:
            # if no fields are focused, there's nothing to save
            return
        # move focus out of fields and save tags
        self.parentWindow.setFocus()
        # and process events so any focus-lost hooks fire
        self.mw.app.processEvents()
        
    # HTML editing
    ######################################################################

    def onHtmlEdit(self):
        d = QDialog(self.widget)
        form = aqt.forms.edithtml.Ui_Dialog()
        form.setupUi(d)
        d.connect(form.buttonBox, SIGNAL("helpRequested()"),
                 lambda: openHelp("editor"))
        form.textEdit.setPlainText(self.note.fields[self.currentField])
        form.textEdit.moveCursor(QTextCursor.End)
        d.exec_()
        html = form.textEdit.toPlainText()
        # filter html through beautifulsoup so we can strip out things like a
        # leading </div>
        html = unicode(BeautifulSoup(html))
        self.note.fields[self.currentField] = html
        self.loadNote()
        # focus field so it's saved
        self.web.setFocus()
        self.web.eval("focusField(%d);" % self.currentField)

    # Tag handling
    ######################################################################

    def setupTags(self):
        import aqt.tagedit
        g = QGroupBox(self.widget)
        g.setFlat(True)
        tb = QGridLayout()
        tb.setSpacing(12)
        tb.setMargin(6)
        # tags
        l = QLabel(_("Tags"))
        tb.addWidget(l, 1, 0)
        self.tags = aqt.tagedit.TagEdit(self.widget)
        self.tags.connect(self.tags, SIGNAL("lostFocus"),
                          self.saveTags)
        tb.addWidget(self.tags, 1, 1)
        g.setLayout(tb)
        self.outerLayout.addWidget(g)

    def updateTags(self):
        if self.tags.col != self.mw.col:
            self.tags.setCol(self.mw.col)
        if not self.tags.text():
            self.tags.setText(self.note.tags.strip())

    def saveTags(self):
        self.note.tags = self.tags.text()
        runHook("tagsUpdated", self.note)

    def hideCompleters(self):
        self.tags.hideCompleter()

    # Format buttons
    ######################################################################

    def toggleBold(self, bool):
        self.web.eval("setFormat('bold');")

    def toggleItalic(self, bool):
        self.web.eval("setFormat('italic');")

    def toggleUnderline(self, bool):
        self.web.eval("setFormat('underline');")

    def toggleSuper(self, bool):
        self.web.eval("setFormat('superscript');")

    def toggleSub(self, bool):
        self.web.eval("setFormat('subscript');")

    def removeFormat(self):
        self.web.eval("setFormat('removeFormat');")

    def onClozeSwitch(self):
        # if we are in a cloze deck, switch to Basic, else to Cloze
        # TODO remember last model?
        if '{{cloze:' not in self.note.model['tmpls'][0]['qfmt']:
            # change to "Cloze" model
            self.changeToModel("Cloze")
        else:
            self.changeToModel("Basic")
        return

    def onClozeInsert(self):
        # make sure we are in a "Cloze" model
        if '{{cloze:' not in self.note.model['tmpls'][0]['qfmt']:
            self.changeToModel("Cloze")
            
        # find the highest existing cloze
        highest = 0
        for name, val in self.note.items():
            m = re.findall("\{\{c(\d+)::", val)
            if m:
                highest = max(highest, sorted([int(x) for x in m])[-1])
        # reuse last if Alt is pressed
        if not self.mw.app.keyboardModifiers() & Qt.AltModifier:
            highest += 1
        # must start at 1
        highest = max(1, highest)
        self.web.eval("wrap('{{c%d::', '}}');" % highest)

    def changeToModel(self, model):
        # remember old data
        self.saveNow()
        oldNote = self.note
        oldField = self.currentField
        self.web.eval("saveSelection();")

        # change model, get new data
        self.modelChooser.changeToModel(model)
        note = self.note
        
        if oldNote and oldNote != note:
            # restore some of the note data
            for n in range(len(note.fields)):
                try:
                    note.fields[n] = oldNote.fields[n]
                except IndexError:
                    break
            self.loadNote()
                    
            # restore caret etc.
            if oldField < len(note.fields):
                self.currentField = oldField
                (start, end) = self.currentSelection
                if start != None and end != None:
                    self.web.eval("setSelection(%d, %d, %d);" % (oldField, start, end))

        
        
        
    # Foreground colour
    ######################################################################

    def setupForegroundButton(self, but):
        self.foregroundFrame = QFrame()
        self.foregroundFrame.setAutoFillBackground(True)
        self.foregroundFrame.setFocusPolicy(Qt.NoFocus)
        self.fcolour = self.mw.pm.profile.get("lastColour", "#00f")
        self.onColourChanged()
        hbox = QHBoxLayout()
        hbox.addWidget(self.foregroundFrame)
        hbox.setMargin(5)
        but.setLayout(hbox)

    # use last colour
    def onForeground(self):
        self._wrapWithColour(self.fcolour)

    # choose new colour
    def onChangeCol(self):
        new = QColorDialog.getColor(QColor(self.fcolour), None)
        # native dialog doesn't refocus us for some reason
        self.parentWindow.activateWindow()
        if new.isValid():
            self.fcolour = new.name()
            self.onColourChanged()
            self._wrapWithColour(self.fcolour)

    def _updateForegroundButton(self):
        self.foregroundFrame.setPalette(QPalette(QColor(self.fcolour)))

    def onColourChanged(self):
        self._updateForegroundButton()
        self.mw.pm.profile['lastColour'] = self.fcolour

    def _wrapWithColour(self, colour):
        self.web.eval("setFormat('forecolor', '%s')" % colour)

    # Audio/video/images
    ######################################################################

    def onAddMedia(self):
        key = (_("Media") +
               " (*.jpg *.png *.gif *.tiff *.svg *.tif *.jpeg "+
               "*.mp3 *.ogg *.wav *.avi *.ogv *.mpg *.mpeg *.mov *.mp4 " +
               "*.mkv *.ogx *.ogv *.oga *.flv *.swf *.flac)")
        def accept(file):
            self.addMedia(file)
        file = getFile(self.widget, _("Add Media"), accept, key, key="media")
        self.parentWindow.activateWindow()

    def addMedia(self, path):
        html = self._addMedia(path)
        self.web.eval("setFormat('inserthtml', %s);" % json.dumps(html))

    def _addMedia(self, path):
        "Add to media folder and return basename."
        # copy to media folder
        name = self.mw.col.media.addFile(path)
        # return a local html link
        ext = name.split(".")[-1].lower()
        if ext in pics:
            return '<img src="%s">' % name
        else:
            anki.sound.play(name)
            return '[sound:%s]' % name

    # LaTeX
    ######################################################################

    def insertLatex(self):
        self.web.eval("wrap('[latex]', '[/latex]');")

    def insertLatexEqn(self):
        self.web.eval("wrap('[$]', '[/$]');")

    def insertLatexMathEnv(self):
        self.web.eval("wrap('[$$]', '[/$$]');")

# Pasting, drag & drop, and keyboard layouts
######################################################################

class EditorWebView(AnkiWebView):

    def __init__(self, parent, editor):
        AnkiWebView.__init__(self)
        self.editor = editor
        self.errtxt = _("An error occured while opening %s")
        self.strip = True

    def keyPressEvent(self, evt):
        if self.keyMatches(evt, "Ctrl+Y") or self.keyMatches(evt, "Ctrl+V"):
            self.onPaste()
        elif self.keyMatches(evt, "Alt+W"):
            self.onCopy()
        elif self.keyMatches(evt, "Ctrl+W") or self.keyMatches(evt, "Ctrl+X"):
            self.onCut()
        elif self.keyMatches(evt, "Ctrl+A"):
            self.onStartLine()
        elif self.keyMatches(evt, "Ctrl+E"):
            self.onEndLine()
        elif self.keyMatches(evt, "Ctrl+K"):
            self.onDeleteEndOfLine()
        elif self.keyMatches(evt, "Ctrl+C"):
            self.editor.onClozeSwitch()
        elif self.keyMatches(evt, "Ctrl+Shift+C"):
            self.editor.onClozeInsert()
        else:
            # no special code
            return QWebView.keyPressEvent(self, evt)
            
        # we parsed it manually
        return evt.accept()

    def keyMatches(self, event, key):
        if not isinstance(key, QKeySequence):
            key = QKeySequence(key)

        # we are lazy, so we just check 1-key sequences
        if key.count() == 1:
            return (event.key() | int(event.modifiers())) == key[0]
        return False
        
    def onCut(self):
        self.triggerPageAction(QWebPage.Cut)
        self._flagAnkiText()

    def onCopy(self):
        self.triggerPageAction(QWebPage.Copy)
        self._flagAnkiText()

    def onPaste(self):
        mime = self.prepareClip()
        self.triggerPageAction(QWebPage.Paste)
        self.restoreClip(mime)

    def onStartLine(self):
        self.triggerPageAction(QWebPage.MoveToStartOfLine)

    def onEndLine(self):
        self.triggerPageAction(QWebPage.MoveToEndOfLine)

    def onDeleteEndOfLine(self):
        self.triggerPageAction(QWebPage.SelectEndOfLine)
        self.triggerPageAction(QWebPage.Cut)

    def mouseReleaseEvent(self, evt):
        if evt.button() == Qt.MidButton:
            # middle click on x11; munge the clipboard before standard
            # handling
            mime = self.prepareClip(mode=QClipboard.Selection)
            AnkiWebView.mouseReleaseEvent(self, evt)
            self.restoreClip(mime, mode=QClipboard.Selection)
        else:
            AnkiWebView.mouseReleaseEvent(self, evt)

    def focusInEvent(self, evt):
        window = False
        if evt.reason() in (Qt.ActiveWindowFocusReason, Qt.PopupFocusReason):
            # editor area got focus again; need to tell js not to adjust cursor
            self.eval("mouseDown++;")
            window = True
        AnkiWebView.focusInEvent(self, evt)
        if evt.reason() == Qt.TabFocusReason:
            self.eval("focusField(0);")
        elif evt.reason() == Qt.BacktabFocusReason:
            n = len(self.editor.note.fields) - 1
            self.eval("focusField(%d);" % n)
        elif window:
            self.eval("mouseDown--;")

    def dropEvent(self, evt):
        oldmime = evt.mimeData()
        # coming from this program?
        if evt.source():
            if oldmime.hasHtml():
                mime = QMimeData()
                mime.setHtml(_filterHTML(oldmime.html()))
            else:
                # old qt on linux won't give us html when dragging an image;
                # in that case just do the default action (which is to ignore
                # the drag)
                return AnkiWebView.dropEvent(self, evt)
        else:
            mime = self._processMime(oldmime)
        # create a new event with the new mime data and run it
        new = QDropEvent(evt.pos(), evt.possibleActions(), mime,
                         evt.mouseButtons(), evt.keyboardModifiers())
        evt.accept()
        QWebView.dropEvent(self, new)
        # tell the drop target to take focus so the drop contents are saved
        self.eval("dropTarget.focus();")
        self.setFocus()

    def prepareClip(self, mode=QClipboard.Clipboard):
        clip = self.editor.mw.app.clipboard()
        mime = clip.mimeData(mode=mode)
        if mime.hasHtml() and mime.html().startswith("<!--anki-->"):
            # pasting from another field, filter extraneous webkit formatting
            html = mime.html()[11:]
            html = _filterHTML(html)
            mime.setHtml(html)
            return
        self.saveClip(mode=mode)
        mime = self._processMime(mime)
        clip.setMimeData(mime, mode=mode)

    def restoreClip(self, mime, mode=QClipboard.Clipboard):
        if not mime:
            return
        clip = self.editor.mw.app.clipboard()
        clip.setMimeData(mime, mode=mode)

    def saveClip(self, mode):
        # we don't own the clipboard object, so we need to copy it
        mime = self.editor.mw.app.clipboard().mimeData(mode=mode)
        n = QMimeData()
        if mime.hasText():
            n.setText(mime.text())
        if mime.hasHtml():
            n.setHtml(mime.html())
        if mime.hasUrls():
            n.setUrls(mime.urls())
        if mime.hasImage():
            n.setImageData(mime.imageData())
        return n

    def _processMime(self, mime):
        # print "html=%s image=%s urls=%s txt=%s" % (
        #     mime.hasHtml(), mime.hasImage(), mime.hasUrls(), mime.hasText())
        # print "html", mime.html()
        # print "urls", mime.urls()
        # print "text", mime.text()
        if mime.hasImage():
            return self._processImage(mime)
        elif mime.hasUrls():
            return self._processUrls(mime)
        elif mime.hasText() and (self.strip or not mime.hasHtml()):
            return self._processText(mime)
        elif mime.hasHtml():
            return self._processHtml(mime)
        else:
            # nothing
            return QMimeData()

    def _processUrls(self, mime):
        url = mime.urls()[0].toString()
        link = self._localizedMediaLink(url)
        mime = QMimeData()
        mime.setHtml(link)
        return mime

    def _localizedMediaLink(self, url):
        l = url.lower()
        for suffix in pics+audio:
            if l.endswith(suffix):
                return self._retrieveURL(url)
        # not a supported type; return link verbatim
        return url

    def _processText(self, mime):
        txt = unicode(mime.text())
        l = txt.lower()
        html = None
        # if the user is pasting an image or sound link, convert it to local
        if l.startswith("http://") or l.startswith("https://") or l.startswith("file://"):
            txt = txt.split("\r\n")[0]
            html = self._localizedMediaLink(txt)
            if html == txt:
                # wasn't of a supported media type; don't change
                html = None
        new = QMimeData()
        if html:
            new.setHtml(html)
        else:
            new.setText(mime.text())
        return new

    def _processHtml(self, mime):
        html = mime.html()
        if self.strip:
            html = stripHTML(html)
        else:
            html = _filterHTML(html)
        mime = QMimeData()
        mime.setHtml(html)
        return mime

    def _processImage(self, mime):
        im = QImage(mime.imageData())
        uname = namedtmp("paste-%d" % im.cacheKey())
        ext = ".jpg"
        im.save(uname+ext, None, 80)
        # invalid image?
        if not os.path.exists(uname+ext):
            return QMimeData()
        mime = QMimeData()
        mime.setHtml(self.editor._addMedia(uname+ext))
        return mime

    def _retrieveURL(self, url):
        # is it media?
        ext = url.split(".")[-1].lower()
        if ext not in pics and ext not in audio:
            return
        # fetch it into a temporary folder
        try:
            req = urllib2.Request(url, None, {
                'User-Agent': 'Mozilla/5.0 (compatible; Anki)'})
            filecontents = urllib2.urlopen(req).read()
        except urllib2.URLError, e:
            showWarning(self.errtxt % e)
            return
        path = namedtmp(os.path.basename(url))
        file = open(path, "wb")
        file.write(filecontents)
        file.close()
        return self.editor._addMedia(path)

    def _flagAnkiText(self):
        # add a comment in the clipboard html so we can tell text is copied
        # from us and doesn't need to be stripped
        clip = self.editor.mw.app.clipboard()
        mime = clip.mimeData()
        if not mime.hasHtml():
            return
        html = mime.html()
        mime.setHtml("<!--anki-->" + mime.html())

    def contextMenuEvent(self, evt):
        m = QMenu(self)
        a = m.addAction(_("Cut"))
        a.connect(a, SIGNAL("activated()"), self.onCut)
        a = m.addAction(_("Copy"))
        a.connect(a, SIGNAL("activated()"), self.onCopy)
        a = m.addAction(_("Paste"))
        a.connect(a, SIGNAL("activated()"), self.onPaste)
        m.popup(QCursor.pos())