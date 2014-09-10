#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for classes in annotator.py."""

import cStringIO
import json
import types
import os
import sys
import tempfile
import unittest

import test_env  # pylint: disable=W0611

from common import annotator
from common import chromium_utils


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class TestAnnotationStreams(unittest.TestCase):
  def setUp(self):
    self.buf = cStringIO.StringIO()

  def _getLines(self):
    """Return list of non-empty lines in output."""
    return [line for line in self.buf.getvalue().rstrip().split('\n') if line]

  def testBasicUsage(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)
    with stream.step('one') as _:
      pass
    with stream.step('two') as _:
      pass

    result = [
        '@@@SEED_STEP one@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_CLOSED@@@',
        '@@@SEED_STEP two@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_CLOSED@@@',
    ]

    self.assertEquals(result, self._getLines())

  def testStepAnnotations(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)
    with stream.step('one') as s:
      s.step_warnings()
      s.step_failure()
      s.step_exception()
      s.step_clear()
      s.step_summary_clear()
      s.step_text('hello')
      s.step_summary_text('hello!')
      s.step_log_line('mylog', 'test')
      s.step_log_end('mylog')
      s.step_log_line('myperflog', 'perf data')
      s.step_log_end_perf('myperflog', 'dashboardname')
      s.step_link('cool_link', 'https://cool.example.com/beano_gnarly')
      s.write_log_lines('full_log', ['line one', 'line two'])
      s.write_log_lines('full_perf_log', ['perf line one', 'perf line two'],
                        perf='full_perf')

    result = [
        '@@@SEED_STEP one@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_WARNINGS@@@',
        '@@@STEP_FAILURE@@@',
        '@@@STEP_EXCEPTION@@@',
        '@@@STEP_CLEAR@@@',
        '@@@STEP_SUMMARY_CLEAR@@@',
        '@@@STEP_TEXT@hello@@@',
        '@@@STEP_SUMMARY_TEXT@hello!@@@',
        '@@@STEP_LOG_LINE@mylog@test@@@',
        '@@@STEP_LOG_END@mylog@@@',
        '@@@STEP_LOG_LINE@myperflog@perf data@@@',
        '@@@STEP_LOG_END_PERF@myperflog@dashboardname@@@',
        '@@@STEP_LINK@cool_link@https://cool.example.com/beano_gnarly@@@',
        '@@@STEP_LOG_LINE@full_log@line one@@@',
        '@@@STEP_LOG_LINE@full_log@line two@@@',
        '@@@STEP_LOG_END@full_log@@@',
        '@@@STEP_LOG_LINE@full_perf_log@perf line one@@@',
        '@@@STEP_LOG_LINE@full_perf_log@perf line two@@@',
        '@@@STEP_LOG_END_PERF@full_perf_log@full_perf@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_CLOSED@@@',
    ]

    self.assertEquals(result, self._getLines())

  def testStepAnnotationsWrongParams(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)
    with stream.step('one') as s:
      with self.assertRaisesRegexp(TypeError, r'1 argument \(2 given\)'):
        s.step_warnings('bar')
      with self.assertRaisesRegexp(TypeError, r'2 arguments \(3 given\)'):
        s.step_summary_text('hello!', 'bar')
      with self.assertRaisesRegexp(TypeError, r'3 arguments \(1 given\)'):
        s.step_log_line()

  def testStepAnnotationsDocstring(self):
    self.assertEqual(
      annotator.AdvancedAnnotationStep.step_link.__doc__,
      'Emits an annotation for STEP_LINK.'
    )


  def testException(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)

    def dummy_func():
      with stream.step('one'):
        raise Exception('oh no!')
    self.assertRaises(Exception, dummy_func)

    log_string = '@@@STEP_LOG_LINE@exception'
    exception = any(line.startswith(log_string) for line in self._getLines())
    self.assertTrue(exception)

  def testNoNesting(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)

    def dummy_func():
      with stream.step('one'):
        with stream.step('two'):
          pass
    self.assertRaises(Exception, dummy_func)

  def testDupLogs(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)

    with stream.step('one') as s:
      lines = ['one', 'two']
      s.write_log_lines('mylog', lines)
      self.assertRaises(ValueError, s.write_log_lines, 'mylog', lines)

  def testAdvanced(self):
    step = annotator.AdvancedAnnotationStep(stream=self.buf, flush_before=None)
    stream = annotator.AdvancedAnnotationStream(stream=self.buf,
                                                flush_before=None)
    stream.step_cursor('one')
    step.step_started()
    stream.step_cursor('two')
    step.step_started()
    stream.step_cursor('one')
    step.step_closed()
    stream.step_cursor('two')
    step.step_closed()

    result = [
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_CLOSED@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_CLOSED@@@',
    ]

    self.assertEquals(result, self._getLines())


