from RECIPE_MODULES.gclient import CONFIG_CTX


@CONFIG_CTX()
def skia(c):
  soln = c.solutions.add()
  soln.name = 'skia'
  soln.url = 'https://skia.googlesource.com/skia.git'
  c.got_revision_mapping['skia'] = 'got_revision'
