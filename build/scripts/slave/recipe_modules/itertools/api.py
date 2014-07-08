from slave import recipe_api

import itertools

class ItertoolsApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(ItertoolsApi, self).__init__(**kwargs)
    for name, obj in itertools.__dict__.iteritems():
      if name[0] == '_':
        continue
      setattr(self, name, obj)
