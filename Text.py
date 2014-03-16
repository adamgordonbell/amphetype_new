from __future__ import division, with_statement

#import psyco
import re
import codecs
import random
from Config import Settings
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
    (" ... ","..."),        
    
    #trimming of dashes; put after dash transformations
    (" - '","-'"),("' - ","'-"),(' - "','-"'),('" - ','"-') 
]

#imports unidecode, if available
try:
    import unidecode
    unidecode_imported = True
except ImportError:
    unidecode_imported = False
    print("Warning: unidecode (for unicode to ascii transliteration) not available.  Transliterations may be limited.")

class SentenceSplitter(object):

    def __init__(self, text):
        self.string = text

    def __iter__(self):
        p = [0]
        sen = re.compile(Settings.get('sentence_regex'))
        return ifilter(None, imap(lambda x: self.pars(p, x), sen.finditer(self.string)))

    def pars(self, p, mat):
        p.append(mat.end())
        return self.string[p[-2]:p[-1]].strip()

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
        for l in f:
            #designated replacements for unicode text
            for orig, repl in unicode_replacements:
                l = l.replace(orig, repl)

            if unidecode_imported:
                #tries to use unidecode if it exists
                ascii_line = unidecode.unidecode(l)
            else: 
                #othewise just deletes all remaining non-ascii chars
                try:
                    ascii_line = l.decode('ascii')
                except UnicodeEncodeError:
                    ascii_line = ''
                    for c in l:
                        if ord(c) < 128:
                            ascii_line += c
                        else:
                            ascii_line += ""

            #replaces any 1+ adjacent whitespace chars (spaces, tabs, newlines, etc) with one ascii space
            ascii_line = re.sub("\s+"," ",ascii_line)               

            #designated replacements for ascii text
            for orig, repl in ascii_replacements:
                ascii_line = ascii_line.replace(orig, repl) 

            l = ascii_line.strip()
            if l <> '':
                p.append(l)
            elif len(p) > 0:
                ps.append(SentenceSplitter(u" ".join(p)))
                p = []
        if len(p) > 0:
            ps.append(SentenceSplitter(u" ".join(p)))
        return ps
