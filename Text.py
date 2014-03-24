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
# March 24 2014:
#  * Added transliteration options, integrated with settings [lalop] 

from __future__ import division, with_statement

#import psyco
import re
import codecs
import random
import textwrap
from Config import Settings, INDEX_TRANSLITERATION_UNIDECODE, INDEX_TRANSLITERATION_DELETE
from itertools import *
from PyQt4.QtCore import *

# strings in the original unicode input to be replaced, and their replacement
# generally used for replacing non-typable unicode with typeable ascii
#   NB: if unidecode not available, this might be the only method of
#       unicode -> ascii transliteration available to the user 
unicode_replacements = [
    # each element is a 2-tuple:
    #    (unicode str of text to replace, unicode str of replacement text)
    # e.g. (u"…",u"...") 

    #transformations to dots
    (u"…",u"..."),   

    #dash transformations
    (u"—",u"-"),

    #quote transformations
    (u"“",u'"'),
    (u"”",u'"'),
    (u"’",u"'"),
    (u"’",u"'"),
    (u"‘",u"'"),

    #special character transformations
    (u"ø",u"o"),
    (u"ö",u"o"),
    (u"ü",u"u"),
    (u"é",u"e") 
]

# strings in the ascii-converted input to be replaced, and their replacement
# generally used for correcting badly formatted input
ascii_replacements = [
    # each element is a 2-tuple:
    #    (ascii str of text to replace, ascii str of replacement text)
    # e.g. (" ... ","...") 

    #transformations to dots
    (". . .","..."),
 
    #trimming of dots; put after dot transformations
    ("... ","..."),(" ...","..."),
    
    #trimming of dashes; put after dash transformations
    (" - '","-'"),("' - ","'-"),(' - "','-"'),('" - ','"-') 
]

#imports unidecode, if available
try:
    import unidecode
    unidecode_imported = True
except ImportError:
    unidecode_imported = False

abbreviations = set(map(unicode, [
'jr', 'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', "sen","rep","sens", "reps",'gov', "attys", "atty", 'supt',
'det', 'rev', 'col','gen', 'lt', 'cmdr', 'adm', 'capt', 'sgt', 'cpl', 'maj',
'dept', 'univ', 'assn', 'bros', 'inc', 'ltd', 'co', 'corp',
'arc', 'al', 'ave', "blvd", "bld",'cl', 'ct', 'cres', 'dr', "expy", "exp", 'dist', 'mt', 'ft',
"fwy", "fy",  "hway", "hwy",'la', "pde", "pd", 'pl', 'plz', 'rd', 'st', 'tce',
'Ala' , 'Ariz', 'Ark', 'Cal', 'Calif', 'Col', 'Colo', 'Conn',
'Del', 'Fed' , 'Fla', 'Ga', 'Ida', 'Id', 'Ill', 'Ind', 'Ia',
'Kan', 'Kans', 'Ken', 'Ky' , 'La', 'Me', 'Md', 'Is', 'Mass',
'Mich', 'Minn', 'Miss', 'Mo', 'Mont', 'Neb', 'Nebr' , 'Nev',
'Mex', 'Okla', 'Ok', 'Ore', 'Penna', 'Penn', 'Pa'  , 'Dak',
'Tenn', 'Tex', 'Ut', 'Vt', 'Va', 'Wash', 'Wis', 'Wisc', "Wy",
'Wyo', 'USAFA', 'Alta' , 'Man', 'Ont', u'Qué', 'Sask', 'Yuk',
'jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec','sept',
'vs', 'etc', 'no', 'esp', 'eg', 'ie', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12',
'avg', 'viz', 'm', 'mme']))

class SentenceSplitter(object):
    sen = re.compile(r"""(?:(?: |^)[^\w. ]*(?P<pre>\w+)[^ .]*\.+|[?!]+)['"]?(?= +(?:[^ a-z]|$))|$""")

    def __init__(self, text):
        self.string = text

    def __iter__(self):
        p = [0]
        return ifilter(None, imap(lambda x: self.pars(p, x), self.sen.finditer(self.string)))

    def pars(self, p, mat):
        if mat.group('pre') and self.isAbbreviation(mat.group('pre')):
            return None
        p.append(mat.end())
        return self.string[p[-2]:p[-1]].strip()

    def isAbbreviation(self, s):
        ls = s.lower()
        return ls in abbreviations or s in abbreviations


