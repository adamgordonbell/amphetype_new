import random
from Config import *

wordCache = dict()

def init():
    global pendingLessons
    pendingLessons = []

# the cache makes each modified text determintistic, in that if you do the same text over and over, it will have the same random elements added.  
# this is useful for building up speed on selection of text
def modifiedWord(word):
    global wordCache
    if not word in wordCache:
        if (not any((c in Settings.get('stop_symbols')) for c in word)) and (len(word) > 1) and (Settings.get('title_case')) and (Settings.get('symbols')):
            wordCache[word] = word[0].capitalize() + word[1:] + random.choice(Settings.get('include_symbols'))
        elif(not any((c in Settings.get('stop_symbols')) for c in word)) and (len(word) > 1) and (Settings.get('symbols')):
            wordCache[word] = word + random.choice(Settings.get('include_symbols'))
        elif(not any((c in Settings.get('stop_symbols')) for c in word)) and (len(word) > 1) and (Settings.get('title_case')):
            wordCache[word] = word[0].capitalize() + word[1:]
        else:
            wordCache[word] = word
    return wordCache[word]

def AddSymbols(text):
    text = ' '.join(modifiedWord(word) for word in text.split(' '))
    text = text.strip()
    return text