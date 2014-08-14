#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import optparse
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.append(os.path.join(BASE_DIR, 'scripts'))
sys.path.append(os.path.join(BASE_DIR, 'site_config'))

from common import archive_utils


DIR_LIST = ['foo',
            os.path.join('fee', 'foo'),
            os.path.join('fee', 'faa'),
            os.path.join('fee', 'fie'),
            os.path.join('foo', 'fee', 'faa')]

TEMP_FILES = ['foo.txt',
              'bar.txt',
              os.path.join('foo', 'buzz.txt'),
              os.path.join('foo', 'bing'),
              os.path.join('fee', 'foo', 'bar'),
              os.path.join('fee', 'faa', 'bar'),
              os.path.join('fee', 'fie', 'fo'),
              os.path.join('foo', 'fee', 'faa', 'boo.txt')]

TEMP_FILES_WITH_WILDCARDS = ['foo.txt',
                             'bar.txt',
                             os.path.join('foo', '*'),
                             os.path.join('fee', '*', 'bar'),
                             os.path.join('fee', '*', 'fo'),
                             os.path.join('foo', 'fee', 'faa', 'boo.txt')]

# Sample FILES.cfg-style contents.
TEST_FILES_CFG = [
  {
    'filename': 'allany.txt',
    'arch': ['32bit', '64bit', 'arm'],
    'buildtype': ['dev', 'official'],
    'filegroup': ['default', 'allany'],
  },
  {
    'filename': 'allany2.txt',
    'buildtype': ['dev', 'official'],
    'filegroup': ['default', 'allany'],
  },
  {
    'filename': 'subdirectory/allany.txt',
    'arch': ['32bit', '64bit'],
    'buildtype': ['dev', 'official'],
    'filegroup': ['default', 'allany'],
  },
  {
    'filename': 'official64.txt',
    'arch': ['64bit'],
    'buildtype': ['official'],
  },
  {
    'filename': 'dev32.txt',
    'arch': ['32bit'],
    'buildtype': ['dev'],
  },
  {
    'filename': 'archive_allany.txt',
    'arch': ['32bit', '64bit'],
    'buildtype': ['dev', 'official'],
    'archive': 'static_archive.zip',
    'filegroup': ['default', 'allany'],
  },
  {
    'filename': 'subdirectory/archive_allany.txt',
    'arch': ['32bit', '64bit'],
    'buildtype': ['dev', 'official'],
    'archive': 'static_archive.zip',
    'filegroup': ['default', 'allany'],
  },
  {
    'filename': 'subdirectory/archive_dev32.txt',
    'arch': ['32bit'],
    'buildtype': ['dev'],
    'archive': 'static_archive.zip',
  },
  {
    'filename': 'allany_dev_optional.txt',
    'arch': ['32bit', '64bit'],
    'buildtype': ['dev', 'official'],
    'optional': ['dev'],
    'filegroup': ['default', 'allany'],
  },
  {
    'filename': 'dev64_direct_archive.txt',
    'arch': ['64bit'],
    'buildtype': ['dev'],
    'archive': 'renamed_direct_archive.txt',
    'direct_archive': 1,
  },
  {
    'filename': 'dev64_implied_direct_archive.txt',
    'arch': ['64bit'],
    'buildtype': ['dev'],
    'archive': 'dev64_implied_direct_archive.txt',
  },
]


def CreateTestFilesCfg(path):
  files_cfg = os.path.join(path, archive_utils.FILES_FILENAME)
  f = open(files_cfg, 'w')
  f.write('FILES = %s' % str(TEST_FILES_CFG))
  f.close()
  return files_cfg


def CreateFileSetInDir(out_dir, file_list):
  for f in file_list:
    dir_part = os.path.dirname(f)
    if dir_part:
      dir_path = os.path.join(out_dir, dir_part)
      if not os.path.exists(dir_path):
        os.makedirs(dir_path)

    temp_file = open(os.path.join(out_dir, f), 'w')
    temp_file.write('contents')
    temp_file.close()


