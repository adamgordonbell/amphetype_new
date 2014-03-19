# -*- coding: UTF-8 -*-

#Changelog
#March 19 2014: Added template for changing color of letters in typer and label
#               depending on errors and position (lalop) 

from __future__ import with_statement, division

ALLOW_MISTAKES = False
LABEL_NORMAL_TEXT_COLOR = "#777777"
LABEL_TEXT_POSITION_COLOR = "green"
LABEL_TEXT_POSITION_WITH_MISTAKE_COLOR = "green"
LABEL_MISTAKES_COLOR = "#a43434"

TEXT_AREA_MISTAKES_COLOR = "#a43434"
TEXT_AREA_REPLACE_SPACES = False

SPACE_REPLACEMENT = "&#8729;"

import platform
import collections
import time
import re
import random

import Globals
from Data import Statistic, DB
from Config import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from QtUtil import *

if platform.system() == "Windows":
    # hack hack, hackity hack
    timer = time.clock
    timer()
else:
    timer = time.time
    
def html_color_letters(strs,new_colors,default_color=None):
    '''strs is list of typically 1 character strings from doing list(string) 

new_colors is a dict : positions (int) -> colors as accepted by html

Non-destructively returns strs with the positions of new_colors changed to the new colors in html'''
    def colorize(i):
        s = strs[i]
        color_s = lambda c : s if c == None else u'<font color="{0}">{1}</font>'.format(c,s)
        if i not in new_colors:
            return color_s(default_color)
        else:
            return color_s(new_colors[i])

    return map(colorize,range(len(strs)))

def replace_at_locs(strs,replacements,locations = None):
    '''strs is list of typically 1 character strings from doing list(string) 
    
replacements is a dict : str -> str, interpreted as source -> replacement
    
locations is a list of ints.  If location is None (not to be confused with []), assume allow all locations. 

Non-destructively: in each index of locations, if the string at that index is in replacements,
replaces it.  Otherwise, leaves it.'''
    def replace_at_locs_a(i):
        s = strs[i]
        if locations != None and i not in locations or s not in replacements:
            return s
        else:
            return replacements[s]

    return map(replace_at_locs_a,range(len(strs)))
    
def disagreements(s,t,full_length=False):
    '''List of all disagreement positions between strings/lists s and t

    Only checks up to the shorter of the two'''
    dlist = []
    for i in range(min(len(s),len(t))):
        if s[i] != t[i]:
            dlist.append(i)

    return dlist
try:
    import winsound
except ImportError:
    import os
    def playsound(frequency, duration):
        return
        #apt-get install beep
        os.system('beep -f %s -l %s' % (frequency, duration))
else:
    def playsound(frequency, duration):
        winsound.Beep(frequency, duration)

wordCache = dict()

