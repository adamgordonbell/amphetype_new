# -*- coding: UTF-8 -*-
# This file is part of Amphetype.

# Amphetype is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Amphetype is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Amphetype.  If not, see <http://www.gnu.org/licenses/>.

# Changelog
# March 19 2014: 
#   * Added template for changing color of letters in typer and label
#     depending on errors and position [lalop]
# March 20 2014:
#   * Fixed template for allowing one to finish despite mistakes. [lalop]
#   * Interpolation between any missing times (hopefully solves gen_tup's
#     division by zero) [lalop]
# March 21 2014:
#   * Integrated with settings [lalop]:
#       1. Most of the special text color/usage options (not working: the
#          "base" color)
#       2. The option for finishing despite mistakes
#       3. Space and return character replacements
#   * Added invisible mode, integrated with settings [lalop]
# March 22 2014:
#  * Added and integrated with settings [lalop]:
#       1. Typer border color
#       2. Inactive palette highlight foreground & background
#       3. Option not to use "wrong" palette
# March 23 2014:
#  * (Hopefully) can now use multiple adjacent spaces in typer and label [lalop]
# March 24 2014:
#  * Refactored, fixed some bugs with invisible text and double spaces [lalop]
# March 26 2014:
#  * Added and integrated with settings [lalop]:
#        1. label position color with adjacent prior mistake
#        2. independent options for space char on the different position colors
# March 27 2014:
#  * Added and integrated with settings: template for continuing to the next word
#    only when space correctly pressed [lalop]
# March 28 2014:
#  * Added and integrated with settings [lalop]:
#        1. Case sensitivity
#        2. Template for automatically inserting certain chars in the text area
# April 4 2014:
#  * Redid stats [lalop]:
#        1. Starting space is now ignored (rather than fudged if not existing)
#        2. Automatically completed chars are now ignored. An optimistic 
#           stat estimate (one that assumes the user completed them correctly
#           and instantaneously) is also shown
# April 5 2014:
#  * Added and integrated with settings option to count adjacent errors as part
#    of the same error [lalop]


from __future__ import with_statement, division

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

#minimum time we assume to take to count char (to prevent division by zero)
MINIMUM_CHAR_TYPING_TIME = 0.000001     #equivalent to 3333.33wpm 
MINIMUM_ELAPSED_TIME = 0.0001 
if platform.system() == "Windows":
    # hack hack, hackity hack
    timer = time.clock
    timer()
else:
    timer = time.time

class Letter(object):
    "Letter data"
    def __init__(self, char, when = None, automatically_inserted = False):
        self.char = char
        self.when = when
        self.automatically_inserted = automatically_inserted

def generate_automatic_insertion_regex():
    '''From settings info, returns the regex for which to re.match the automatically inserted chars

Or None if no chars are to be automatically inserted.'''
    #the str of characters (in regex-escaped form, but not regex) to automatically insert
    automatically_inserted_chars = ""
    if Settings.get('use_automatic_other_insertion'):
        automatically_inserted_chars += re.escape(Settings.get('automatic_other_insertion'))
    for s,c in ('automatic_space_insertion',u" "),('automatic_return_insertion',u"\n"):
        if Settings.get(s):
            automatically_inserted_chars += re.escape(c)

    return "[{0}]+".format(automatically_inserted_chars) if automatically_inserted_chars else None

def html_font_color(color,string):
    '''Returns html unicode string representing string with font color color'''
    return u'<font color="{0}">{1}</font>'.format(color,string)

def html_color_strs(strs,new_colors,default_color=None):
    '''strs is list of typically 1 character strings from doing list(string) 

new_colors is a dict : positions (int) -> colors as accepted by html

Non-destructively returns strs with the positions of new_colors changed to the new colors in html'''
    def colorize(i,s):
        color_s = lambda c : s if c == None else html_font_color(c,s)
        if i in new_colors:
            return color_s(new_colors[i])
        else:
            return color_s(default_color)

    return [colorize(i,s) for i,s in enumerate(strs)]

def replace_at_locs(strs,replacements,locations = None):
    '''strs is list of typically 1 character strings from doing list(string) 
    
replacements is a dict : str -> str, interpreted as source -> replacement
    
locations is a list of ints.  If location is None (not to be confused with []), assume allow all locations. 

Non-destructively: in each index of locations, if the string at that index is in replacements,
replaces it.  Otherwise, leaves it.'''
    def replace_at_locs_a(i,s):
        if locations != None and i not in locations or s not in replacements:
            return s
        else:
            return replacements[s]

    return [replace_at_locs_a(i,s) for i,s in enumerate(strs)]
    