def BuildTestFilesTree(test_path):
  for temp_file in TEMP_FILES:
    temp_path = os.path.join(test_path, temp_file)
    dir_name = os.path.dirname(temp_path)

    if not os.path.exists(temp_path):
      relative_dir_name = os.path.dirname(temp_file)
      if relative_dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)
      open(temp_path, 'a')


def FetchSvn(cfg_path, svn=None):
  if not svn:
    svn = pysvn.Client()
  f, files_cfg = tempfile.mkstemp()
  os.write(f, svn.cat(cfg_path))
  os.close(f)
  return files_cfg


def DiffFilesCfg(cfg_path, svn):
  """Parse local FILES.cfg and show changes so they can be manually verified."""

  print '\nDiff parsing "%s" ...' % cfg_path
  d = difflib.Differ()
  def CompareLists(svnlist, newlist, msg):
    diffs = []
    for x in d.compare(svnlist, newlist):
      if x.startswith('- '):
        diffs.append('  DELETION: %s' % x[2:])
      elif x.startswith('+ '):
        diffs.append('  ADDITION: %s' % x[2:])
    if diffs:
      print msg
      print '\n'.join(diffs)

  svn_cfg = FetchSvn(RealFilesCfgTest.SVNBASE + cfg_path, svn)
  svnparser = archive_utils.FilesCfgParser(svn_cfg, None, None)
  os.unlink(svn_cfg)
  newparser = archive_utils.FilesCfgParser(options.src_base + cfg_path, None,
                                           None)

  # Determine the "parsable values" in the two versions.
  archs = []
  buildtypes = []
  groups = []
# pylint: disable=W0212
  for item in newparser._files_cfg + svnparser._files_cfg:
# pylint: enable=W0212
    if item.get('arch'):
      archs.extend(item['arch'])
    if item.get('buildtype'):
      buildtypes.extend(item['buildtype'])
    if item.get('filegroup'):
      groups.extend(item['filegroup'])
  archs = set(archs)
  buildtypes = set(buildtypes)
  groups = set(groups)

  # Legacy list handling (i.e. default filegroup).
  print '\nChecking ParseLegacyList() ...'
  for arch, buildtype in itertools.product(archs, buildtypes):
    msg = '%s:%s' % (arch, buildtype)
    newparser.arch = svnparser.arch = arch
    newparser.buildtype = svnparser.buildtype = buildtype
    svn_legacy_list = svnparser.ParseLegacyList()
    new_legacy_list = newparser.ParseLegacyList()
    CompareLists(svn_legacy_list, new_legacy_list, msg)

  print '\nChecking ParseGroup() ...'
  for group, arch, buildtype in itertools.product(groups, archs, buildtypes):
    msg = '%s:%s:%s' % (group, arch, buildtype)
    newparser.arch = svnparser.arch = arch
    newparser.buildtype = svnparser.buildtype = buildtype
    svn_group_list = svnparser.ParseGroup(group)
    new_group_list = newparser.ParseGroup(group)
    CompareLists(svn_group_list, new_group_list, msg)

  print '\nChecking Archives() ...'
  for arch, buildtype in itertools.product(archs, buildtypes):
    newparser.arch = svnparser.arch = arch
    newparser.buildtype = svnparser.buildtype = buildtype
    svn_archive_lists = svnparser.ParseArchiveLists()
    new_archive_lists = newparser.ParseArchiveLists()
    archives = set(svn_archive_lists.keys() + new_archive_lists.keys())
    for archive in archives:
      msg = '%s:%s:%s' % (archive, arch, buildtype)
      CompareLists([x['filename'] for x in svn_archive_lists.get(archive, [])],
                   [x['filename'] for x in new_archive_lists.get(archive, [])],
                   msg)


