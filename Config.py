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


from __future__ import with_statement

import cPickle
from QtUtil import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import getpass

try:
    _dbname = getpass.getuser() or "typer"
    if '.' not in _dbname:
        _dbname += '.db'
except:
    _dbname = "typer.db"

def unicode_to_html(s):
    '''Takes a unicode string and encodes it as HTML'''
    return s.encode('ascii', 'xmlcharrefreplace')

class AmphSettings(QSettings):

    defaults = {
            "allow_mistakes":True,
            'quiz_invisible':False,
            'quiz_invisible_color':"#000000",
            "text_area_mistakes_color":"#a43434",
            "show_text_area_mistakes":True,
            "text_area_space_replacement":u"∙", #in html, "&#8729;", 
            "text_area_replace_spaces":False,
            'text_area_return_replacement':u"↵",
            'text_area_replace_return':True,
            "label_return_symbol":u"↵",
            "label_space_replacement":u"∙", #in html, "&#8729;", 
            "label_replace_spaces_in_mistakes":True,
            "label_replace_spaces_in_position":False,
            'label_text_color':"#777777",
            'label_mistakes_color':"#a43434",
            'show_label_mistakes':True,
            'label_position_color':"#008000",
            'show_label_position':True, 
            'label_position_with_mistakes_color':"#a0a000",
            'show_label_position_with_mistakes':False,
            "typer_font": str(QFont("Arial", 14).toString()),
            "history": 30.0,
            "min_chars": 220,
            "max_chars": 600,
            "lesson_stats": 0, # show text/lesson in perf -- not used anymore
            "perf_group_by": 0,
            "perf_items": 100,
            "text_regex": r"",
            "db_name": _dbname,
            "select_method": 0,
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
            "quiz_wrong_fg": "#646464",
            "quiz_wrong_bg": "#000000",

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
            [SettingsCheckBox('auto_review', "Automatically review slow and mistyped words after texts."),
                ('<a href="http://code.google.com/p/amphetype/wiki/Settings">(help)</a>\n', 1)],
            SettingsCheckBox('show_last', "Show last result(s) above text in the Typer."),
            SettingsCheckBox('use_lesson_stats', "Save key/trigram/word statistics from generated lessons."),
            [SettingsCheckBox('req_space', "Make SPACE mandatory before each session"),
                ('<a href="http://code.google.com/p/amphetype/wiki/Settings">(help)</a>\n', 1)],
            None,
            SettingsCheckBox('allow_mistakes', "Allow continuing to next passage even with mistakes"), 
            None,
            [AmphGridLayout([
                ["INPUT PALETTE", "Text Color", "Background"],
                ["Correct Input", SettingsColor('quiz_right_fg', "Foreground"),
                        SettingsColor('quiz_right_bg', "Background")],
                ["Wrong Input", SettingsColor('quiz_wrong_fg', "Foreground"),
                        SettingsColor('quiz_wrong_bg', "Background")],
                ["INVISIBLE MODE", SettingsColor('quiz_invisible_color', "Foreground"),
                        SettingsCheckBox('quiz_invisible', "Enabled")],
                ["INPUT MISTAKES"],
                ["Color", SettingsColor('text_area_mistakes_color','Foreground'),SettingsCheckBox('show_text_area_mistakes', "Show")],
                ["Space char",SettingsEdit('text_area_space_replacement',data_type=unicode), SettingsCheckBox('text_area_replace_spaces', "Use")],
                ["Return char",SettingsEdit('text_area_return_replacement',data_type=unicode), SettingsCheckBox('text_area_replace_return', "Use")],
                ["LABEL"],
                ["Base", SettingsColor('label_text_color', "Foreground")],
                ["Mistakes", SettingsColor('label_mistakes_color','Foreground'),SettingsCheckBox('show_label_mistakes', "Show")],
                ["Position", SettingsColor('label_position_color','Foreground'),SettingsCheckBox('show_label_position', "Show")],
                ["Position (with errors)", SettingsColor('label_position_with_mistakes_color','Foreground'),SettingsCheckBox('show_label_position_with_mistakes', "Use")],
                ["Space char in mistakes",SettingsEdit('label_space_replacement',data_type=unicode), SettingsCheckBox('label_replace_spaces_in_mistakes', "Use for mistakes"), SettingsCheckBox('label_replace_spaces_in_position', "Use for position")],
                ["Return char",SettingsEdit('label_return_symbol',data_type=unicode)],
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
