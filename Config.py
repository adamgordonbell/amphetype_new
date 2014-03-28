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
# March 21 2014:
#  * Integrated with settings [lalop]:
#      1. Most of the special text color/usage options (not working: the
#         "base" color)
#      2. The option for finishing despite mistakes
#      3. Space and return character replacements
# March 22 2014:
#  * Integrated with settings [lalop]:
#       1. Typer border color
#       2. Inactive palette highlight foreground & background
#       3. Option not to use "wrong" palette
#       4. Various GUI color settings
# March 24 2014:
#  * Integrated transliteration options with settings [lalop]
# March 26 2014:
#  * Integrated with settings [lalop]:
#        1. label position color with adjacent prior mistake
#        2. independent options for space char on the different position colors
# March 27 2014:
#  * Integrated with settings: template for continuing to the next word
#    only when space correctly pressed [lalop]
# March 28 2014:
#  * Added and integrated with settings [lalop]:
#        1. Case sensitivity
#        2. Template for automatically inserting certain chars in the text area
#  * Changed default database name

from __future__ import with_statement

import cPickle
from QtUtil import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import getpass
import string

INDEX_TRANSLITERATION_DELETE = 1
INDEX_TRANSLITERATION_UNIDECODE = 2

transliteration_methods = ['No automatic method','Delete Non-Ascii'] 

#checks if unidecode available
try:
    import unidecode
    transliteration_methods.append('Unidecode')
except ImportError:
    print("Warning: unidecode (for unicode to ascii transliteration) not available.  Transliterations may be limited.")

try:
    _dbname = getpass.getuser() or "typer" 
    if '.' not in _dbname:
        _dbname += '-L.db'
except:
    _dbname = "typer-L.db"

def unicode_to_html(s):
    '''Takes a unicode string and encodes it as HTML'''
    return s.encode('ascii', 'xmlcharrefreplace')