def disagreements(s,t,case_sensitive=True,full_length=False):
    '''List (in ascending order) of all disagreement positions between strings s and t
    
    (s and t can also be lists as long as case_sensitive==True)
    
    case_sensitive: whether or not this check is case sensitive

    full_length: whether or not to check the full length, or stop at the shorter of the two'''
    dlist = []
    if not case_sensitive:
        s = s.lower()
        t = t.lower()
    for i in xrange(min(len(s),len(t))):
        if s[i] != t[i]:
            dlist.append(i)

    return dlist

def linearly_interpolate(iterable,interpolate_element = lambda i,e : e is None):
    '''iterable is a iterable of numbers, some of which we want to interpolate. 
Its first value must be non-interpolating and either:
1. Last value non-interpolating (if terminating)
2. No upper bound on non-interpolatings (if non-terminating)

Nondestructively: replaces any sequences of interpolatables in nums with
averaged values interpolated from the non-interpolated immediately before
and after it
    
interpolate_element : Ints x Numbers -> Boolean is a function used to determine which ones to interpolate.
It will de called via interpolate_element(index of element e,element e)

The numbers that should be interpolated are those numbers e, at index i for which interpolate_element(i,e) == True

e.g. linearly_interpolate([3,5,7,None,None,None,None,8,9,None,None,5,None,None,None,None,10,None,12,18,-5]) = 
        iterator generating: 3, 5, 7, 7.2, 7.4, 7.6, 7.8, 8, 9,
                             7.666666666666667, 6.333333333333334,
                             5, 6.0, 7.0, 8.0, 9.0, 10, 11.0, 12, 18, -5'''
    non_interpolation_dist = 0      #dist since last non_interpolation
    last_non_interpolation = None   #what that last non_interpolation was
    for i,e in enumerate(iterable):
        if interpolate_element(i,e):
            non_interpolation_dist += 1
            continue
        elif non_interpolation_dist == 0:
            #no previous elements to interpolate over, return value
            yield e
        else:
            non_interpolation_dist += 1
            average_change = 1.0*(e-last_non_interpolation)/non_interpolation_dist
            for i in xrange(1,non_interpolation_dist):
                #interpolates over previous zeroes
                yield last_non_interpolation + i*average_change
            yield e
        non_interpolation_dist = 0
        last_non_interpolation = e
   
def new_error(position,errors):
    '''Given list of error positions and current position, 
returns whether or there's a new error at position'''
    #considers adjacent errors to be part of the same error if the setting is toggled
    return position in errors and not (Settings.get('adjacent_errors_not_counted') and position - 1 in errors)
    
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

def set_typer_text(typer, text = None, func = None, cursor_position = None):    

    '''Given a Typer, sets its text content to text, matching old cursor position.
    
If text not specified, the plain text (to unicode) from the typer is used.  This can, e.g. clear html.

If func specified, uses that function for the text setting.  Otherwise, uses typer.setPlainText'''
    if text == None:
        text = unicode(typer.toPlainText()) 
        
    if func == None:
        func = typer.setPlainText

    #edits the html string into the text area, corrects cursor position
    old_cursor = typer.textCursor()
    old_position = old_cursor.position() if cursor_position is None else cursor_position

    typer.editflag = True
    func(text)
    old_cursor.setPosition(old_position)
    typer.setTextCursor(old_cursor)
    typer.editflag = False

def set_colored_typer_text(typer,color,text = None): 
    '''Given text to be set with color color (in RGB format, e.g. #112233), sets it'''
    def text_setter(t):
        '''Sets unicode text t as html with color color'''
        t_list = list(t)
        t_list = html_list_process_spaces(t_list)
        typer.setHtml(html_font_color(color,"".join(t_list).replace("\n","<BR>")))
    set_typer_text(typer, text, func = text_setter)

def set_typer_html(typer,html):
    '''Given a Typer, sets its html content to html, matching old cursor position.'''
    set_typer_text(typer, html, func = typer.setHtml)
    
