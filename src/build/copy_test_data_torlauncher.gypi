{
  'inputs': [
    # The |-o <(test_data_prefix)| is ignored; it is there to work around a
    # caching bug in gyp (https://code.google.com/p/gyp/issues/detail?id=112).
    # It caches command output when the string is the same, so if two copy
    # steps have the same relative paths, there can be bogus cache hits that
    # cause compile failures unless something varies.
    '<!@pymod_do_main(copy_test_data_torlauncher -o <(test_data_prefix) --inputs <(test_data_files))',
  ],
  'outputs': [
    '<!@pymod_do_main(copy_test_data_torlauncher -o <(PRODUCT_DIR)/<(test_data_prefix) --outputs <(test_data_files))',
  ],
  'action': [
    'python',
    '<(DEPTH)/build/copy_test_data_torlauncher.py',
    '-o', '<(PRODUCT_DIR)/<(test_data_prefix)',
    '<@(test_data_files)',
  ],
}
