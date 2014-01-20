from __future__ import division, with_statement

#import psyco
import re
import codecs
import random
from Config import Settings
from itertools import *
from PyQt4.QtCore import *

#some undesired fancy characters to replace
fancy2normal = [
    #transformations to dots
    (u"…",u"..."),(u". . .",u"..."),

    #trimming of dots; put after dot transformations
    (u" ... ",u"..."),        
    
    #dash transformations
    (u"—",u"-"),
   
    #trimming of dashes; put after dash transformations
    (u" - '",u"-'"),(u"' - ",u"'-"),(u' - "',u'-"'),(u'" - ',u'"-'),
    
    #quote transformations
    (u"“",u'"'),
    (u"”",u'"'),
    (u"’",u"'"),
    (u"‘",u"'")
]

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
            #replaces some undesired fancy characters
            for fancy, normal in fancy2normal:
                l = l.replace(fancy, normal)
            l = l.strip()
            if l != '':
                p.append(l)
            elif len(p) > 0:
                ps.append(SentenceSplitter(u" ".join(p)))
                p = []
        if len(p) > 0:
            ps.append(SentenceSplitter(u" ".join(p)))
        return ps