class AmphSettings(QSettings):

    defaults = {
            "main_background_color":"#000000",
            'main_text_color':"#737375",          #old: "#777777",
            "main_text_area_color":"#626263",
            "main_borders_color":"#151515",
            "widgets_background_color":"#323232",
            "widgets_text_color":"#000000",
            "allow_mistakes":True,
            'quiz_invisible':False,
            'quiz_invisible_color':"#000000",
            "quiz_invisible_bd": "#282828", 
            "text_area_mistakes_color":"#a43434",
            "show_text_area_mistakes":True,
            "single_space_only":True,
            "text_area_mistakes_space_char":u"∙", #in html, "&#8729;", 
            "text_area_replace_spaces":False,
            'text_area_return_replacement':u"↵",
            'text_area_replace_return':True,
            'ignore_until_correct_space':False,
            'automatic_space_insertion':False,
            'automatic_return_insertion':False,
            'automatic_other_insertion':string.punctuation, 
            'use_automatic_other_insertion':False,
            'case_sensitive':True,
            "label_return_symbol":u"↵",
            "label_mistakes_space_char":u"∙", 
            "label_position_space_char":u"∙", 
            "label_position_with_mistakes_space_char":u"∙", 
            "label_position_with_prior_mistake_space_char":u"∙", 
            "label_replace_spaces_in_mistakes":True,
            "label_replace_spaces_in_position":False,
            "label_replace_spaces_in_position_with_mistakes":False,
            "label_replace_spaces_in_position_with_prior_mistake":True,
            'label_mistakes_color':"#a43434",
            'show_label_mistakes':True,
            'label_position_color':"#949475", #formerly 008000, aaaa74
            'show_label_position':True, 
            'label_position_with_mistakes_color':"#a0a000",
            'show_label_position_with_mistakes':False,
            'label_position_with_prior_mistake_color':"#00aa00",
            'show_label_position_with_prior_mistake':True,
            "typer_font": str(QFont("Arial", 14).toString()),
            "history": 30.0,
            "min_chars": 220,
            "max_chars": 600,
            "lesson_stats": 0, # show text/lesson in perf -- not used anymore
            "perf_group_by": 0,
            "perf_items": 100,
            "text_regex": r"",
            "db_name": _dbname,
            "select_method": 1,
            "num_rand": 50,
            "graph_what": 3,
            "req_space": False, 
            "show_last": True,
            "show_xaxis": False,
            "chrono_x": False,
            "dampen_graph": False,

            "minutes_in_sitting": 60.0,
            "dampen_average": 10,
            "def_group_by": 10,

            "use_lesson_stats": False,
            "auto_review": False,

            "min_wpm": 0.0,
            "min_acc": 0.0,
            "min_lesson_wpm": 0.0,
            "min_lesson_acc": 97.0,

            "quiz_right_fg": "#646464",
            "quiz_right_bg": "#000000", 
            "quiz_right_bd": "#282828", 
            "quiz_inactive_fg": "#646464",
            "quiz_inactive_bg": "#000000", 
            "quiz_inactive_bd": "#282828", 
            "quiz_inactive_hl":"#050f0a",
            "quiz_inactive_hl_text":"#2d3233",
            "quiz_use_wrong_palette":False,
            "quiz_wrong_fg": "#646464",
            "quiz_wrong_bg": "#1a0000",
            "quiz_wrong_bd": "#282828", 

            'transliteration_manual_unicode':True,
            'transliteration_method':len(transliteration_methods) - 1,
            'transliteration_manual_ascii':True,

            "group_month": 365.0,
            "group_week": 30.0,
            "group_day": 7.0,

            "ana_which": "wpm asc",
            "ana_what": 0,
            "ana_many": 30,
            "ana_count": 1,

            "gen_copies": 3,
            "gen_take": 2,
            "gen_mix": 'c',
            #"gen_stats": False,
            "str_clear": 's',
            "str_extra": 10,
            "str_what": 'e'
        }

    def __init__(self, *args):
        super(AmphSettings, self).__init__(QSettings.IniFormat, QSettings.UserScope, "Amphetype", "Amphetype")

    def get(self, k):
        v = self.value(k)
        if not v.isValid():
            return self.defaults[k]
        return cPickle.loads(str(v.toString()))

    def getFont(self, k):
        qf = QFont()
        qf.fromString(self.get(k))
        return qf

    def getColor(self, k):
        return QColor(self.get(k))
    
    def getHtml(self,k):
        return unicode_to_html(self.get(k))

    def set(self, k, v):
        p = self.get(k)
        if p == v:
            return
        self.setValue(k, QVariant(cPickle.dumps(v)))
        self.emit(SIGNAL("change"))
        self.emit(SIGNAL("change_" + k), v)



Settings = AmphSettings()


class SettingsColor(AmphButton):
    def __init__(self, key, text):
        self.key_ = key
        super(SettingsColor, self).__init__(Settings.get(key), self.pickColor)
        self.updateIcon()

    def pickColor(self):
        color = QColorDialog.getColor(Settings.getColor(self.key_), self)
        if not color.isValid():
            return
        Settings.set(self.key_, unicode(color.name()))
        self.updateIcon()

    def updateIcon(self):
        pix = QPixmap(32, 32)
        c = Settings.getColor(self.key_)
        pix.fill(c)
        self.setText(Settings.get(self.key_))
        self.setIcon(QIcon(pix))



class SettingsEdit(AmphEdit):
    def __init__(self, setting, data_type = None):
        val = Settings.get(setting)
        typ = data_type if data_type else type(val)
        validator = None
        if isinstance(val, float):
            validator = QDoubleValidator
        elif isinstance(val, (int, long)):
            validator = QIntValidator
        if validator is None:
            self.fmt = lambda x: x
        else:
            self.fmt = lambda x: "%g" % x
        super(SettingsEdit, self).__init__(
                            self.fmt(val),
                            lambda: Settings.set(setting, typ(self.text())),
                            validator=validator)
        self.connect(Settings, SIGNAL("change_" + setting), lambda x: self.setText(self.fmt(x)))