def _synthesizeCmd(args):
  basecmd = [sys.executable, '-c']
  basecmd.extend(args)
  return basecmd


class TestExecution(unittest.TestCase):
  def setUp(self):
    self.capture = chromium_utils.FilterCapture()
    self.tempfd, self.tempfn = tempfile.mkstemp()
    self.temp = os.fdopen(self.tempfd, 'wb')
    self.script = os.path.join(SCRIPT_DIR, os.pardir, 'annotator.py')

  def tearDown(self):
    self.temp.close()
    if os.path.exists(self.tempfn):
      os.remove(self.tempfn)

  def _runAnnotator(self, cmdlist, env=None):
    json.dump(cmdlist, self.temp)
    self.temp.close()
    cmd = [sys.executable, self.script, self.tempfn]
    cmd_env = os.environ.copy()
    cmd_env['PYTHONPATH'] = os.pathsep.join(sys.path)
    if env:
      cmd_env.update(env)
    return chromium_utils.RunCommand(cmd, filter_obj=self.capture, env=cmd_env,
                                     print_cmd=False)

  def testSimpleExecution(self):
    cmdlist = [{'name': 'one', 'cmd': _synthesizeCmd(['print \'hello!\''])},
               {'name': 'two', 'cmd': _synthesizeCmd(['print \'yo!\''])}]

    ret = self._runAnnotator(cmdlist)

    self.assertEquals(ret, 0)

    step_one_header = [
        '@@@STEP_CURSOR one@@@',
        '',
        '@@@STEP_STARTED@@@',
        '',
        sys.executable + " -c print 'hello!'",
        'in dir %s:' % os.getcwd(),
        ' allow_subannotations: False',
        ' cmd: [' + repr(sys.executable) + ', \'-c\', "print \'hello!\'"]',
        ' name: one',
        'full environment:',
    ]
    step_one_result = [
        'hello!',
        '',
        '@@@STEP_CURSOR one@@@',
        '',
        '@@@STEP_CLOSED@@@',
    ]
    step_two_header = [
        '@@@STEP_CURSOR two@@@',
        '',
        '@@@STEP_STARTED@@@',
        '',
        sys.executable + " -c print 'yo!'",
        'in dir %s:' % os.getcwd(),
        ' allow_subannotations: False',
        ' cmd: [' + repr(sys.executable) + ', \'-c\', "print \'yo!\'"]',
        ' name: two',
        'full environment:',
    ]
    step_two_result = [
        'yo!',
        '',
        '@@@STEP_CURSOR two@@@',
        '',
        '@@@STEP_CLOSED@@@',
    ]

    def has_sublist(whole, part):
      n = len(part)
      return any((part == whole[i:i+n]) for i in xrange(len(whole) - n+1))

    self.assertTrue(has_sublist(self.capture.text, step_one_header))
    self.assertTrue(has_sublist(self.capture.text, step_one_result))
    self.assertTrue(has_sublist(self.capture.text, step_two_header))
    self.assertTrue(has_sublist(self.capture.text, step_two_result))

  def testFailBuild(self):
    cmdlist = [{'name': 'one', 'cmd': _synthesizeCmd(['print \'hello!\''])},
               {'name': 'two', 'cmd': _synthesizeCmd(['error'])}]

    ret = self._runAnnotator(cmdlist)

    self.assertTrue('@@@STEP_FAILURE@@@' in self.capture.text)
    self.assertEquals(ret, 1)

  def testStopBuild(self):
    cmdlist = [{'name': 'one', 'cmd': _synthesizeCmd(['error'])},
               {'name': 'two', 'cmd': _synthesizeCmd(['print \'yo!\''])}]

    ret = self._runAnnotator(cmdlist)

    self.assertTrue('@@@STEP_CURSOR two@@@' not in self.capture.text)
    self.assertEquals(ret, 1)

  def testException(self):
    cmdlist = [{'name': 'one', 'cmd': ['doesn\'t exist']}]

    ret = self._runAnnotator(cmdlist)

    self.assertTrue('@@@STEP_EXCEPTION@@@' in self.capture.text)
    self.assertEquals(ret, 1)

  def testCwd(self):
    tmpdir = os.path.realpath(tempfile.mkdtemp())
    try:
      cmdlist = [{'name': 'one',
                  'cmd': _synthesizeCmd(['import os; print os.getcwd()']),
                  'cwd': tmpdir
                 },]
      ret = self._runAnnotator(cmdlist)
    finally:
      os.rmdir(tmpdir)
    self.assertTrue(tmpdir in self.capture.text)
    self.assertEquals(ret, 0)

  def testStepEnvKeep(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd([
                  'import os; print os.environ[\'SOME_ENV\']'
                ]),
                'env': {'SOME_OTHER_ENV': '123'}
               },]
    ret = self._runAnnotator(cmdlist, env={'SOME_ENV': 'blah-blah'})
    self.assertTrue('blah-blah' in self.capture.text)
    self.assertEquals(ret, 0)

  def testStepEnvAdd(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd([
                  'import os; print os.environ[\'SOME_ENV\']'
                ]),
                'env': {'SOME_ENV': 'blah-blah'}
               },]
    ret = self._runAnnotator(cmdlist)
    self.assertTrue('blah-blah' in self.capture.text)
    self.assertEquals(ret, 0)

  def testStepEnvReplace(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd([
                  'import os; print os.environ[\'SOME_ENV\']'
                ]),
                'env': {'SOME_ENV': 'two'}
               },]
    ret = self._runAnnotator(cmdlist, env={'SOME_ENV': 'one'})
    self.assertTrue('two' in self.capture.text)
    self.assertEquals(ret, 0)

  def testStepEnvRemove(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd([
                  'import os\n'
                  'print \'SOME_ENV is set:\', \'SOME_ENV\' in os.environ'
                ]),
                'env': {'SOME_ENV': None}
               },]
    ret = self._runAnnotator(cmdlist, env={'SOME_ENV': 'one'})
    self.assertTrue('SOME_ENV is set: False' in self.capture.text)
    self.assertEquals(ret, 0)

  def testIgnoreAnnotations(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd(['print \'@@@SEED_STEP@blah@@@\'']),
                'ignore_annotations': True
               },]
    ret = self._runAnnotator(cmdlist)
    self.assertFalse('@@@SEED_STEP@blah@@@' in self.capture.text)
    self.assertEquals(ret, 0)


