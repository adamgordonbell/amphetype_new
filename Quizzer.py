# -*- coding: UTF-8 -*-

#Changelog
#March 19 2014: 
#  * Added template for changing color of letters in typer and label
#    depending on errors and position [lalop]
#March 20 2014:
#  * Fixed template for allowing one to finish despite mistakes. [lalop]
#  * Interpolation between any missing times (hopefully solves gen_tup's
#    division by zero) [lalop]

from __future__ import with_statement, division

ALLOW_MISTAKES = True

LABEL_NORMAL_TEXT_COLOR = "#777777"
LABEL_TEXT_POSITION_COLOR = "green"
LABEL_TEXT_POSITION_WITH_MISTAKE_COLOR = "green"
LABEL_MISTAKES_COLOR = "#a43434"

TEXT_AREA_MISTAKES_COLOR = "#a43434"
TEXT_AREA_REPLACE_SPACES = False

SPACE_REPLACEMENT = "&#8729;"

#import psyco
import platform
import collections
import time
import re

from Data import Statistic, DB
from Config import Settings

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
    
def interpolate_zeroes(iterable):
    '''l is a iterable of numbers with first value nonzero and either:
1. Last value nonzero (if terminating)
2. No upper bound on nonzeroes (if non-terminating)

Nondestructively: replaces any sequences of zeroes in nums with
averaged values interpolated from the nonzeroes immediately before
and after it

e.g. interpolate_zeroes([3,5,7,0,0,0,0,8,9,0,0,5,0,0,0,0,10,0,12,18,-5]) = 
        iterator generating: 3, 5, 7, 7.2, 7.4, 7.6, 7.8, 8, 9,
                             7.666666666666667, 6.333333333333334,
                             5, 6.0, 7.0, 8.0, 9.0, 10, 11.0, 12, 18, -5'''
    it = iter(iterable)
    nonzero_dist = 0      #dist since last nonzero
    last_nonzero = None   #what that last nonzero was
    for e in it:
        if e == 0:
            nonzero_dist += 1
            continue
        elif nonzero_dist == 0:
            #no previous zeroes to interpolate over, return value
            yield e
        else:
            nonzero_dist += 1
            average_change = 1.0*(e-last_nonzero)/nonzero_dist
            for i in range(1,nonzero_dist):
                #interpolates over previous zeroes
                yield last_nonzero + i*average_change
            yield e
        nonzero_dist = 0
        last_nonzero = e

def new_error(position,errors):
    '''Given list of error positions and current position, 
returns whether or there's a new error at position'''
    #considers adjacent errors to be part of the same error
    return position in errors and position - 1 not in errors

