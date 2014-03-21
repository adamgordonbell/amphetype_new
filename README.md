My Fork of Amphetype - A great typing program.
It contains a bunch of small improvements that I needed to use it.

This is my personal fork of https://code.google.com/p/amphetype/

Differences include:

These include:
 * Phrase based lesson
 * Forced addition of capitals and symbols to words ( to strength training of these if so desired)
 * improved lesson splitter
 * permissive mode
 * Unicode -> ascii transliteration to avoid "untypable characters", as well as some replacements of bad formatting, either via unidecode and/or manually (see Text.py)
 * Experimental: Individual letter coloring based on current positions and error 
 * Experimental: Allows continuation even with typing errors 
 * Dark Theme
 * etc

Todo:

1. Refactor so that data analysis is separate from GUI classes


License and Disclaimer

GPLv3 (see gpl.txt).

Sample text included:
 * Selections from project gutenberg
 * All the typing tests from TyperRacer.com
 * QWERTY right hand / Left Hand and alternating hand words


To run, type:

python Amphetype.py

Depends on:

python-qt4  (that is, PyQt 4.3+)

OPTIONAL:

unidecode from https://pypi.python.org/pypi/Unidecode/
 - Will attempt to transliterate unicode -> ascii using this,
 if available. The default methods are mostly manual 
 (see: unicode_replacements in Text.py) and probably not as 
 effective.

py-editdist from http://www.mindrot.org/projects/py-editdist/
 - This latter dependancy is by no means critical and you will
 probably never get to use it. (For fetching words from a wordfile
 that are "similar" to your target words in the lesson generator.)
 If you don't have the module it will just select random words
 instead