def html_list_process_spaces(li, breaking_replacement = " ", non_breaking_replacement = "&nbsp;"):
    '''Given a list li of (to be) html character strings, process the spaces.

default breaking_replacement is " ", non_breaking replacement is "&nbsp;

    
First, adjacent spaces, e.g. "     " are replaced 

with breaking and non-breaking spaces, e.g. " &nbsp; &nbsp; ".  The last space in any such sequence is
breaking (to avoid it being word-wrapped as the first char on a line).


If the first char is a breaking space, replaces it with non-breaking space."'''
    #None if not in sequence, True if current space in sequence should be breaking,
    #False if current space in sequence should be non-breaking
    breaking = None 
    result = list(li)
    for i in xrange(len(li)-1,-1,-1): 
        #loops backward to ensure last space in any sequence is non-breaking
        if breaking == None:
            #check if we're at the start (i.e. the highest index of) of a sequence
            if i > 0 and result[i] == result[i-1] == " ":
                result[i] = breaking_replacement
                breaking = False
        elif result[i] == " ":
            #we're in a sequence, make the appropriate replacement
            result[i] = breaking_replacement if breaking else non_breaking_replacement
            breaking = not breaking  
        else:
            #exited a sequence
            breaking = None
    
    if len(result) > 0 and result[0] == breaking_replacement:
        result[0] = non_breaking_replacement
    return result

def space_replacement_dict(replacement):
    '''Returns a dict that assigns to html spaces the value replacement'''
    return {" ":replacement,"&nbsp;":replacement}

def space_replacement_dict_from_setting(replacement_var):
    '''Returns a dict that assigns to html spaces the value in the setting replacement_var'''
    return space_replacement_dict(Settings.get(replacement_var))

def update_typer_html(typer,errors):
    '''Organizational function.

Given a Typer, updates its html based on settings (not including invisible mode)'''
    #dict : str -> str ; original and displacement strs in error region (for easier display)
    v = unicode(typer.toPlainText())
    v_err_replacements = {}
    if Settings.get('text_area_replace_spaces'):
        #if want to make replacements change spaces in text area as well (risky!)
        v_err_replacements.update(space_replacement_dict_from_setting('text_area_mistakes_space_char'))
        
    if Settings.get('text_area_replace_return'):
        #want to make replacements change returns in text area as well (a little less risky since there's usually fewer)
        v_err_replacements["\n"] = Settings.get('text_area_return_replacement')
    
    error_colors = {} #dict : int -> str, mapping errors to color
    v_replaced_list = list(v)  #list of strs, initially one char each, to operate on
    v_replaced_list = html_list_process_spaces(v_replaced_list)

    if Settings.get("show_text_area_mistakes"):
        error_colors = dict(map(lambda i : (i,Settings.get('text_area_mistakes_color')),errors))
        v_replaced_list = replace_at_locs(v_replaced_list,v_err_replacements,errors)

    v_colored_list = html_color_strs(v_replaced_list,error_colors)
    htmlized = "".join(v_colored_list).replace("\n","<BR>")
    set_typer_html(typer,htmlized)
    