class ArchiveUtilsTest(unittest.TestCase):

  def setUp(self):
    self.temp_dir = tempfile.mkdtemp()
    self.src_dir = os.path.join(self.temp_dir, 'src')
    self.build_dir = os.path.join(self.temp_dir, 'build')
    self.tool_dir = os.path.join(self.src_dir, 'tools')
    os.makedirs(self.src_dir)
    os.makedirs(self.build_dir)
    os.makedirs(self.tool_dir)

  def tearDown(self):
    shutil.rmtree(self.temp_dir)

  # copied from python2.7 version of unittest
  # TODO(sbc): remove once python2.7 is required.
  def assertIn(self, member, container, msg=None):
    """Just like self.assertTrue(a in b), but with a nicer default message."""
    if member not in container:
      standardMsg = '%s not found in %s' % (repr(member),
                                            repr(container))
      self.fail(self._formatMessage(msg, standardMsg))

  # copied from python2.7 version of unittest
  # TODO(sbc): remove once python2.7 is required.
  def assertNotIn(self, member, container, msg=None):
    """Just like self.assertTrue(a not in b), but with a nicer default
    message."""
    if member in container:
      standardMsg = '%s unexpectedly found in %s' % (repr(member),
                                                     repr(container))
      self.fail(self._formatMessage(msg, standardMsg))

  def verifyZipFile(self, zip_dir, zip_file_path, archive_name, expected_files):
    # Extract the files from the archive
    extract_dir = os.path.join(zip_dir, 'extract')
    os.makedirs(extract_dir)
    zip_file = zipfile.ZipFile(zip_file_path)
    # The extractall method is supported from V2.6
    if hasattr(zip_file, 'extractall'):
      zip_file.extractall(extract_dir)  # pylint: disable=E1101
      # Check that all expected files are there
      def FindFiles(arg, dirname, names):
        subdir = dirname[len(arg):].strip(os.path.sep)
        extracted_files.extend([os.path.join(subdir, name) for name in names if
                                os.path.isfile(os.path.join(dirname, name))])
      extracted_files = []
      archive_path = os.path.join(extract_dir, archive_name)
      os.path.walk(archive_path, FindFiles, archive_path)
      self.assertEquals(len(expected_files), len(extracted_files))
      for f in extracted_files:
        self.assertIn(f, expected_files)
    else:
      test_result = zip_file.testzip()
      self.assertTrue(not test_result)

    zip_file.close()

  def testParseFilesList(self):
    files_cfg = CreateTestFilesCfg(self.temp_dir)
    arch = '64bit'
    buildtype = 'official'
    files_list = archive_utils.ParseFilesList(files_cfg, buildtype, arch)
    # Verify FILES.cfg was parsed correctly.
    for i in TEST_FILES_CFG:
      if buildtype not in i['buildtype']:
        continue
      if i.get('arch') and arch not in i['arch']:
        continue
      # 'archive' flagged files shouldn't be included in the default parse.
      if i.get('archive'):
        self.assertNotIn(i['filename'], files_list)
      else:
        self.assertIn(i['filename'], files_list)
        files_list.remove(i['filename'])
        # No duplicate files.
        self.assertEqual(files_list.count(i['filename']), 0)
    # No unexpected files.
    self.assertEqual(len(files_list), 0)

  def testParseLegacyList(self):
    files_cfg = CreateTestFilesCfg(self.temp_dir)
    arch = '64bit'
    buildtype = 'official'
    fparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    files_list = fparser.ParseLegacyList()
    # Verify FILES.cfg was parsed correctly.
    for i in TEST_FILES_CFG:
      if buildtype not in i['buildtype']:
        continue
      if i.get('arch') and arch not in i['arch']:
        continue
      # 'archive' flagged files shouldn't be included in the default parse.
      if i.get('archive'):
        self.assertNotIn(i['filename'], files_list)
      else:
        self.assertIn(i['filename'], files_list)
        files_list.remove(i['filename'])
        # No duplicate files.
        self.assertEqual(files_list.count(i['filename']), 0)
    # No unexpected files.
    self.assertEqual(len(files_list), 0)

  def testParseArchiveLists(self):
    ARCHIVENAME = 'static_archive.zip'
    files_cfg = CreateTestFilesCfg(self.temp_dir)
    arch = '64bit'
    buildtype = 'official'
    fparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    archives = fparser.ParseArchiveLists()
    self.assertEqual(archives.keys(), [ARCHIVENAME])
    self.assertEqual([x['filename'] for x in archives[ARCHIVENAME]],
                     ['archive_allany.txt', 'subdirectory/archive_allany.txt'])

    # 32bit dev has additional files under the same archive name.
    arch = '32bit'
    buildtype = 'dev'
    fparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    archives = fparser.ParseArchiveLists()
    self.assertEqual(archives.keys(), [ARCHIVENAME])
    self.assertEqual([x['filename'] for x in archives[ARCHIVENAME]],
                     ['archive_allany.txt', 'subdirectory/archive_allany.txt',
                      'subdirectory/archive_dev32.txt'])

  def testOptionalFiles(self):
    files_cfg = CreateTestFilesCfg(self.temp_dir)
    optional_fn = 'allany_dev_optional.txt'
    arch = '64bit'
    buildtype = 'dev'
    fparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    self.assertTrue(fparser.IsOptional(optional_fn))

    # It's only optional for 'dev' builds.
    buildtype = 'official'
    fparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    self.assertFalse(fparser.IsOptional(optional_fn))

  def testDirectArchive(self):
    files_cfg = CreateTestFilesCfg(self.temp_dir)
    arch = '64bit'
    buildtype = 'dev'
    fparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    archives = fparser.ParseArchiveLists()
    self.assertTrue(fparser.IsDirectArchive(
        archives['renamed_direct_archive.txt']))
    self.assertTrue(fparser.IsDirectArchive(
        archives['dev64_implied_direct_archive.txt']))
    self.assertFalse(fparser.IsDirectArchive(archives['static_archive.zip']))

  def testParserChange(self):
    """Changing parser criteria should be the same as creating a new one."""
    files_cfg = CreateTestFilesCfg(self.temp_dir)
    arch = '64bit'
    buildtype = 'dev'
    oldfparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    old_dev_list = oldfparser.ParseLegacyList()
    buildtype = 'official'
    oldfparser.buildtype = buildtype
    old_official_list = oldfparser.ParseLegacyList()
    # The changed parser should return different ParseLegacyList.
    self.assertNotEqual(sorted(old_dev_list), sorted(old_official_list))

    newfparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    new_official_list = newfparser.ParseLegacyList()
    # The new parser and changed parser should return the same data.
    self.assertEqual(sorted(old_official_list), sorted(new_official_list))
    old_allany_list = oldfparser.ParseGroup('allany')
    new_allany_list = oldfparser.ParseGroup('allany')
    self.assertEqual(sorted(old_allany_list), sorted(new_allany_list))

  def testExtractDirsFromPaths(self):
    path_list = TEMP_FILES[:]
    expected_dir_list = DIR_LIST[:]
    expected_dir_list.sort()

    dir_list = archive_utils.ExtractDirsFromPaths(path_list)
    dir_list.sort()
    self.assertEquals(expected_dir_list, dir_list)

  def testExpandWildcards(self):
    path_list = TEMP_FILES_WITH_WILDCARDS[:]
    expected_path_list = TEMP_FILES[:]
    expected_path_list.sort()

    BuildTestFilesTree(self.temp_dir)

    expanded_path_list = archive_utils.ExpandWildcards(self.temp_dir, path_list)
    expanded_path_list.sort()
    self.assertEquals(expected_path_list, expanded_path_list)

  def testCreateArchive(self):
    files_cfg = CreateTestFilesCfg(self.tool_dir)
    CreateFileSetInDir(self.build_dir, [i['filename'] for i in TEST_FILES_CFG])
    archive_name = 'test'
    arch = '64bit'
    buildtype = 'official'
    fparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    files_list = fparser.ParseLegacyList()
    zip_dir, zip_file_path = archive_utils.CreateArchive(
        self.build_dir , self.temp_dir, files_list, archive_name)
    self.assertTrue(zip_dir)
    self.assertTrue(zip_file_path)
    self.assertTrue(os.path.exists(zip_file_path))
    self.assertEqual(os.path.basename(zip_file_path), archive_name)
    self.verifyZipFile(zip_dir, zip_file_path, os.path.basename(zip_dir),
                       files_list)

    # Creating the archive twice is wasteful, but shouldn't fail (e.g. due to
    # conflicts with existing zip_dir or zip_file_path). This also tests the
    # condition on the bots where they don't clean up their staging directory
    # between runs.
    zip_dir, zip_file_path = archive_utils.CreateArchive(
        self.build_dir, self.temp_dir, files_list, archive_name)
    self.assertTrue(zip_dir)
    self.assertTrue(zip_file_path)
    self.assertTrue(os.path.exists(zip_file_path))
    self.verifyZipFile(zip_dir, zip_file_path, os.path.basename(zip_dir),
                       files_list)

  def testCreateZipExtArchive(self):
    files_cfg = CreateTestFilesCfg(self.tool_dir)
    CreateFileSetInDir(self.build_dir, [i['filename'] for i in TEST_FILES_CFG])
    archive_name = 'test_with_ext.zip'
    arch = '64bit'
    buildtype = 'official'
    fparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    files_list = fparser.ParseLegacyList()
    zip_dir, zip_file_path = archive_utils.CreateArchive(
        self.build_dir , self.temp_dir, files_list, archive_name)
    self.assertTrue(zip_dir)
    self.assertTrue(zip_file_path)
    self.assertTrue(os.path.exists(zip_file_path))
    self.assertEqual(os.path.basename(zip_file_path), archive_name)
    self.verifyZipFile(zip_dir, zip_file_path, os.path.basename(zip_dir),
                       files_list)

    # Creating the archive twice is wasteful, but shouldn't fail (e.g. due to
    # conflicts with existing zip_dir or zip_file_path). This also tests the
    # condition on the bots where they don't clean up their staging directory
    # between runs.
    zip_dir, zip_file_path = archive_utils.CreateArchive(
        self.build_dir, self.temp_dir, files_list, archive_name)
    self.assertTrue(zip_dir)
    self.assertTrue(zip_file_path)
    self.assertTrue(os.path.exists(zip_file_path))
    self.verifyZipFile(zip_dir, zip_file_path, os.path.basename(zip_dir),
                       files_list)

  def testCreateEmptyArchive(self):
    files_cfg = CreateTestFilesCfg(self.tool_dir)
    archive_name = 'test_empty'
    arch = '64bit'
    buildtype = 'nosuchtype'
    fparser = archive_utils.FilesCfgParser(files_cfg, buildtype, arch)
    files_list = fparser.ParseLegacyList()
    zip_dir, zip_file_path = archive_utils.CreateArchive(
        self.build_dir , self.temp_dir, files_list, archive_name)
    self.assertFalse(zip_dir)
    self.assertFalse(zip_file_path)
    self.assertFalse(os.path.exists(zip_file_path))


