from slave import recipe_test_api

class TryserverTestApi(recipe_test_api.RecipeTestApi):
  def download_patch(self, cwd=None):
    return self.m.raw_io.output('fake patch.diff contents')