class Typer(QTextEdit):
    def __init__(self, *args):
        super(Typer, self).__init__(*args)

        self.setPalettes()
        self.permissive = Settings.get("permissive_errors")
        self.connect(self, SIGNAL("textChanged()"), lambda: self.emit(SIGNAL("textChanged")))
        #self.setLineWrapMode(QTextEdit.NoWrap)
        set_palette_change_signals = [ "quiz_wrong_fg", "quiz_wrong_bg","quiz_wrong_bd", "quiz_right_fg",
                                       "quiz_right_bg","quiz_right_bd", "quiz_invisible_color", "quiz_invisible_bd",
                                       "quiz_inactive_fg", "quiz_inactive_bg","quiz_inactive_bd", "quiz_inactive_hl",
                                       "quiz_inactive_hl_text", 'quiz_use_wrong_palette']
        
        for change_signal in set_palette_change_signals:
            self.connect(Settings, SIGNAL("change_{0}".format(change_signal)), self.setPalettes)

        if Settings.get("invisible_mode"):
            self.setTextColor(QColor(Qt.white))
            self.setTextBackgroundColor(QColor(Qt.white))
            self.setCursorWidth(0)
        self.target = None
        self.when = None
        self.start_time = None  #start time; None (if not started), 0 (if started but unset) or float
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
        inactive_palette = QPalette(Qt.black,
                Settings.getColor("quiz_inactive_bd"), Qt.lightGray, Qt.darkGray, Qt.gray,
                Settings.getColor("quiz_inactive_fg"), Qt.yellow, Settings.getColor("quiz_inactive_bg"), Qt.yellow)

        inactive_palette.setColor(QPalette.Highlight, Settings.getColor("quiz_inactive_hl"))
        inactive_palette.setColor(QPalette.HighlightedText, Settings.getColor("quiz_inactive_hl_text"))
        self.palettes = {
            'wrong': QPalette(Qt.black,
                Settings.getColor("quiz_wrong_bd"), Qt.lightGray, Qt.darkGray, Qt.gray,
                Settings.getColor("quiz_wrong_fg"), Qt.white, Settings.getColor("quiz_wrong_bg"), Qt.yellow),
            'right': QPalette(Qt.black,
                Settings.getColor("quiz_right_bd"), Qt.lightGray, Qt.darkGray, Qt.gray,
                Settings.getColor("quiz_right_fg"), Qt.yellow, Settings.getColor("quiz_right_bg"), Qt.yellow),
            'invisible': QPalette(Qt.black,
                Settings.getColor("quiz_invisible_bd"), Qt.lightGray, Qt.darkGray, Qt.gray,
                Settings.getColor("quiz_invisible_color"), Qt.yellow, Settings.getColor("quiz_invisible_color"), Qt.yellow),
            'inactive':inactive_palette }
        self.setPalette(self.palettes['inactive']) 

    def setTarget(self, text, guid):
        self.editflag = True
        self.target = text
        self.data = [None]* (len(self.target))

        # time for each character typed

        # whether each character was a mistake
        self.mistake = [False] * len(self.target)

        # mistake characters ( must be what was actually typed )
        self.mistakes = {} #collections.defaultdict(lambda: [])
        self.farthest_correct = -1
        self.farthest_data = -1
        self.clear()
        self.setPalette(self.palettes['inactive'])
        self.setText(self.getWaitText())
        self.selectAll()
        self.editflag = False
        self.is_lesson = DB.fetchone("select discount from source where rowid=?", (None, ), (guid, ))[0]
        self.start_time = None
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
        # from lalop
        #return self.when[-1]-self.when[0]
        return self.when[self.where]-self.when[0]

    def getStats(self):
        user_entered_data = filter(lambda letter : letter and not letter.automatically_inserted, self.data)
        when = list(linearly_interpolate(letter.when for letter in user_entered_data)) 
            # my refactoring mean this may never get hit, I'm not sure what when and times are for, so i'm not sure if I'm breaking some edge case here??
        
        times = []
        for i in xrange(len(when)-1):
            #prevent division by zero when 0 time 
            time = when[i+1] - when[i]
            times.append(max(time, MINIMUM_CHAR_TYPING_TIME))
     
        typed_text = "".join([l.char for l in user_entered_data])

        end_time = when[-1]
        time_elapsed = max(end_time - self.start_time, MINIMUM_ELAPSED_TIME)
        #from agbell
        #return self.getElapsed(), self.where, self.times, self.mistake, self.getMistakes()
            
        return time_elapsed, typed_text, len(typed_text), times, self.mistake, self.getMistakes()
        
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
        
    def activate_invisibility(self):
        '''Turns on invisible mode'''
        self.setPalette(self.palettes['invisible'])
        set_colored_typer_text(self,Settings.get('quiz_invisible_color'))  #flushes out html with plaintext