class Typer(QTextEdit):
    def __init__(self, *args):
        super(Typer, self).__init__(*args)

        self.setPalettes()
        self.permissive = Settings.get("permissive_errors")
        self.connect(self, SIGNAL("textChanged()"), lambda: self.emit(SIGNAL("textChanged")))
        #self.setLineWrapMode(QTextEdit.NoWrap)
        self.connect(Settings, SIGNAL("change_quiz_wrong_fg"), self.setPalettes)
        self.connect(Settings, SIGNAL("change_quiz_wrong_bg"), self.setPalettes)
        self.connect(Settings, SIGNAL("change_quiz_right_fg"), self.setPalettes)
        self.connect(Settings, SIGNAL("change_quiz_right_bg"), self.setPalettes)
        if Settings.get("invisible_mode"):
            self.setTextColor(QColor(Qt.white))
            self.setTextBackgroundColor(QColor(Qt.white))
            self.setCursorWidth(0)
        self.target = None
        self.when = None
        self.is_lesson = None
        self.times = None
        self.editflag = None
        self.mistakes = None
        self.where = None
        self.mistake = None
        self.editflag = None
        self.mins = None
        self.count = 0
        self.max_count = 0
        self.last_count = 0

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.emit(SIGNAL("cancel"))
        elif e.key() == Qt.Key_Backspace and int(e.modifiers()) == 1073741824: #Altgr backspace
            e = QKeyEvent(QEvent.KeyPress, e.key(), Qt.KeyboardModifiers(0),e.text(),e.isAutoRepeat(),e.count())
        elif e.key() == Qt.Key_Return and int(e.modifiers()) == 1073741824: #Altgr return 
            e = QKeyEvent(QEvent.KeyPress, e.key(), Qt.KeyboardModifiers(0),e.text(),e.isAutoRepeat(),e.count())

        return QTextEdit.keyPressEvent(self, e)

    def setPalettes(self):
        inactive_palette = QPalette(Qt.black, Qt.lightGray, Qt.lightGray, Qt.darkGray,
                                 Qt.gray, QColor(120,120,120), # QColor(20,20,20)
                                    QColor(0,0,0)
        )
        # inactive_palette.setColor(QPalette.Highlight, QColor(15,25,20))
        # inactive_palette.setColor(QPalette.HighlightedText, QColor(55,60,60))
        inactive_palette.setColor(QPalette.Highlight, QColor(5,15,10))
        inactive_palette.setColor(QPalette.HighlightedText, QColor(45,50,51))
        self.palettes = {
            'wrong': QPalette(Qt.black,
                Qt.lightGray, Qt.lightGray, Qt.darkGray, Qt.gray,
                Settings.getColor("quiz_wrong_fg"), Qt.white, Settings.getColor("quiz_wrong_bg"), Qt.yellow),
            'right': QPalette(Qt.black,
                Qt.lightGray, Qt.lightGray, Qt.darkGray, Qt.gray,
                Settings.getColor("quiz_right_fg"), Qt.yellow, Settings.getColor("quiz_right_bg"), Qt.yellow),
            'inactive':inactive_palette }
        self.setPalette(self.palettes['inactive'])

    def setTarget(self, text, guid):
        self.editflag = True
        self.target = text
        self.when = [0] * (len(self.target)+1)

        # time for each character typed
        self.times = [0] * len(self.target)

        # whether each character was a mistake
        self.mistake = [False] * len(self.target)

        # mistake characters ( must be what was actually typed )
        self.mistakes = {} #collections.defaultdict(lambda: [])
        self.where = 0
        self.clear()
        self.setPalette(self.palettes['inactive'])
        self.setText(self.getWaitText())
        self.selectAll()
        self.editflag = False
        self.is_lesson = DB.fetchone("select discount from source where rowid=?", (None, ), (guid, ))[0]
        if self.is_lesson:
            self.mins = (Settings.get("min_lesson_wpm"), Settings.get("min_lesson_acc"))
        else:
            self.mins = (Settings.get("min_wpm"), Settings.get("min_acc"))

    def getWaitText(self):
        if Settings.get('req_space'):
            return "Press SPACE and then immediately start typing the text\n" + \
                    "Press ESCAPE to restart with a new text at any time"
        else:
            return "Press ESCAPE to restart with a new text at any time"

    def checkText(self):
        if self.target is None or self.editflag:
            return

        v = unicode(self.toPlainText())
        if self.when[0] == 0:
            space = len(v) > 0 and v[-1] == u" "
            req = Settings.get('req_space')

            self.editflag = True
            if space:
                self.when[0] = timer()
                self.clear()
                self.setPalette(self.palettes['right'])
            elif req:

                self.setText(self.getWaitText())
                self.selectAll()
            self.editflag = False

            if req or space:
                return
            else:
                self.when[0] = -1

        y = 0
        for y in xrange(min(len(v), len(self.target)), -1, -1):
            if v[0:y] == self.target[0:y]:
                break
        lcd = v[0:y]
        self.where = y

        if self.when[y] == 0 and y == len(v):
            self.when[y] = timer()
            if y > 0:
                self.times[y-1] = self.when[y] - self.when[y-1]

        if lcd == self.target or ALLOW_MISTAKES and len(v) >= len(self.target):
            if not any(self.mistake):
                self.count = self.count + 1
                self.max_count = max(self.max_count, self.count)
            self.emit(SIGNAL("done"))
            return

        if y < len(v) and y < len(self.target):
            self.mistake[y] = True
            self.mistakes[y] = self.target[y] + v[y]
            self.last_count = self.count
            self.count = 0

        if v == lcd:
            self.setPalette(self.palettes['right'])
        else:
             # Fail on 100%
            if self.mins[1] == 100.0:
                self.emit(SIGNAL("repeat"))
            else:

                if self.permissive:
                    self.setText(self.target[0:(len(v))])
                    cursor = self.textCursor()
                    cursor.setPosition(len(v))
                    self.setTextCursor(cursor)
                    Freq = 300
                    Dur = 100
                    playsound(Freq, Dur)
                else:
                    self.setPalette(self.palettes['wrong'])
    def getMistakes(self):
        inv = collections.defaultdict(lambda: 0)
        for p, m in self.mistakes.iteritems():
            inv[m] += 1
        return inv

    def getElapsed(self):
        return self.when[self.where]-self.when[0]

    def getStats(self):
        if self.when[0] == -1:
            # my refactoring mean this may never get hit, I'm not sure what when and times are for, so i'm not sure if I'm breaking some edge case here??
            t = self.times[1:]
            t.sort(reverse=True)
            v = DB.fetchone('select time from statistic where type = 0 and data = ? order by rowid desc limit 1', (t[len(t)//5], ), (self.target[0], ))
            self.times[0] = v[0]
            self.when[0] = self.when[1] - self.times[0]
        return self.getElapsed(), self.where, self.times, self.mistake, self.getMistakes()

    def getAccuracy(self):
        if self.where > 0:
            return 1.0 - len(filter(None, self.mistake)) / self.where
        else:
            return 0

    def getRawSpeed(self):
        if self.where > 0:
            return self.getElapsed() / self.where
        else:
            return 1

    def getSpeed(self):
        return 12 / self.getRawSpeed()

    def getViscosity(self):
        return sum(map(lambda x: ((x-self.getRawSpeed())/self.getRawSpeed())**2, self.times)) / self.where

class Quizzer(QWidget):
    def __init__(self, *args):
        super(Quizzer, self).__init__(*args)

        self.result = QLabel()
        self.typer = Typer()
        self.label = WWLabel()
        self.result.setVisible(Settings.get("show_last"))
        self.label.setStyleSheet("padding: 1px")
        #self.label.setFrameStyle(QFrame.Raised | QFrame.StyledPanel)
        #self.typer.setBuddy(self.label)
        self.info = SettingsCheckBox('repeat', 'repeat lesson') # AmphButton("Back one", self.lastText)
        self.connect(self.typer, SIGNAL("done"), self.done)
        self.connect(self.typer,  SIGNAL("textChanged"), self.checkText)
        self.connect(self.typer, SIGNAL("cancel"), SIGNAL("wantText"))
        self.connect(Settings, SIGNAL("change_typer_font"), self.readjust)
        self.connect(Settings, SIGNAL("change_show_last"), self.result.setVisible)
        self.connect(self.typer, SIGNAL("repeat"), self.repeatText)

        self.text = ('', '', 0, None)

        layout = QVBoxLayout()
        if Settings.get('show_repeat'):
            layout.addWidget(self.info)
        layout.addSpacing(20)
        layout.addWidget(self.result, 0, Qt.AlignRight)
        layout.addWidget(self.label, 1, Qt.AlignBottom)
        layout.addWidget(self.typer, 1)
        self.setLayout(layout)
        self.readjust()

    def updateLabel(self,position,errors):
        text_strs = replace_at_locs(list(self.text[2]),{" ":SPACE_REPLACEMENT,"\n":"&#8629;<BR>"},errors)
        colors = dict([(position, LABEL_TEXT_POSITION_WITH_MISTAKE_COLOR if errors else LABEL_TEXT_POSITION_COLOR)] +
                      [(i,LABEL_MISTAKES_COLOR) for i in errors])
        htmlized = "".join(html_color_letters(text_strs,colors)).replace(u"\n", u"↵<BR>")

        self.label.setText(htmlized) 

    def checkText(self):
        if self.typer.target is None or self.typer.editflag:
            return

        v = unicode(self.typer.toPlainText())
        if self.typer.when[0] == 0:
            space = len(v) > 0 and v[-1] == u" "
            req = Settings.get('req_space')

            self.typer.editflag = True
            if space:
                self.typer.when[0] = timer()
                self.typer.clear()
                self.typer.setPalette(self.typer.palettes['right'])
            elif req:
                self.typer.setText(self.typer.getWaitText())
                self.typer.selectAll()
            self.typer.editflag = False

            if req or space:
                return
            else:
                self.typer.when[0] = -1

        y = 0
        for y in xrange(min(len(v), len(self.typer.target)), -1, -1):
            if v[0:y] == self.typer.target[0:y]:
                break
        lcd = v[0:y]
        self.typer.where = y

        if self.typer.when[y] == 0 and y == len(v):
            self.typer.when[y] = timer()
            if y > 0:
                self.typer.times[y-1] = self.typer.when[y] - self.typer.when[y-1]

        if lcd == self.typer.target or ALLOW_MISTAKES and len(v) >= len(self.typer.target):
            self.done()
            return

        if y < len(v) and y < len(self.typer.target):
            self.typer.mistake[y] = True
            self.typer.mistakes[y] = self.typer.target[y] + v[y]

        if v == lcd:
            self.typer.setPalette(self.typer.palettes['right'])
        else:
            self.typer.setPalette(self.typer.palettes['wrong'])
            
        #colors text in typer depending on errors
        errors = disagreements(v,self.typer.target)
        error_colors = dict(map(lambda d : (d,TEXT_AREA_MISTAKES_COLOR),errors))
        self.typer.editflag = True
        
        v_err_replacements = {"\n":"&#8629;"}
        if TEXT_AREA_REPLACE_SPACES:
            #if want to make replacements change spaces in text area as well (risky!)
            v_err_replacements[" "] = SPACE_REPLACEMENT

        v_replaced_list = replace_at_locs(list(v),v_err_replacements,errors)

        v_colored_list = html_color_letters(v_replaced_list,error_colors)
        htmlized = "".join(v_colored_list).replace("\n","<BR>")

        old_cursor = self.typer.textCursor()
        old_position = old_cursor.position()
        
        self.typer.setHtml(htmlized)
        old_cursor.setPosition(old_position)
        self.typer.setTextCursor(old_cursor)

        self.typer.editflag = False
        
        #updates the label depending on errors
        self.updateLabel(old_position,errors)

    def readjust(self):
        f = Settings.getFont("typer_font")
        f.setKerning(False)
        self.label.setFont(f)
        self.typer.setFont(f)

    def setText(self, text):
        self.text = text 

        tempText = self.AddSymbols(text[2])
        tempText = tempText.replace('  ', ' ')
        self.text = (text[0], text[1], tempText)

        self.label.setText(self.text[2].replace(u"\n", u"↵\n"))
        self.typer.setTarget(self.text[2], self.text[1])
        self.typer.setFocus()

    def repeatText(self):
        Freq = 250
        Dur = 200
        playsound(Freq, Dur)
        self.updateResultLabel()
        self.setText(self.text)

    def lastText(self):
        self.emit(SIGNAL("lastText"))

    def getStatsAndViscosity(self):
        stats = collections.defaultdict(Statistic)
        visc = collections.defaultdict(Statistic)
        text = self.text[2]
        perCharacterMistakes = self.typer.mistake
        perCharacterTimes = self.typer.times
        spc = self.typer.getRawSpeed()

        for c, t, m in zip(text, self.typer.times, perCharacterMistakes):
            stats[c].append(t, m)
            visc[c].append(((t-spc)/spc)**2)

        def gen_tup(s, e):
            perch = sum(perCharacterTimes[s:e])/(e-s)
            visc = sum(map(lambda x: ((x-perch)/perch)**2, perCharacterTimes[s:e]))/(e-s)
            return (text[s:e], perch, len(filter(None, perCharacterMistakes[s:e])), visc)

        for tri, t, m, v in [gen_tup(i, i+3) for i in xrange(0, self.typer.where-2)]:
            stats[tri].append(t, m > 0)
            visc[tri].append(v)

        wordRegex = re.compile(r"(\w|'(?![A-Z]))+(-\w(\w|')*)*")
        for w, t, m, v in [gen_tup(*x.span()) for x in wordRegex.finditer(text) if x.end()-x.start() > 3]:
            stats[w].append(t, m > 0)
            visc[w].append(v)

        #pairRegex = re.compile(r"(?=(\b[^\s]+\s+[^\s]+))")
        #for w, t, m, v in [gen_tup(*x.span(1)) for x in pairRegex.finditer(text) if x.end(1)-x.start(1) > 3]:
        #    stats[w].append(t, m > 0)
        #    visc[w].append(v)
        if Settings.get('phrase_lessons'):
            tripleRegex = re.compile(r"(?=(\b[^\s]+\s+[^\s]+\s+[^\s]+))")
            for w, t, m, v in [gen_tup(*x.span(1)) for x in tripleRegex.finditer(text) if x.end(1)-x.start(1) > 3]:
                stats[w].append(t, m > 0)
                visc[w].append(v)

        return stats, visc

    def updateResultLabel(self):
        spc = self.typer.getSpeed()
        accuracy = self.typer.getAccuracy()
        v2 = DB.fetchone("""select agg_median(wpm), agg_median(acc) from
            (select wpm, 100.0*accuracy as acc from result order by w desc limit %d)""" % Settings.get('def_group_by'), (0.0, 100.0))
        if Settings.get('show_since_fail_counter'):
            self.result.setText("Last: %.1fwpm (%.1f%%), last 10 average: %.1fwpm (%.1f%%) \n\nPerfect Count: (Current :%1d) (Max : %1d) (Last : %1d)"  % ((spc, 100.0*accuracy) + v2 + ( self.typer.count, self.typer.max_count, self.typer.last_count)))
        else:
            self.result.setText("Last: %.1fwpm (%.1f%%), last 10 average: %.1fwpm (%.1f%%)"  % ((spc, 100.0*accuracy) + v2 ))

    def insertResults(self, now):
        return DB.execute('insert into result (w, text_id, source, wpm, accuracy, viscosity) values (?, ?, ?, ?, ?, ?)',
                           (now, self.text[0], self.text[1], 12.0/self.typer.getRawSpeed(), self.typer.getAccuracy(), self.typer.getViscosity()))

    def done(self):
        now = time.time()
        assert self.typer.where == len(self.text[2])

        if ALLOW_MISTAKES:
            self.emit(SIGNAL("wantText"))
            return

        self.insertResults(now)

        self.updateResultLabel()

        self.emit(SIGNAL("statsChanged"))

        if Settings.get('use_lesson_stats') or not self.isLesson():
            stats, visc = self.getStatsAndViscosity()
            vals = self.getVals(now, stats, visc)
            self.insertStats(now, vals)

        # if Fail cut-offs, redo
        if self.lessThanSpeed() or self.lessThanAccuracy():
            self.setText(self.text)
        # if pending lessons left, then keep going
        elif self.isLesson() and Globals.pendingLessons:
            self.emit(SIGNAL("newReview"), Globals.pendingLessons.pop())
        # create a lesson
        elif not self.isLesson() and Settings.get('auto_review'):
            self.createLessons(vals)
        # Success, new lesson
        else:
            self.emit(SIGNAL("wantText"))

    def getVals(self, now, stats, visc):
        def type(k):
            if len(k) == 1:
                return 0
            elif len(k) == 3:
                return 1
            elif len(k.split()) > 1:
                return 3
            return 2
        vals = []
        for k, s in stats.iteritems():
            v = visc[k].median()
            vals.append((s.median(), v*100.0, now, len(s), s.flawed(), type(k), k))
        return vals

    def insertStats(self, now, vals):
        DB.executemany_('''insert into statistic
            (time, viscosity, w, count, mistakes, type, data) values (?, ?, ?, ?, ?, ?, ?)''', vals)
        DB.executemany_('insert into mistake (w, target, mistake, count) values (?, ?, ?, ?)',
                [(now, k[0], k[1], v) for k, v in self.typer.getMistakes().iteritems()])

    def createLessons(self, vals):
        # need to add of type #3 to these lessons
        # get words
        words = filter(lambda x: x[5] == 2, vals)
        if len(words) == 0:
            self.emit(SIGNAL("wantText"))
        else:
            #sort mistakes to beginning
            words.sort(key=lambda x: (x[4], x[1]), reverse=True)
            i = 0
            while words[i][4] != 0:
                i += 1
            #addon some non mistakes
            if i < (len(words) -1 // 8):
                i = (len(words) - 1) // 8
                i = i + 1
            wordLessons = map(lambda x: x[6], words[0:i])

            phrases = filter(lambda x: x[5] == 3, vals)
            phrases.sort(key=lambda x: (x[1], x[4]), reverse=True)
            i = len(wordLessons)
            phraseLessons = map(lambda x: x[6], phrases[0: i])
            self.emit(SIGNAL("wantReview"), wordLessons + phraseLessons)

    def lessThanSpeed(self):
        return self.typer.getSpeed() < self.getMinimums()[0]

    def lessThanAccuracy(self):
        return self.typer.getAccuracy() < (self.getMinimums()[1])/100.0

    def isLesson(self):
        is_lesson = DB.fetchone("select discount from source where rowid=?", (None, ), (self.text[1], ))[0]
        return is_lesson

    def getMinimums(self):
        if self.isLesson():
            minimums = (Settings.get("min_lesson_wpm"), Settings.get("min_lesson_acc"))
        else:
            minimums = (Settings.get("min_wpm"), Settings.get("min_acc"))
        return minimums

    def AddSymbols(self, text):
        text = ' '.join(self.modifiedWord(word) for word in text.split(' '))
        text = text.strip()
        return text

    # the cache makes each modified text determintistic, in that if you do the same text over and over, it will have the same random elements added.
    # this is useful for building up speed on selection of text
    def modifiedWord(self, word):
        global wordCache
        if not word in wordCache:
            symbols = random.choice(Settings.get('include_symbols').split(" "));
            if (not any((c in Settings.get('stop_symbols')) for c in word)) and (len(word) > 1) and (Settings.get('title_case')) and (Settings.get('symbols')):
                wordCache[word] = symbols.replace("0",(word[0].capitalize() + word[1:]))
            elif(not any((c in Settings.get('stop_symbols')) for c in word)) and (len(word) > 1) and (Settings.get('symbols')):
                wordCache[word] = symbols.replace("0",word )
            elif(not any((c in Settings.get('stop_symbols')) for c in word)) and (len(word) > 1) and (Settings.get('title_case')):
                wordCache[word] = word[0].capitalize() + word[1:]
            else:
                wordCache[word] = word
        return wordCache[word]
