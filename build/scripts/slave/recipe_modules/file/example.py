# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


DEPS = [
  'file',
  'path',
  'raw_io',
]


TEST_CONTENTS = {
  'simple': 'abcde',
  'spaces': 'abcde fgh',
  'symbols': '! ~&&',
  'multiline': '''ab
cd
efg
''',
}


def GenSteps(api):
  for name, content in TEST_CONTENTS.iteritems():
    api.file.write('write_%s' % name, 'tmp_file.txt', content)
    actual_content = api.file.read(
        'read_%s' % name, 'tmp_file.txt',
        test_data=content
    )
    msg = 'expected %s but got %s' % (content, actual_content)
    assert actual_content == content, msg

  # copytree
  content = 'some file content'
  tmp_dir = api.path['slave_build'].join('copytree_example_tmp')
  api.path.makedirs('makedirs', tmp_dir)
  path = tmp_dir.join('dummy_file')
  api.file.write('write %s' % path, path, content)
  new_tmp = api.path['slave_build'].join('copytree_example_tmp2')
  new_path = new_tmp.join('dummy_file')
  api.file.copytree('copytree', tmp_dir, new_tmp)
  actual_content = api.file.read('read %s' % new_path, new_path,
                                 test_data=content)
  api.path.rmtree('cleanup', tmp_dir)
  api.path.rmtree('cleanup2', new_tmp)
  assert actual_content == content


def GenTests(api):
  yield api.test('file_io')