class Quizzer(QWidget):
    def __init__(self, *args):
        super(Quizzer, self).__init__(*args)

        self.result = QLabel()
        self.result.setAlignment(Qt.AlignRight)
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
        '''Populates the label with colors depending on current position and errors.'''
        #dict : str -> str ; original and displacement strs in error region (for easier display)
        err_replacements = {"\n":u"{0}<BR>".format(Settings.get('label_return_symbol'))}

        colors = {}  #dict : int -> str, mapping errors to color
        
        if Settings.get('show_label_mistakes'):
            #showing mistakes; need to populate color
            colors = dict([(i,Settings.get('label_mistakes_color')) for i in errors])

            if Settings.get('label_replace_spaces_in_mistakes'):
                err_replacements.update(space_replacement_dict_from_setting('label_mistakes_space_char'))

        text_strs = list(self.text[2]) #list of strs, initially one char each, to operate on
        text_strs = html_list_process_spaces(text_strs)
        text_strs = replace_at_locs(text_strs,err_replacements,errors)

        def color_position(settings_color_var, use_space_var, space_var):
            '''Colors position with the color stored in settings_color_var.
            
strs use_space_var and space_var are settings variables to look up.
If [setting] use_space_var, space at position is replaced with [setting] space_var

Returns the new text_strs list (for assignment).'''
            colors[position] = Settings.get(settings_color_var)

            if Settings.get(use_space_var):
                return replace_at_locs(text_strs,space_replacement_dict_from_setting(space_var),[position])
            else:
                return text_strs
            
        #designates colors and replacements of position
        if Settings.get('show_label_position_with_prior_mistake') and position - 1 in errors:
            text_strs = color_position('label_position_with_prior_mistake_color',
                                       'label_replace_spaces_in_position_with_prior_mistake',
                                       'label_position_with_prior_mistake_space_char')
        elif Settings.get('show_label_position_with_mistakes') and errors:
            text_strs = color_position('label_position_with_mistakes_color',
                                       'label_replace_spaces_in_position_with_mistakes',
                                       'label_position_with_mistakes_space_char')
        elif Settings.get('show_label_position'): 
            text_strs = color_position('label_position_color',
                                       'label_replace_spaces_in_position',
                                       'label_position_space_char') 

        htmlized = "".join(html_color_strs(text_strs,colors))
        htmlized = htmlized.replace(u"\n", u"{0}<BR>".format(Settings.get('label_return_symbol')))
        
        self.label.setText(htmlized) 

    def checkText(self, automatically_inserted = False):
        if self.typer.target is None or self.typer.editflag:
            return

        v = unicode(self.typer.toPlainText())
        
        if Settings.get('allow_mistakes') and len(v) >= len(self.typer.target):
            v = self.typer.target

        if self.typer.start_time == None and Settings.get('req_space'):
            #space is required before beginning the passage proper
            if v == u" ":
                #the first char typed was space
                #the first space only starts the session; clear the typer
                set_typer_text(self.typer,"",cursor_position=0)
                self.typer.start_time = 0
                return
            else:
                #reset the wait text
                set_typer_text(self.typer,self.typer.getWaitText())
                self.typer.selectAll()
                return
                
        if not self.typer.start_time:
            self.typer.start_time = timer()

        old_cursor = self.typer.textCursor()
        old_position = old_cursor.position()
        old_str_position = old_position - 1  #the position that has (presumably, unless delete was used) just been typed
     
        #colors text in typer depending on errors
        errors = disagreements(v,self.typer.target,case_sensitive=Settings.get('case_sensitive'))
        first_error = errors[0] if errors else None

        #records time that any char was hit
        #except that if we've already been correct farther, we don't record
        if self.typer.farthest_correct < old_str_position < len(self.typer.target):
            if old_str_position not in errors:
                self.typer.farthest_correct = old_str_position

            #invalidates all farther-out times that might have previously been written
            if old_str_position < self.typer.farthest_data:
                for i in xrange(old_str_position+1, self.typer.farthest_data + 1):
                    self.typer.data[i].when = None

            self.typer.farthest_data = old_str_position
            self.typer.data[old_str_position] = Letter(char=self.typer.target[old_str_position],
                                                       when=timer(),
                                                       automatically_inserted=automatically_inserted)

        automatic_insertion_regex = generate_automatic_insertion_regex()
        #TODO: refactor so this doesn't rely on text setting then re-calling gimmick
        #TODO: change statistics to account for this
        #Automatically insert characters into the text area
        if automatic_insertion_regex and old_position == len(v): #only works if cursor is at the end
            automatic_insertion = re.match(automatic_insertion_regex,self.typer.target[old_position:])
            if automatic_insertion:
                new_end = old_position + automatic_insertion.end()
                set_typer_text(self.typer, v[:old_position] + self.typer.target[old_position:new_end], cursor_position = new_end)
                self.checkText(automatically_inserted=True)  #recovers the formatting
                return

        #TODO: refactor so this doesn't rely on text setting then re-calling gimmick
        #Prevent advancement until user correctly types space
        if Settings.get('ignore_until_correct_space') and self.typer.target[old_str_position] == u" " and old_str_position in errors:
            #gets rid of new character (sets as plaintext)
            set_typer_text(self.typer,v[:old_str_position] + v[old_str_position+1:],cursor_position = old_position - 1) 
            self.checkText()    #recovers the formatting 
            return

        if len(v) >= len(self.typer.target) and (not first_error or first_error >= len(self.typer.target)):
            self.done()
            return
       
        if new_error(old_str_position,errors): 
            self.typer.mistake[old_str_position] = True
            self.typer.mistakes[old_str_position] = self.typer.target[old_str_position] + v[old_str_position]

        if Settings.get('quiz_invisible'):
            self.typer.activate_invisibility()
        else:
            if Settings.get("quiz_use_wrong_palette") and errors:
                self.typer.setPalette(self.typer.palettes['wrong'])
            else:
                self.typer.setPalette(self.typer.palettes['right'])
            update_typer_html(self.typer,errors)
        
        #updates the label depending on errors
        self.updateLabel(old_position,errors)

    def readjust(self):
        f = Settings.getFont("typer_font")
        f.setKerning(False)
        #TODO: get rid of "vertical kerning"
        #  f.setFixedPitch(True) didn't work
        self.label.setFont(f)
        self.typer.setFont(f)

    def setText(self, text):
        self.text = text 
        self.label.setText(self.text[2].replace(u"\n", u"{0}\n".format(Settings.get('label_return_symbol')))) 
        tempText = self.AddSymbols(text[2])
        tempText = tempText.replace('  ', ' ')
        self.text = (text[0], text[1], tempText)

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
        accuracy = 1.0 - num_mistake_positions / chars
        wpm = 12.0/spc
        
        #function to format wpm and accuracy as a str
        results_str = lambda wpm, accuracy: "{0:.1f} wpm ({1:.1f}%)".format(wpm,accuracy)

        text_len = len(self.text[2])
        if chars == text_len:
            optimistic_message = ""
        else:
            #some chars were automated; make optimistic estimate for if the user
            #completed them all instantly and correctly
            optimistic_accuracy = 1.0 - num_mistake_positions / text_len 
            optimistic_wpm = 12.0*text_len/elapsed
            optimistic_message = " ; Upper-Bound: {0}".format(results_str(optimistic_wpm,100*optimistic_accuracy))
        stats = collections.defaultdict(Statistic)
        visc = collections.defaultdict(Statistic)
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

    def done1(self):
        now = time.time()
        assert self.typer.where == len(self.text[2])

        
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

    def getStatsAndViscosity(self, spc):
        stats = collections.defaultdict(Statistic)
        visc = collections.defaultdict(Statistic)
        text = self.text[2]
        mis = self.typer.mistake
        times = self.typer.times
        chars = self.typer.where
        
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
        return stats, visc

    def done(self):
        now = time.time()
        elapsed, text, chars, times, mis, mistakes = self.typer.getStats()

        num_mistake_positions = len(filter(None, mis))
        accuracy = 1.0 - num_mistake_positions / chars
        spc = elapsed / chars
        wpm = 12.0/spc
        
        #function to format wpm and accuracy as a str
        results_str = lambda wpm, accuracy: "{0:.1f} wpm ({1:.1f}%)".format(wpm,accuracy)

        text_len = len(self.text[2])
        if chars == text_len:
            optimistic_message = ""
        else:
            #some chars were automated; make optimistic estimate for if the user
            #completed them all instantly and correctly
            optimistic_accuracy = 1.0 - num_mistake_positions / text_len 
            optimistic_wpm = 12.0*text_len/elapsed
            optimistic_message = " ; Upper-Bound: {0}".format(results_str(optimistic_wpm,100*optimistic_accuracy))

        viscosity = sum(map(lambda x: ((x-spc)/spc)**2, times)) / chars

        DB.execute('insert into result (w,text_id,source,wpm,accuracy,viscosity) values (?,?,?,?,?,?)',
                   (now, self.text[0], self.text[1], 12.0/spc, accuracy, viscosity))

        v2 = DB.fetchone("""select agg_median(wpm),agg_median(acc) from
            (select wpm,100.0*accuracy as acc from result order by w desc limit %d)""" % Settings.get('def_group_by'), (0.0, 100.0))

        self.result.setText("Last: {0}{1}\nLast 10 average: {2}".format(results_str(wpm,100.0*accuracy),optimistic_message,results_str(*v2)))

        self.emit(SIGNAL("statsChanged"))

        stats = collections.defaultdict(Statistic)
        visc = collections.defaultdict(Statistic)

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

        vals = self.getVals(now, stats, type, visc)

        is_lesson = DB.fetchone("select discount from source where rowid=?", (None,), (self.text[1], ))[0]

        if Settings.get('use_lesson_stats') or not is_lesson:
            self.insertStats(now, vals)

        if is_lesson:
            mins = (Settings.get("min_lesson_wpm"), Settings.get("min_lesson_acc"))
        else:
            mins = (Settings.get("min_wpm"), Settings.get("min_acc"))

        # Fail cut-offs, redo
        if 12.0/spc < mins[0] or accuracy < mins[1]/100.0:
            self.setText(self.text)
        elif is_lesson and globals.pendingLessons:            
            self.emit(SIGNAL("newReview"), globals.pendingLessons.pop())        
        # create a lesson
        elif not is_lesson and Settings.get('auto_review'):
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