class LessonMiner(QObject):
    def __init__(self, fname):
        super(LessonMiner, self).__init__()
        #print time.clock()
        with codecs.open(fname, "r", "utf_8_sig") as f:
            self.paras = self.paras(f)
        self.lessons = None
        self.min_chars = Settings.get('min_chars')

    def doIt(self):
        self.lessons = []
        backlog = []
        backlen = 0
        i = 0
        for p in self.paras:
            if len(backlog) > 0:
                backlog.append(None)
            for s in p:
                backlog.append(s)
                backlen += len(s)
                if backlen >= self.min_chars:
                    self.lessons.append(self.popFormat(backlog))
                    backlen = 0
            i += 1
            self.emit(SIGNAL("progress(int)"), int(100 * i/len(self.paras)))
        if backlen > 0:
            self.lessons.append(self.popFormat(backlog))

    def popFormat(self, lst):
        #print lst
        ret = []
        p = []
        while len(lst) > 0:
            s = lst.pop(0)
            if s is not None:
                p.append(s)
            else:
                ret.append(u' '.join(p))
                p = []
        if len(p) > 0:
            ret.append(u' '.join(p))
        return u'\n'.join(ret)

    def __iter__(self):
        if self.lessons is None:
            self.doIt()
        return iter(self.lessons)

    def paras(self, f):
        p = []
        ps = []
        previous_line_empty = True
        for l in f:
            #designated replacements for unicode text
            if Settings.get('transliteration_manual_unicode'):
                for orig, repl in unicode_replacements:
                    l = l.replace(orig, repl)
                    
            ascii_line = l
            if unidecode_imported and Settings.get('transliteration_method') == INDEX_TRANSLITERATION_UNIDECODE:
                #tries to use unidecode if it exists
                ascii_line = unidecode.unidecode(ascii_line)
            elif Settings.get('transliteration_method') == INDEX_TRANSLITERATION_DELETE:
                #deletes all remaining non-ascii chars
                try:
                    ascii_line = ascii_line.decode('ascii')
                except UnicodeEncodeError:
                    ascii_line = ''
                    for c in l:
                        if ord(c) < 128:
                            ascii_line += c
                        else:
                            ascii_line += ""

            #replaces any 1+ adjacent whitespace chars (spaces, tabs, newlines, etc) with one ascii space
            if Settings.get('single_space_only'): 
                ascii_line = re.sub("\s+"," ",ascii_line)               

            #designated replacements for ascii text
            if Settings.get('transliteration_manual_ascii'):
                for orig, repl in ascii_replacements:
                    ascii_line = ascii_line.replace(orig, repl) 

            l = ascii_line.strip()
            current_line_empty = not l
           
            #the current line is empty: insert empty line 
            #or the current line and previous line both nonempty: need to insert empty line between them
            if (current_line_empty or not previous_line_empty) and len(p) > 0:
                ps.append(SentenceSplitter(u" ".join(p)))
                p = []

            if not current_line_empty:
                p.append(l)
                
            previous_line_empty = current_line_empty
        if len(p) > 0:
            ps.append(SentenceSplitter(u" ".join(p)))
        return ps

def to_lessons(sentences):
    backlog = []
    backlen = 0
    min_chars = Settings.get('min_chars')
    max_chars = Settings.get('max_chars')
    sweet_size = 3*(min_chars + max_chars) // 4

    for s in sentences:
        ssplit = []
        while len(s) > sweet_size:
            idx = s.find(' ', sweet_size)
            if idx == -1:
                break
            if idx != -1:
                ssplid.append(s[:idx])
                s = s[idx+1:]
        ssplit.append(s)
        for xs in ssplit:
            backlog.append(xs)
            backlen += len(xs)
            if backlen >= min_chars:
                yield u' '.join(backlog)
                backlog = []
                backlen = 0
    if backlen > 0:
        yield u' '.join(backlog)



class LessonGeneratorPlain(object):
    def __init__(self, words, per_lesson=12, repeats=4):
        while (0 < len(words) % per_lesson < per_lesson / 2):
            per_lesson += 1

        self.lessons = []
        wcopy = words[:]
        while wcopy:
            lesson = wcopy[0:per_lesson] * repeats
            wcopy[0:per_lesson] = []
            random.shuffle(lesson)
            self.lessons.append( #textwrap.fill(
                                                u' '.join(lesson)) #, width))

    def __iter__(self):
        return iter(self.lessons)





if __name__ == '__main__':
    import sys
    for x in LessonMiner(sys.argv[1]):
        print "--%s--" % x




