from __future__ import division, with_statement

from itertools import *
import bisect
import sqlite3
import re
from Config import Settings

class Statistic(list):
    def __init__(self):
        super(Statistic, self).__init__()
        self.flawed_ = 0

    def append(self, x, flawed=False):
        bisect.insort(self, x)
        if flawed:
            self.flawed_ += 1

    def __cmp__(self, other):
        return cmp(self.median(), other.median())

    def measurement(self):
        return self.trimmed_average(len(self), map(lambda x: (x, 1), self))

    def median(self):
        l = len(self)
        if l == 0:
            return None
        if l & 1:
            return self[l // 2]
        return (self[l//2] + self[l//2-1])/2.0

    def flawed(self):
        return self.flawed_

    def trimmed_average(self, total, series):
        s = 0.0
        n = 0

        start = 0
        cutoff = total // 3
        while cutoff > 0:
            cutoff -= series[start][1]
            start += 1
        if cutoff < 0:
            s += -cutoff * series[start-1][0]
            n += -cutoff

        end = len(series)-1
        cutoff = total // 3
        while cutoff > 0:
            cutoff -= series[end][1]
            end -= 1
        if cutoff < 0:
            s += -cutoff * series[end+1][0]
            n += -cutoff

        while start <= end:
            s += series[start][1] * series[start][0]
            n += series[start][1]
            start += 1

        return s/n

class MedianAggregate(Statistic):
    def step(self, val):
        self.append(val)

    def finalize(self):
        return self.median()

class MeanAggregate(object):
    def __init__(self):
        self.sum_ = 0.0
        self.count_ = 0

    def step(self, value, count):
        self.sum_ += value * count
        self.count_ += count

    def finalize(self):
        return self.sum_ / self.count_

class FirstAggregate(object):
    def __init__(self):
        self.val = None

    def step(self, val):
        if self.val is not None:
            self.val = val

    def finalize(self):
        return self.val

class AmphDatabase(sqlite3.Connection):
    def CreateNewDBIfMissingTables(self):
        try:
            self.fetchall("select * from result limit 1")
            self.fetchall("select * from source limit 1")
            self.fetchall("select * from statistic limit 1")
            self.fetchall("select * from mistake limit 1")
            self.fetchall("select * from text limit 1")
        except:
            self.newDB()

    def __init__(self, *args):
        sqlite3.Connection.__init__(self, *args)

        self.setRegex("")
        self.resetCounter()
        self.resetTimeGroup()
        sqlite3.Connection.create_function(self, "counter", 0, self.counter)
        sqlite3.Connection.create_function(self, "regex_match", 1, self.match)
        sqlite3.Connection.create_function(self, "abbreviate", 2, self.abbreviate)
        sqlite3.Connection.create_function(self, "time_group", 2, self.time_group)
        sqlite3.Connection.create_aggregate(self, "agg_median", 1, MedianAggregate)
        sqlite3.Connection.create_aggregate(self, "agg_mean", 2, MeanAggregate)
        sqlite3.Connection.create_aggregate(self, "agg_first", 1, FirstAggregate)
        sqlite3.Connection.create_function(self, "ifelse", 3, lambda x, y, z: y if x is not None else z)
        self._count = None
        self.timecnt_ = None
        self.regex_ = None
        self.lasttime_ = None

        self.CreateNewDBIfMissingTables()

    def resetTimeGroup(self):
        self.lasttime_ = 0.0
        self.timecnt_ = 0

    def time_group(self, d, x):
        if abs(x-self.lasttime_) >= d:
            self.timecnt_ += 1
        self.lasttime_ = x
        return self.timecnt_

    def setRegex(self, x):
        self.regex_ = re.compile(x)

    def abbreviate(self, x, n):
        if len(x) <= n:
            return x
        return x[: n-3] + "..."

    def match(self, x):
        if self.regex_.search(x):
            return 1
        return 0

    def counter(self):
        self._count += 1
        return self._count
    def resetCounter(self):
        self._count = -1

    def newDB(self):
        sqlite3.Connection.executescript(self, """
create table source (name text, disabled integer, discount integer);
create table text (id text primary key, source integer, text text, disabled integer);
create table result (w real, text_id text, source integer, wpm real, accuracy real, viscosity real);
create table statistic (w real, data text, type integer, time real, count integer, mistakes integer, viscosity real);
create table mistake (w real, target text, mistake text, count integer);
create view text_source as
    select id, s.name, text, coalesce(t.disabled, s.disabled)
        from text as t left join source as s on (t.source = s.rowid);
        """)
        sqlite3.Connection.commit(self)

    def executemany_(self, *args):
        sqlite3.Connection.executemany(self, *args)
    def executemany(self, *args):
        sqlite3.Connection.executemany(self, *args)
        #self.commit()

    def fetchall(self, *args):
        return sqlite3.Connection.execute(self, *args).fetchall()

    def fetchone(self, sql, default, *args):
        x = sqlite3.Connection.execute(self, sql, *args)
        g = x.fetchone()
        if g is None:
            return default
        return g

    def getSource(self, source, lesson=None):
        v = self.fetchall('select rowid from source where name = ? limit 1', (source, ))
        if len(v) > 0:
            sqlite3.Connection.execute(self, 'update source set disabled = NULL where rowid = ?', v[0])
            sqlite3.Connection.commit(self)
            return v[0][0]
        sqlite3.Connection.execute(self, 'insert into source (name, discount) values (?, ?)', (source, lesson))
        return self.getSource(source)

dbname = Settings.get("db_name")

# GLOBAL
DB = sqlite3.connect(dbname, 5, 0, "DEFERRED", False, AmphDatabase)
