# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cStringIO
import re

DEFAULTS = {
    'color' : 'white',
    'background-color' : 'black',
    'font-weight' : 'normal',
    'text-decoration' : 'none',
}


class Ansi2HTML:
    """Class for converting text streams with ANSI codes into html"""

    ANSIEscape = '['
   
    ANSIAttributes = {
        0 : ['color:' + DEFAULTS['color'],
             'font-weight:' + DEFAULTS['font-weight'],
             'text-decoration:' + DEFAULTS['text-decoration'],
             'background-color:' + DEFAULTS['background-color']], # reset
        1 : ['font-weight:bold'],
        2 : ['font-weight:lighter'],
        4 : ['text-decoration:underline'],
        5 : ['text-decoration:blink'],
        7 : [], # invert attribute?
        8 : [], # invisible attribute?
        30 : ['color:black'],
        31 : ['color:red'],
        32 : ['color:green'],
        33 : ['color:yellow'],
        34 : ['color:blue'],
        35 : ['color:magenta'],
        36 : ['color:cyan'],
        37 : ['color:white'],
        39 : ['color:' + DEFAULTS['color']],
        40 : ['background-color:black'],
        41 : ['background-color:red'],
        42 : ['background-color:green'],
        43 : ['background-color:yellow'],
        44 : ['background-color:blue'],
        45 : ['background-color:magenta'],
        46 : ['background-color:cyan'],
        47 : ['background-color:white'],
        49 : ['background-color:' + DEFAULTS['background-color']],
    }

    def __init__(self):
        self.ctx = {}
        # Send a 0 code, resetting ctx to defaults.
        self.attrib('0')
        # Prepare a regexp recognizing all ANSI codes.
        code_src = '|'.join(self.ANSICodes)
        # This captures non-greedy code argument and code itself, both grouped.
        self.code_re = re.compile("(.*?)(" + code_src + ")")

    def noop(self, arg):
        """Noop code, for ANSI codes that have no html equivalent."""
        return ''

    def attrib(self, arg):
        """Text atribute code"""
        if arg == '':
            # Apparently, empty code argument means reset (0).
            arg = '0'
        for attr in arg.split(";"):
            try:
                for change in self.ANSIAttributes[int(attr)]:
                    pieces = change.split(":")
                    self.ctx[pieces[0]] = pieces[1]
            except KeyError:
                # Invalid key? Hmmm.
                return 'color:red">ANSI code not found: ' + \
                        arg + '<font style="color:' + self.ctx['color']
        return self.printStyle()

    ANSICodes = { 
        'H' : noop, # cursor_pos, # ESC[y,xH - Cursor position y,x
        'A' : noop, # cursor_up, # ESC[nA - Cursor Up n lines
        'B' : noop, # cursor_down, # ESC[nB - Cursor Down n lines
        'C' : noop, # cursor_forward, # ESC[nC - Cursor Forward n characters
        'D' : noop, # cursor_backward, # ESC[nD - Cursor Backward n characters
        'f' : noop, # cursor_xy, # ESC[y;xf - Cursor pos y,x (infrequent)
        'R' : noop, # cursor_report, # ESC[y;xR - Cursor position report y,x
        'n' : noop, # device_status, # ESC[6n - Dev status report (cursor pos)
        's' : noop, # save_cursor, # ESC[s - Save cursor position
        'u' : noop, # restore_cursor, # ESC[u - Restore cursor position
        'J' : noop, # clrscr, # ESC[2J - Erase display
        'K' : noop, # erase2eol, # ESC[K - Erase to end of line
        'L' : noop, # insertlines, # ESC[nL - Inserts n blank lines at cursor
        'M' : noop, # deletelines, # ESC[nM - Deletes n lines including cursor
        '@' : noop, # insertchars, # ESC[n@ - Inserts n blank chars at cursor
        'P' : noop, # deletechars, # ESC[nP - Deletes n chars including cursor
        'y' : noop, # translate, # ESC[n;ny - Output char translate
        'p' : noop, # key_reassign, #ESC["str"p - Keyboard Key Reassignment
        'm' : attrib, # ESC[n;n;...nm - Set attributes
    }

    def printStyle(self, showDefaults=False):
        """Returns a text representing the style of the current context."""
        style = ''
        for attr in DEFAULTS:
            if self.ctx[attr] != DEFAULTS[attr] or showDefaults:
                style += attr + ':' + self.ctx[attr] + ';'
        return style

    def printHtmlHeader(self, title):
        text = '<html><head><title>%s</title></head>' % title
	text += '<body bgcolor="%s"><pre>' % DEFAULTS['background-color']
        return text

    def printHtmlFooter(self):
        return '</pre></body></html>'

    def printHeader(self):
        """Envelopes everything into defaults <font> tag and opens a stub."""
        self.attrib("0") # this means reset to default
        return '<font style="%s"><font>' % self.printStyle(showDefaults=True)

    def printFooter(self):
        """Closes both stub and envelope font tags."""
        return '</font></font>'

    def parseBlock(self, string):
        """Takes a block of text and transform into html"""
        output = cStringIO.StringIO()
        skipfirst = True
        # Splitting by ANSIEscape turns the line into following elements:
        # arg,code,text
        # First two change the context, text is carried.
        for block in string.split(self.ANSIEscape):
            if not block:
                # First block is empty -> the line starts with escape code.
                skipfirst = False
                continue

            if skipfirst:
                # The line doesn't start with escape code -> skip first block.
                output.write(block)
                skipfirst = False
                continue

            match = self.code_re.match(block)
            if not match:
                # If there's no match, it is the line end. Don't parse it.
                output.write(block)
                continue

            parseFunc = self.ANSICodes[match.group(2)]
            # Replace ANSI codes with </font><font> sequence
            output.write('</font><font style="')
            output.write(parseFunc(self, match.group(1)))
            output.write('">')
            # Output the text
            output.write(block.split(match.group(2),1)[1])

        return output.getvalue()
