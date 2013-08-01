My Fork of Amphetype - A great typing program.
It contains a bunch of small improvements that I needed to use it.

This is my personal fork of https://code.google.com/p/amphetype/

These include:
 * Phrase based lesson
 * Forced addition of capitals and symbols to words ( to strength training of these if so desired)
 * improved lesson splitter
 * permissive mode
 * etc

Sample text included:
 * Selections from project gutenberg
 * All the typing tests from TyperRacer.com
 * QWERTY right hand / Left Hand and alternating hand words


To run, type:

python Amphetype.py

Depends on:

python-qt4  (that is, PyQt 4.3+)

OPTIONAL: py-editdist from http://www.mindrot.org/projects/py-editdist/
 - This latter dependancy is by no means critical and you will
 probably never get to use it. (For fetching words from a wordfile
 that are "similar" to your target words in the lesson generator.)
 If you don't have the module it will just select random words
 instead
