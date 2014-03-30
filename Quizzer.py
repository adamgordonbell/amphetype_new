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


from __future__ import with_statement, division

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

#minimum time we assume to take to count char (to prevent division by zero)
MINIMUM_CHAR_TYPING_TIME = 0.000001     #equivalent to 3333.33wpm 

if platform.system() == "Windows":
    # hack hack, hackity hack
    timer = time.clock
    timer()
else:
    timer = time.time

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
    for i in range(min(len(s),len(t))):
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
            for i in range(1,non_interpolation_dist):
                #interpolates over previous zeroes
                yield last_non_interpolation + i*average_change
            yield e
        non_interpolation_dist = 0
        last_non_interpolation = e
   
def new_error(position,errors):
    '''Given list of error positions and current position, 
returns whether or there's a new error at position'''
    #considers adjacent errors to be part of the same error
    return position in errors and position - 1 not in errors
    
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
    for i in range(len(li)-1,-1,-1): 
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

        self.connect(self, SIGNAL("textChanged()"), lambda: self.emit(SIGNAL("textChanged")))
        #self.setLineWrapMode(QTextEdit.NoWrap)
        set_palette_change_signals = [ "quiz_wrong_fg", "quiz_wrong_bg","quiz_wrong_bd", "quiz_right_fg",
                                       "quiz_right_bg","quiz_right_bd", "quiz_invisible_color", "quiz_invisible_bd",
                                       "quiz_inactive_fg", "quiz_inactive_bg","quiz_inactive_bd", "quiz_inactive_hl",
                                       "quiz_inactive_hl_text", 'quiz_use_wrong_palette']
        
        for change_signal in set_palette_change_signals:
            self.connect(Settings, SIGNAL("change_{0}".format(change_signal)), self.setPalettes)

        self.target = None
        self.started = False

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

    def setTarget(self,  text):
        self.editflag = True
        self.target = text
        self.when = [None] * (len(self.target)+1)
        self.times = [0] * len(self.target)
        self.mistake = [False] * len(self.target)
        self.mistakes = {} #collections.defaultdict(lambda: [])
        self.farthest_correct = 0
        self.clear()
        self.setPalette(self.palettes['inactive'])
        self.setText(self.getWaitText())
        self.selectAll()
        self.editflag = False
        self.started = False

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
        #TODO: redo when, times to avoid guessing time taken to hit zeroth char from old stat
        if self.when[0] == -1:
            t = self.times[1:]
            t.sort(reverse=True)
            v = DB.fetchone('select time from statistic where type = 0 and data = ? order by rowid desc limit 1', (t[len(t)//5], ), (self.target[0], ))
            self.when[0] = self.when[1] - v[0]

        if not self.when[-1]:
            self.when[-1] = timer()

        self.when = list(linearly_interpolate(self.when))
        
        for i in range(len(self.times)):
            #prevent division by zero when 0 time 
            time = self.when[i+1] - self.when[i]
            self.times[i] = MINIMUM_CHAR_TYPING_TIME if time == 0 else time   

        return self.when[-1]-self.when[0], len(self.target), self.times, self.mistake, self.getMistakes()

    def activate_invisibility(self):
        '''Turns on invisible mode'''
        self.setPalette(self.palettes['invisible'])
        set_colored_typer_text(self,Settings.get('quiz_invisible_color'))  #flushes out html with plaintext

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

    def checkText(self):
        if self.typer.target is None or self.typer.editflag:
            return

        v = unicode(self.typer.toPlainText())
        
        if Settings.get('allow_mistakes') and len(v) >= len(self.typer.target):
            v = self.typer.target

        if not self.typer.started:
            if Settings.get('req_space'):
            #space is required before beginning the passage proper
                if v == u" ":
                    #the first char typed was space
                    #the first space only starts the session; clear the typer
                    set_typer_text(self.typer,"",cursor_position=0)
                    self.typer.when[0] = timer()
                    self.typer.started = True
                    return
                else:
                    #reset the wait text
                    set_typer_text(self.typer,self.typer.getWaitText())
                    self.typer.selectAll()
                    return
            else:
                self.typer.when[0] = -1
                self.typer.when[1] = timer()  #have to set starting time regardless of correctness
                self.typer.started = True

        old_cursor = self.typer.textCursor()
        old_position = old_cursor.position()
        old_str_position = old_position - 1  #the position that has (presumably) just been typed
     
        #colors text in typer depending on errors
        errors = disagreements(v,self.typer.target,case_sensitive=Settings.get('case_sensitive'))
        first_error = errors[0] if errors else None

        #records time that any char was correctly hit
        #except that if we've already been correct farther, we don't record
        if self.typer.farthest_correct < old_str_position < len(self.typer.target) and not old_str_position in errors:
            self.typer.when[old_str_position+1] = timer() #zeroth position is original space
            self.typer.farthest_correct = old_str_position

        automatic_insertion_regex = generate_automatic_insertion_regex()
        #TODO: refactor so this doesn't rely on text setting then re-calling gimmick
        #TODO: change statistics to account for this
        #Automatically insert characters into the text area
        if automatic_insertion_regex and old_position == len(v): #only works if cursor is at the end
            automatic_insertion = re.match(automatic_insertion_regex,self.typer.target[old_position:])
            if automatic_insertion:
                new_end = old_position + automatic_insertion.end()
                set_typer_text(self.typer, v[:old_position] + self.typer.target[old_position:new_end], cursor_position = new_end)
                self.checkText()  #recovers the formatting
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
