from slave import recipe_test_api

class AOSPTestApi(recipe_test_api.RecipeTestApi):
  def calculate_blacklist(self):
    return self.m.json.output({
      'blacklist': [
        'blacklist/project/1',
        'blacklist/project/2',
      ]
    })