class Typer(QTextEdit):
    def __init__(self, *args):
        super(Typer, self).__init__(*args)

        self.setPalettes()

        self.connect(self, SIGNAL("textChanged()"), lambda: self.emit(SIGNAL("textChanged")))
        #self.setLineWrapMode(QTextEdit.NoWrap)
        self.connect(Settings, SIGNAL("change_quiz_wrong_fg"), self.setPalettes)
        self.connect(Settings, SIGNAL("change_quiz_wrong_bg"), self.setPalettes)
        self.connect(Settings, SIGNAL("change_quiz_right_fg"), self.setPalettes)
        self.connect(Settings, SIGNAL("change_quiz_right_bg"), self.setPalettes)
        self.target = None

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

    def setTarget(self,  text):
        self.editflag = True
        self.target = text
        self.when = [0] * (len(self.target)+1)
        self.times = [0] * len(self.target)
        self.mistake = [False] * len(self.target)
        self.mistakes = {} #collections.defaultdict(lambda: [])
        self.where = 0
        self.clear()
        self.setPalette(self.palettes['inactive'])
        self.setText(self.getWaitText())
        self.selectAll()
        self.editflag = False

    def getWaitText(self):
        if Settings.get('req_space'):
            return "Press SPACE and then immediately start typing the text\n" + \
                    "Press ESCAPE to restart with a new text at any time"
        else:
            return "Press ESCAPE to restart with a new text at any time"

    def getMistakes(self):
        inv = collections.defaultdict(lambda: 0)
        for p, m in self.mistakes.iteritems():
            inv[m] += 1
        return inv

    def getStats(self):
        if self.when[0] == -1:
            t = self.times[1:]
            t.sort(reverse=True)
            v = DB.fetchone('select time from statistic where type = 0 and data = ? order by rowid desc limit 1', (t[len(t)//5], ), (self.target[0], ))
            self.times[0] = v[0]
            self.when[0] = self.when[1] - self.times[0]
            self.when = list(interpolate_zeroes(self.when))
            for i in range(1,len(self.times)):
                self.times[i] = self.when[i] - self.when[i-1]
        return self.when[self.where]-self.when[0], self.where, self.times, self.mistake, self.getMistakes()

class Quizzer(QWidget):
    def __init__(self, *args):
        super(Quizzer, self).__init__(*args)

        self.result = QLabel()
        self.typer = Typer()
        self.label = WWLabel()
        self.result.setVisible(Settings.get("show_last"))
        #self.label.setFrameStyle(QFrame.Raised | QFrame.StyledPanel)
        #self.typer.setBuddy(self.label)
        #self.info = QLabel()
        self.connect(self.typer,  SIGNAL("done"), self.done)
        self.connect(self.typer,  SIGNAL("textChanged"), self.checkText)
        self.connect(self.typer,  SIGNAL("cancel"), SIGNAL("wantText"))
        self.connect(Settings, SIGNAL("change_typer_font"), self.readjust)
        self.connect(Settings, SIGNAL("change_show_last"), self.result.setVisible)

        self.text = ('','', 0, None)

        layout = QVBoxLayout()
        #layout.addWidget(self.info)
        #layout.addSpacing(20)
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
        
        if ALLOW_MISTAKES and len(v) >= len(self.typer.target):
            v = self.typer.target

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

        if lcd == self.typer.target:
            self.done()
            return
       
        old_cursor = self.typer.textCursor()
        old_position = old_cursor.position()
        old_str_position = old_position - 1  #the position that has (presumably) just been typed
     
        #colors text in typer depending on errors
        errors = disagreements(v,self.typer.target)
        
        if new_error(old_str_position,errors): 
            self.typer.mistake[old_str_position] = True
            self.typer.mistakes[old_str_position] = self.typer.target[old_str_position] + v[old_str_position]

        if errors:
            self.typer.setPalette(self.typer.palettes['wrong'])
        else:
            self.typer.setPalette(self.typer.palettes['right'])
  
        v_err_replacements = {"\n":"&#8629;"}
        if TEXT_AREA_REPLACE_SPACES:
            #if want to make replacements change spaces in text area as well (risky!)
            v_err_replacements[" "] = SPACE_REPLACEMENT

        error_colors = dict(map(lambda d : (d,TEXT_AREA_MISTAKES_COLOR),errors))
        v_replaced_list = replace_at_locs(list(v),v_err_replacements,errors)
        v_colored_list = html_color_letters(v_replaced_list,error_colors)
        htmlized = "".join(v_colored_list).replace("\n","<BR>")

        self.typer.editflag = True
        self.typer.setHtml(htmlized)
        old_cursor.setPosition(old_position)
        self.typer.setTextCursor(old_cursor)
        self.typer.editflag = False
        
        #updates the label depending on errors
        self.updateLabel(old_position,errors)

    def readjust(self):
        f = Settings.getFont("typer_font")
        f.setKerning(False)
        #todo: get rid of "vertical kerning"
        # not f.setFixedPitch(True)
        self.label.setFont(f)
        self.typer.setFont(f)

    def setText(self, text):
        self.text = text 
        self.label.setText(self.text[2].replace(u"\n", u"↵\n"))
        self.typer.setTarget(self.text[2])
        self.typer.setFocus()

    def done(self):
        now = time.time()
        elapsed, chars, times, mis, mistakes = self.typer.getStats()

        assert chars == len(self.text[2])

        accuracy = 1.0 - len(filter(None, mis)) / chars
        spc = elapsed / chars
        viscosity = sum(map(lambda x: ((x-spc)/spc)**2, times)) / chars

        DB.execute('insert into result (w,text_id,source,wpm,accuracy,viscosity) values (?,?,?,?,?,?)',
                   (now, self.text[0], self.text[1], 12.0/spc, accuracy, viscosity))

        v2 = DB.fetchone("""select agg_median(wpm),agg_median(acc) from
            (select wpm,100.0*accuracy as acc from result order by w desc limit %d)""" % Settings.get('def_group_by'), (0.0, 100.0))
        self.result.setText("Last: %.1fwpm (%.1f%%), last 10 average: %.1fwpm (%.1f%%)"
            % ((12.0/spc, 100.0*accuracy) + v2))

        self.emit(SIGNAL("statsChanged"))

        stats = collections.defaultdict(Statistic)
        visc = collections.defaultdict(Statistic)
        text = self.text[2]

        for c, t, m in zip(text, times, mis):
            stats[c].append(t, m)
            visc[c].append(((t-spc)/spc)**2)

        def gen_tup(s, e):
            perch = sum(times[s:e])/(e-s)
            visc = sum(map(lambda x: ((x-perch)/perch)**2, times[s:e]))/(e-s)
            return (text[s:e], perch, len(filter(None, mis[s:e])), visc)

        for tri, t, m, v in [gen_tup(i, i+3) for i in xrange(0, chars-2)]:
            stats[tri].append(t, m > 0)
            visc[tri].append(v)

        regex = re.compile(r"(\w|'(?![A-Z]))+(-\w(\w|')*)*")

        for w, t, m, v in [gen_tup(*x.span()) for x in regex.finditer(text) if x.end()-x.start() > 3]:
            stats[w].append(t, m > 0)
            visc[w].append(v)

        def type(k):
            if len(k) == 1:
                return 0
            elif len(k) == 3:
                return 1
            return 2

        vals = []
        for k, s in stats.iteritems():
            v = visc[k].median()
            vals.append( (s.median(), v*100.0, now, len(s), s.flawed(), type(k), k) )

        is_lesson = DB.fetchone("select discount from source where rowid=?", (None,), (self.text[1], ))[0]

        if Settings.get('use_lesson_stats') or not is_lesson:
            DB.executemany_('''insert into statistic
                (time,viscosity,w,count,mistakes,type,data) values (?,?,?,?,?,?,?)''', vals)
            DB.executemany_('insert into mistake (w,target,mistake,count) values (?,?,?,?)',
                    [(now, k[0], k[1], v) for k, v in mistakes.iteritems()])

        if is_lesson:
            mins = (Settings.get("min_lesson_wpm"), Settings.get("min_lesson_acc"))
        else:
            mins = (Settings.get("min_wpm"), Settings.get("min_acc"))

        if 12.0/spc < mins[0] or accuracy < mins[1]/100.0:
            self.setText(self.text)
        elif not is_lesson and Settings.get('auto_review'):
            ws = filter(lambda x: x[5] == 2, vals)
            if len(ws) == 0:
                self.emit(SIGNAL("wantText"))
                return
            ws.sort(key=lambda x: (x[4],x[0]), reverse=True)
            i = 0
            while ws[i][4] != 0:
                i += 1
            i += (len(ws) - i) // 4

            self.emit(SIGNAL("wantReview"), map(lambda x:x[6], ws[0:i]))
        else:
            self.emit(SIGNAL("wantText"))
