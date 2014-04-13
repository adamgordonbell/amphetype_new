My Fork of Amphetype - A great typing program.
# Amphetype (lalop edition)
It contains a bunch of small improvements that I needed to use it.

This is my personal fork of [Amphetype](https://code.google.com/p/amphetype/).

Differences include:

These include:
 * Unicode -> Ascii transliteration to avoid "untypable characters", as well as some replacements of bad formatting, either via unidecode and/or manually (see Text.py)
 * Phrase based lesson
 * Forced addition of capitals and symbols to words ( to strength training of these if so desired)
 * Letter coloring, both in input and displayed text, based on current positions and errors
 * Individual letter coloring, both in input and displayed text, based on current positions and errors
 * improved lesson splitter
4. Toggle case sensitivity
 * Option for continuing to the next passage even with typing mistakes
 * permissive mode
5. Option for continuing to the next passage even with typing mistakes
 * Invisible Mode: Makes input text invisible (goes well with #2)
 * Option for preventing continuing to the next word until space correctly pressed
6. Option to count adjacent errors as only one error

7. Option for automatically inserting space, newline, and other custom letters
 * Allows continuation even with typing errors
 * Dark Theme
 * etc
 * Extensive GUI Color Settings
 * Can change return and space characters
 * Allows for smaller resizing than vanilla Amphetype

8. Option for preventing continuing to the next word until space correctly pressed

9. Extensive GUI Color Settings

Todo:
10. Can change return and space characters

11. Allows for smaller resizing than vanilla Amphetype

### Warning about databases/statistics: 
The database/statistics of this fork should be considered unstable.  In addition, some of the options here (e.g. counting or not counting adjacent errors) can significantly change the resulting statistics. 

License and Disclaimers
It is therefore recommended to use a different database for this fork than with other versions of amphetype, as well as to make regular backups of any important data.


Amphetype is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Amphetype is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Amphetype.  If not, see <http://www.gnu.org/licenses/>.

Sample text included:
 * Selections from project gutenberg
 * All the typing tests from TyperRacer.com
 * QWERTY right hand / Left Hand and alternating hand words
THIS SOFTWARE, ANY ASSOCIATED FILES, AND ANY ASSOCIATED DOCUMENTATION
ARE PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS", WITHOUT
WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, ANY ASSOCIATED FILES,
OR ANY ASSOCIATED DOCUMENTATION, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.


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