class RealFilesCfgTest(unittest.TestCase):
  """Basic sanity checks for the real FILES.cfg files."""

  SVNBASE = 'svn://svn.chromium.org/chrome/trunk/src'
  WIN_PATH = '/chrome/tools/build/win/FILES.cfg'
  LINUX_PATH = '/chrome/tools/build/linux/FILES.cfg'
  MAC_PATH = '/chrome/tools/build/mac/FILES.cfg'
  CROS_PATH = '/chrome/tools/build/chromeos/FILES.cfg'

  def setUp(self):
    self.files_cfg = None
    self.svn = pysvn.Client()

  def tearDown(self):
    if self.files_cfg:
      os.unlink(self.files_cfg)

  def ParseFilesCfg(self, cfg_path):
    if cfg_path.startswith('svn://'):
      # Store the svn file so it will be automatically cleaned up in tearDown().
      self.files_cfg = FetchSvn(cfg_path, self.svn)
      cfg_path = self.files_cfg

    # There should always be some 32bit, official and dev files (otherwise
    # there's nothing to archive).
    arch = '32bit'
    buildtype = 'official'
    fparser = archive_utils.FilesCfgParser(cfg_path, buildtype, arch)
    files_list = fparser.ParseLegacyList()
    self.assertTrue(files_list)
    fparser.buildtype = 'dev'
    files_list = fparser.ParseLegacyList()
    self.assertTrue(files_list)

    # Arbitrary buildtype shouldn't return anything.
    fparser.buildtype = 'bogus'
    files_list = fparser.ParseLegacyList()
    self.assertFalse(files_list)

    # Check for incomplete/incorrect settings.
    # buildtype must exist and be in ['dev', 'official']
    self.assertFalse([f for f in fparser._files_cfg # pylint: disable=W0212
        if not f['buildtype']
        or set(f['buildtype']) - set(['dev', 'official'])])

  def testWinParse(self):
    self.ParseFilesCfg(options.src_base + RealFilesCfgTest.WIN_PATH)

  def testWinParseSymbols(self):
    files_cfg = options.src_base + RealFilesCfgTest.WIN_PATH

    # There should be some official build symbols.
    fparser = archive_utils.FilesCfgParser(files_cfg, 'official', '32bit')
    official_list = fparser.ParseGroup('symsrc')
    self.assertTrue(official_list)

    # Windows symbols should be the same regardless of arch.
    fparser = archive_utils.FilesCfgParser(files_cfg, 'official', '64bit')
    official64_list = fparser.ParseGroup('symsrc')
    self.assertEqual(official64_list, official_list)

  def testMacParse(self):
    self.ParseFilesCfg(options.src_base + RealFilesCfgTest.MAC_PATH)

  def testLinuxParse(self):
    self.ParseFilesCfg(options.src_base + RealFilesCfgTest.LINUX_PATH)

  def testChromeosParse(self):
    self.ParseFilesCfg(options.src_base + RealFilesCfgTest.CROS_PATH)


