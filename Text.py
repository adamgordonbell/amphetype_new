from __future__ import division, with_statement

#import psyco
import re
import codecs
import random
from Config import Settings
from itertools import *
from PyQt4.QtCore import *



class LessonMiner(QObject):
    def __init__(self, fname):
        super(LessonMiner, self).__init__()
        with codecs.open(fname, "r", "utf_8_sig") as f:
            self.text = f.read()
        self.lessons = None
        self.min_chars = Settings.get('min_chars')
        self.split_regex = Settings.get('sentence_regex')
        self.split = re.compile(self.split_regex).split(self.text)

    def doIt(self):
        if self.split_regex == r"\n":
            rejoin = "\n"
        elif self.split_regex == r"\s":
            rejoin = " "
        elif len(self.split_regex) == 1:
            rejoin = self.split_regex
        else:
            rejoin = " "
        self.lessons = []
        backlog = []
        backlen = 0
        i = 0
        for s in self.split:
            backlog.append(s)
            backlen += len(s)
            if backlen >= self.min_chars:
                self.lessons.append(rejoin.join(backlog).strip())
                backlen = 0
                backlog = []
            i += 1
            self.emit(SIGNAL("progress(int)"), int(100 * i/len(self.split)))
        if backlen > 0:
            rejoin = " "
            self.lessons.append(rejoin.join(backlog).strip())

    def __iter__(self):
        if self.lessons is None:
            self.doIt()
        return iter(self.lessons)