class SettingsCombo(QComboBox):
    def __init__(self, setting, lst, *args):
        super(SettingsCombo, self).__init__(*args)

        prev = Settings.get(setting)
        self.idx2item = []
        for i in range(len(lst)):
            if isinstance(lst[i], basestring):
                # not a tuple, use index as key
                k, v = i, lst[i]
            else:
                k, v = lst[i]
            self.addItem(v)
            self.idx2item.append(k)
            if k == prev:
                self.setCurrentIndex(i)

        self.connect(self, SIGNAL("activated(int)"),
                    lambda x: Settings.set(setting, self.idx2item[x]))

        #self.connect(Settings, SIGNAL("change_" + setting),
        #            lambda x: self.setCurrentIndex(self.item2idx[x]))

class SettingsCheckBox(QCheckBox):
    def __init__(self, setting, *args):
        super(SettingsCheckBox, self).__init__(*args)
        self.setCheckState(Qt.Checked if Settings.get(setting) else Qt.Unchecked)
        self.connect(self, SIGNAL("stateChanged(int)"),
                    lambda x: Settings.set(setting, True if x == Qt.Checked else False))

class PreferenceWidget(QWidget):
    def __init__(self):
        super(PreferenceWidget, self).__init__()

        self.font_lbl = QLabel()

        self.setLayout(AmphBoxLayout([
            ["Typer font is", self.font_lbl, AmphButton("Change...", self.setFont), None],
            SettingsCheckBox('allow_mistakes', "Allow continuing to next passage even with mistakes"), 
            [SettingsCheckBox('auto_review', "Automatically review slow and mistyped words after texts."),
                ('<a href="http://code.google.com/p/amphetype/wiki/Settings">(help)</a>\n', 1)],
            SettingsCheckBox('show_last', "Show last result(s) above text in the Typer."),
            SettingsCheckBox('use_lesson_stats', "Save key/trigram/word statistics from generated lessons."),
            [SettingsCheckBox('req_space', "Make SPACE mandatory before each session"),
                ('<a href="http://code.google.com/p/amphetype/wiki/Settings">(help)</a>\n', 1)],
            # SettingsCheckBox('single_space_only', "Convert double(+) spaces to single space"),   #doesn't work between sentences
            SettingsCheckBox('ignore_until_correct_space', "Prevent continuing to next word until space is correctly pressed"), 
            SettingsCheckBox('case_sensitive', "Case sensitive"), 
            [AmphGridLayout([["AUTOMATICALLY INSERT:", SettingsCheckBox('automatic_space_insertion', "spaces"),SettingsCheckBox('automatic_return_insertion', "newlines")],
                             ["  - Other characters:", SettingsEdit('automatic_other_insertion',data_type=unicode),SettingsCheckBox('use_automatic_other_insertion', "Use")], 
                [1+1j,1+2j,2+1j,2+2j], 
            ]), None],

            None,
            [AmphGridLayout([ 
                ["INPUT PALETTE", "Text Color", "Border", "Background","Highlight","Highlight Text"],
                ["Inactive", SettingsColor('quiz_inactive_fg', "Foreground"),SettingsColor('quiz_inactive_bd', "Foreground"), SettingsColor('quiz_inactive_bg', "Background"),SettingsColor('quiz_inactive_hl', "Highlight"),SettingsColor('quiz_inactive_hl_text', "Highlight Text")],
                ["Correct",  SettingsColor('quiz_right_fg', "Foreground"),SettingsColor('quiz_right_bd', "Foreground"), SettingsColor('quiz_right_bg', "Background")],
                ["Wrong",  SettingsColor('quiz_wrong_fg', "Foreground"),SettingsColor('quiz_wrong_bd', "Foreground"), SettingsColor('quiz_wrong_bg', "Background"),SettingsCheckBox('quiz_use_wrong_palette', "Use")],
                ["INVISIBLE MODE", SettingsColor('quiz_invisible_color', "Foreground"), SettingsColor('quiz_invisible_bd', "Foreground"), SettingsCheckBox('quiz_invisible', "Enabled")],
                ["INPUT MISTAKES"],
                ["Color", SettingsColor('text_area_mistakes_color','Foreground'),SettingsCheckBox('show_text_area_mistakes', "Show")],
                ["Space char",SettingsEdit('text_area_mistakes_space_char',data_type=unicode), SettingsCheckBox('text_area_replace_spaces', "Use")],
                ["Return char",SettingsEdit('text_area_return_replacement',data_type=unicode), SettingsCheckBox('text_area_replace_return', "Use")],
                ["TEXT DISPLAY"," "," ","Space char"], 
                ["Mistakes", SettingsColor('label_mistakes_color','Foreground'),SettingsCheckBox('show_label_mistakes', "Show"), SettingsEdit('label_mistakes_space_char',data_type=unicode), SettingsCheckBox("label_replace_spaces_in_mistakes", "Use")],
                ["Position", SettingsColor('label_position_color','Foreground'),SettingsCheckBox('show_label_position', "Show"), SettingsEdit('label_position_space_char',data_type=unicode), SettingsCheckBox("label_replace_spaces_in_position", "Use")],
                ["  - with mistakes", SettingsColor('label_position_with_mistakes_color','Foreground'),SettingsCheckBox('show_label_position_with_mistakes', "Use"), SettingsEdit('label_position_with_mistakes_space_char',data_type=unicode), SettingsCheckBox("label_replace_spaces_in_position_with_mistakes", "Use")],
                ["  - next to mistake", SettingsColor('label_position_with_prior_mistake_color','Foreground'),SettingsCheckBox('show_label_position_with_prior_mistake', "Use"), SettingsEdit('label_position_with_prior_mistake_space_char',data_type=unicode), SettingsCheckBox("label_replace_spaces_in_position_with_prior_mistake", "Use")],
                ["Return char",SettingsEdit('label_return_symbol',data_type=unicode)],
                ["WIDGETS"],                
                ["Background",SettingsColor('widgets_background_color', "Background")],
                ["Foreground", SettingsColor('widgets_text_color', "Foreground")],
                ["TEXT AREAS"],
                ["Background",SettingsColor('main_text_area_color', "Background")],
                ["GENERAL"],                
                ["Background",SettingsColor('main_background_color', "Background")],
                ["Text Color", SettingsColor('main_text_color', "Foreground")],
                ["Borders", SettingsColor("main_borders_color", "Foreground")],
                
                [1+1j,1+2j,2+1j,2+2j],
            ]), None],
            [AmphGridLayout([ 
                ["UNICODE -> ASCII TRANSLITERATION"],
                [SettingsCheckBox('transliteration_manual_unicode', "Initial manual transliteration (see Text.py)")],
                [SettingsCombo('transliteration_method', transliteration_methods)],
                [SettingsCheckBox('transliteration_manual_ascii', "Manual ascii -> ascii replacements (see Text.py)")],

                [1+1j,1+2j,2+1j,2+2j]
            ]), None],
            None,
            ["Data is considered too old to be included in analysis after",
                SettingsEdit("history"), "days.", None],
            ["Try to limit texts and lessons to between", SettingsEdit("min_chars"),
                "and", SettingsEdit("max_chars"), "characters.", None],
            ["When selecting easy/difficult texts, scan a sample of",
                SettingsEdit('num_rand'), "texts.", None],
            ["When grouping by sitting on the Performance tab, consider results more than",
                SettingsEdit('minutes_in_sitting'), "minutes away to be part of a different sitting.", None],
            ["Group by", SettingsEdit('def_group_by'), "results when displaying last scores and showing last results on the Typer tab.", None],
            ["When smoothing out the graph, display a running average of", SettingsEdit('dampen_average'), "values", None]
        ]))

        self.updateFont()

    def setFont(self):
        font, ok = QFontDialog.getFont(Settings.getFont('typer_font'), self)
        Settings.set("typer_font", unicode(font.toString()))
        self.updateFont()

    def updateFont(self):
        self.font_lbl.setText(Settings.get("typer_font"))
        qf = Settings.getFont('typer_font')
        self.font_lbl.setFont(qf)
