import random

wordCache = dict()

def init():
    global pendingLessons
    pendingLessons = []

# the cache makes each modified text determintistic, in that if you do the same text over and over, it will have the same random elements added.  
# this is useful for building up speed on selection of text
def modifiedWord(word):
    global wordCache
    chars = '.,!?                                    '
    stopChars = ',.?!-\'\n' #words containing these are left alone
    if not word in wordCache:
        if (not any((c in stopChars) for c in word)) and (len(word) > 1):
            wordCache[word] = word[0].capitalize() + word[1:] + random.choice(chars)
        else:
            wordCache[word] = word
    return wordCache[word]

def AddSymbols(text):
    text = ' '.join(modifiedWord(word) for word in text.split(' '))
    text = text.strip()
    return text