class TestMatchAnnotation(unittest.TestCase):
  class Callback(object):
    def __init__(self):
      self.called = []

    def STEP_WARNINGS(self):
      self.called.append(('STEP_WARNINGS', []))

    def STEP_LOG_LINE(self, log_name, line):
      self.called.append(('STEP_LOG_LINE', [log_name, line]))

    def STEP_LINK(self, name, url):
      self.called.append(('STEP_LINK', [name, url]))

    def STEP_CURSOR(self):  # pylint: disable=R0201
      assert False, 'STEP_CURSOR called'

    def STEP_TRIGGER(self, spec):
      self.called.append(('STEP_TRIGGER', [json.loads(spec)]))

    def SOME_OTHER_METHOD(self):  # pylint: disable=R0201
      assert False, 'SOME_OTHER_METHOD called'


  def setUp(self):
    self.c = self.Callback()

  def testNonAnnotated(self):
    annotator.MatchAnnotation('@not really an annotation', self.c)
    annotator.MatchAnnotation('@@@also not really an annotation@@', self.c)
    annotator.MatchAnnotation('#@@@totally not an annotation@@@', self.c)
    annotator.MatchAnnotation('###clearly not an annotation###', self.c)
    annotator.MatchAnnotation('@@@', self.c)
    self.assertEqual(self.c.called, [])

  def testZeroAnnotated(self):
    annotator.MatchAnnotation('@@@STEP_WARNINGS@@@', self.c)
    self.assertEqual(self.c.called, [
      ('STEP_WARNINGS', []),
    ])

  def testZeroAnnotatedCruft(self):
    with self.assertRaisesRegexp(Exception, 'cruft "@"'):
      annotator.MatchAnnotation('@@@STEP_WARNINGS@@@@', self.c)
    with self.assertRaisesRegexp(Exception, 'cruft " "'):
      annotator.MatchAnnotation('@@@STEP_WARNINGS @@@', self.c)

  def testZeroCruft(self):
    with self.assertRaisesRegexp(Exception, "cruft"):
      annotator.MatchAnnotation('@@@STEP_WARNINGS flazoo@@@', self.c)

  def testAlias(self):
    annotator.MatchAnnotation('@@@BUILD_WARNINGS@@@', self.c)
    annotator.MatchAnnotation('@@@link@foo@bar@trashcan@@@', self.c)
    self.assertEqual(self.c.called, [
      ('STEP_WARNINGS', []),
      ('STEP_LINK', ['foo', 'bar@trashcan']),
    ])

  def testWrongZero(self):
    with self.assertRaisesRegexp(Exception, "expects 1 args, got 0."):
      annotator.MatchAnnotation('@@@SEED_STEP@@@', self.c)

  def testTwoAnnotated(self):
    annotator.MatchAnnotation('@@@STEP_LOG_LINE@foo bar@ awesome line!@@@',
                              self.c)
    annotator.MatchAnnotation('@@@STEP_LOG_LINE bat fur@ cool line.@@@',
                              self.c)
    annotator.MatchAnnotation('@@@STEP_LOG_LINE@ doom cake@ok@line :/@@@',
                              self.c)
    annotator.MatchAnnotation('@@@STEP_LOG_LINE  sooper pants@ pants@@@',
                              self.c)
    annotator.MatchAnnotation('@@@STEP_LOG_LINE @@@@', self.c)
    self.assertEqual(self.c.called, [
      ('STEP_LOG_LINE', ['foo bar', ' awesome line!']),
      ('STEP_LOG_LINE', ['bat fur', ' cool line.']),
      ('STEP_LOG_LINE', [' doom cake', 'ok@line :/']),
      ('STEP_LOG_LINE', [' sooper pants', ' pants']),
      ('STEP_LOG_LINE', ['', '']),
    ])

  def testWrongTwo(self):
    with self.assertRaisesRegexp(Exception, "expects 2 args, got 0."):
      annotator.MatchAnnotation('@@@STEP_LOG_LINE@@@', self.c)
    with self.assertRaisesRegexp(Exception, "expects 2 args, got 1."):
      annotator.MatchAnnotation('@@@STEP_LOG_LINE @@@', self.c)
    with self.assertRaisesRegexp(Exception, "expects 2 args, got 1."):
      annotator.MatchAnnotation('@@@STEP_LOG_LINE@foo@@@', self.c)

  def testWrongImpl(self):
    with self.assertRaisesRegexp(TypeError, "takes exactly 1 argument"):
      annotator.MatchAnnotation('@@@STEP_CURSOR@p-pow!@@@', self.c)

  def testBadAnnotation(self):
    with self.assertRaisesRegexp(Exception, "Unrecognized annotator"):
      annotator.MatchAnnotation('@@@SOME_OTHER_METHOD@@@', self.c)

  def testMissingImpl(self):
    with self.assertRaisesRegexp(Exception, "does not implement"):
      annotator.MatchAnnotation('@@@SEED_STEP_TEXT@thingy@i like pie@@@',
                                self.c)

  def testTrigger(self):
    annotator.MatchAnnotation(
        '@@@STEP_TRIGGER {"builderNames": ["myBuilder"]}@@@',
        self.c)
    annotator.MatchAnnotation(
        ('@@@STEP_TRIGGER {"builderNames": ["myBuilder"], "set_properties":'
         '{"answer": 42}}@@@'),
        self.c)
    self.assertEqual(self.c.called, [
        ('STEP_TRIGGER', [{u'builderNames': [u'myBuilder']}]),
        ('STEP_TRIGGER', [{
            u'builderNames': [u'myBuilder'],
            u'set_properties': {u'answer': 42},
        }]),
    ])


class TestMatchAnnotationImplementation(unittest.TestCase):
  def testChromiumStepAnnotationObserver(self):
    from master.chromium_step import AnnotationObserver
    required = set(annotator.ALL_ANNOTATIONS.keys())
    implemented = set()
    for name, fn in AnnotationObserver.__dict__.iteritems():
      if name not in required:
        continue
      implemented.add(name)
      self.assertIsInstance(fn, types.FunctionType)
      expected_num_args = annotator.ALL_ANNOTATIONS[name]
      self.assertEqual(expected_num_args, fn.func_code.co_argcount - 1)
    self.assertSetEqual(required, implemented)


if __name__ == '__main__':
  unittest.main()
