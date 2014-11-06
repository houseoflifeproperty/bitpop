# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import urllib

################################################################################
# Gerrit API
################################################################################

class QueryBuilder(object):
  """Class to iteratively construct a Gerrit query string.

  This functions as a helper class to simplify explicit versus implicit
  quoting and nesting of Gerrit query strings.

  Gerrit query semantics are documented here:
  https://gerrit-review.googlesource.com/Documentation/user-search.html
  """

  def __init__(self, terms, operator):
    """
    Initializes a Gerrit query object. This should not be used directly;
    instead, one of the supplied constructors (New, NewOR, NewAND) should be
    used to create a new builder.

    Args:
      terms: (list) A list of explicit query parameters to start with. If
          'terms' is an existing Query instance, the current instance will be
          initialized as a clone.
      operator: (str) If not 'None', this term will be implicitly added after
          each explicit query term. Suggested values are 'AND' and 'OR'.
    """
    self._terms = tuple(terms)
    self._operator = operator

  @classmethod
  def _New(cls, terms, operator=None):
    return cls(
        [cls._prepareTerm(t) for t in terms],
        operator)

  @classmethod
  def New(cls, *terms):
    return cls._New(terms)

  @classmethod
  def NewOR(cls, *terms):
    return cls._New(terms, operator='OR')

  @classmethod
  def NewAND(cls, *terms):
    return cls._New(terms, operator='AND')

  @classmethod
  def _prepareTerm(cls, value):
    """Analyze the type of 'value' and generates a term from it (see 'add()')"""
    if isinstance(value, basestring):
      parts = value.split(':', 1)
      if len(parts) == 2:
        return cls._prepareSelector(parts[0], parts[1])
      else:
        return cls._prepareString(value, quoted=True)
    if isinstance(value, QueryBuilder):
      # Return its query verbatim, enclosed in parenthesis
      return list(value.termiter())

    # Try iterator
    it = None
    try:
      it = iter(value)
    except TypeError:
      pass
    if it is not None:
      return tuple(cls._prepareTerm(x) for x in it)

    # Default to stringify
    return cls._prepareString(str(value), quoted=True)

  @classmethod
  def _prepareString(cls, value, quoted=False):
    """Constructs a string term."""
    if quoted:
      value = urllib.quote(value)
    return value

  @classmethod
  def _prepareSelector(cls, key, value):
    """Constructs a selector (e.g., 'label:Code-Review+1') term"""
    # Quote key/value individually; the colon does not get quoted
    return '%s:%s' % (
        cls._prepareString(key, quoted=True),
        cls._prepareString(value, quoted=True))

  def _cloneWithTerms(self, *terms):
    """Creates a new 'QueryBuilder' with an augmented term set."""
    new_terms = self._terms + terms
    return self.__class__(new_terms, self._operator)

  def add(self, *values):
    """Adds a new query term to the Query.

    This is a generic 'add' function that infers how to add 'value' based on
    its type and contents. For more specific control, use the specialised
    'add*' functions.

    The query term ('value') may be any of the following:
      - A key:value term, in which case the key and value are quoted but the
      colon is left unquoted.
      - A single term string, in which case the entire term is quoted
      - A QueryBuilder instance, in which case it is embedded as a single term
        bounded by parenthesis.
      - An iterable of query terms, in which case each term will be formatted
        recursively and placed inside parenthesis.

    Args:
      values: The query term to add (see above).
    Returns: (Query) this Query object
    """
    terms = []
    for value in values:
      term = self._prepareTerm(value)
      if term is not None:
        terms.append(term)
    if len(terms) == 0:
      return self
    return self._cloneWithTerms(*terms)

  def addSelector(self, key, value):
    """Adds a 'key:value' term to the query.

    The 'key' and 'value' terms will be URL quoted.

    Args:
      key: (str) the key
      value: (str) the value
    Returns: (Query) this Query object
    """
    return self._cloneWithTerms(self._prepareSelector(key, value))

  def addQuoted(self, value):
    """Adds a URL-quoted term to the query.

    Args:
      value: (str) the value to quote and add
    Returns: (Query) this Query object
    """
    return self._cloneWithTerms(self._prepareString(value, quoted=True))

  def addUnquoted(self, value):
    """Directly adds a term to the query.

    Args:
      value: (str) the value to add
    Returns: (Query) this Query object
    """
    return self._cloneWithTerms(self._prepareString(value, quoted=False))

  @classmethod
  def _formatQuery(cls, terms):
    """Recursive method to convert internal nested string/list to a query"""
    formatted_terms = []
    for term in terms:
      if isinstance(term, (list, tuple)):
        if len(term) == 0:
          continue
        term = '(%s)' % (cls._formatQuery(term))
      formatted_terms.append(term)
    return '+'.join(formatted_terms)

  def termiter(self):
    """Iterator overload to iterate over individual query terms"""
    first = True
    for param in self._terms:
      if first:
        first = False
      elif self._operator is not None:
        yield self._operator
      yield param

  def __len__(self):
    """Returns: (int) the number of explicit query terms"""
    return len(self._terms)

  def __str__(self):
    """Constructs a URL-quoted query string from this query's terms"""
    return self._formatQuery(self.termiter())