if __name__ == '__main__':
  option_parser = optparse.OptionParser()
  option_parser.add_option('--realfiles', action='store_true',
      help='Also run tests on FILES.cfg files from chromium sources.')
  option_parser.add_option('--realfiles-only', action='store_true',
      help='Only run tests on FILES.cfg files from chromium sources.')
  option_parser.add_option('--src-base', default=RealFilesCfgTest.SVNBASE,
      help='Base file or svn path to the chromium sources.')
  option_parser.add_option('--diffparse', action='store_true',
      help='Compare parsing local FILES.cfg and latest SVN version. '
           '(Requires a --realfiles* and --src-base flag.) '
           'Use this to make sure any changes in file groupings, archive '
           'contents, etc. are intentional.')
  options, unused_args = option_parser.parse_args()

  errors = False
  if not options.realfiles_only:
    suite = unittest.TestLoader().loadTestsFromTestCase(ArchiveUtilsTest)
    # Run with a bit more output.
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not errors:
      errors = not result.wasSuccessful()

  # These tests are a little slow due to the svn download, so only run them if
  # explicitly requested.
  if options.realfiles or options.realfiles_only:
    import pysvn  # pylint: disable=F0401
    suite = unittest.TestLoader().loadTestsFromTestCase(RealFilesCfgTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not errors:
      errors = not result.wasSuccessful()

    if options.diffparse:
      import difflib # pylint: disable=F0401
      import itertools # pylint: disable=F0401
      if options.src_base == RealFilesCfgTest.SVNBASE:
        print ('WARNING: --diffparse requires --src-base set to your local src '
               'path. Skipping because nothing to compare.')
      else:
        # Turn off stdout buffering to allow progress messages during slow svn.
        sys.stdout.flush()
        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        svn_client = pysvn.Client()
        DiffFilesCfg(RealFilesCfgTest.WIN_PATH, svn_client)
        DiffFilesCfg(RealFilesCfgTest.LINUX_PATH, svn_client)
        DiffFilesCfg(RealFilesCfgTest.MAC_PATH, svn_client)
        DiffFilesCfg(RealFilesCfgTest.CROS_PATH, svn_client)

  # Specify error return so caller (e.g. shell script) can easily detect
  # failures.
  sys.exit(errors)
