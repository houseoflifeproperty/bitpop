from slave import recipe_test_api

class TryserverTestApi(recipe_test_api.RecipeTestApi):
  def patch_content(self):
    return self.m.raw_io.output(
        'fake patch.diff content (line 1)\n'
        'fake patch.diff content (line 2)\n')

  def patch_content_windows(self):
    return self.m.raw_io.output(
        'fake patch.diff content for Windows (line 1)\r\n'
        'fake patch.diff content for Windows (line 2)\r\n')
