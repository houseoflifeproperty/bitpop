#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to check lkgr.

   grab Chromium LKGR from http://chromium-status.appspot.com/lkgr
   Compare with version saved in local file.
   If greater (or no local file), return 0.
   Else return 1.
"""
import sys
import optparse
import os
import urllib2

class CheckLKGR(object):
  def __init__(self, root):
    self.root = root
    self.filename = os.path.abspath(os.path.join(root, 'last-lkgr.txt'))
    self.lkgr_url = 'http://chromium-status.appspot.com/lkgr'
    self.old_lkgr = 0
    self.new_lkgr = 0
    super(CheckLKGR, self).__init__()

  def ReadSavedLKGR(self):
    """Read saved LKGR; if not found use the 0."""
    if not os.path.exists(self.filename):
      print 'No saved LKGR'
      return
    f = open(self.filename, 'r')
    self.old_lkgr = int(f.read())
    f.close()

  def GetNewLKGR(self):
    """Get the latest LKGR.  Do not save it to disk."""
    f = urllib2.urlopen(self.lkgr_url)
    data = f.read()
    f.close()
    self.new_lkgr = int(data)

  def Save(self):
    """Save the new LKGR."""
    print 'Saving LKGR %d in %s' % (self.new_lkgr, self.filename)
    if os.path.exists(self.filename):
      os.unlink(self.filename)
    f = open(self.filename, 'w')
    f.write('%d\n' % self.new_lkgr)
    f.close()

  def __str__(self):
    if self.new_lkgr > self.old_lkgr:
      action = 'NEW TEST NEEDED'
    else:
      action = 'No test needed.'
    return ('CheckLKGR:  old_lkgr: %d   new_lkgr: %d  %s' %
            (self.old_lkgr, self.new_lkgr, action))

  def CheckForNew(self):
    """Compare old and new LKGRs.

    Read old and new ones.  Save new one.  If bigger, return True.
    """
    self.ReadSavedLKGR()
    self.GetNewLKGR()
    self.Save()
    print self
    return self.new_lkgr > self.old_lkgr

def main():
  option_parser = optparse.OptionParser()
  option_parser.add_option('', '--root', help='root of source tree')
  options, args = option_parser.parse_args()
  if args or not options.root:
    option_parser.error('Must be invoked with --root argument')
  c = CheckLKGR(options.root)
  if c.CheckForNew():
    return 0
  return 1

if '__main__' == __name__:
  sys.exit(main())
