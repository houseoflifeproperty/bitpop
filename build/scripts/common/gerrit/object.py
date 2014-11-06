# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from common.frozendict import frozendict
from common.gerrit.time import ParseGerritTime


# Gerrit API version
__version__ = '2.10'


class GerritObject(frozendict):
  """Base object to encapsulate and enhance immutable Gerrit REST API objects.

  Each GerritObject is instantiated from a dictionary that is directly
  deserialized from the Gerrit JSON. The GerritObject, in turn, provides
  read-only accessors to object's internal fields.
  """

  __gerrit_object_name__ = 'GerritObject'

  def __init__(self, *args, **kwargs):
    super(GerritObject, self).__init__(self._wrap(dict(*args, **kwargs)))

  @classmethod
  def _wrap(cls, value):
    """Wraps a JSON object value in a suitable immutable structure. Since JSON
    only deserializes into specific field types, this is easily scoped."""
    if isinstance(value, (dict, frozendict)):
      d = {}
      for k, v in value.iteritems():
        if not isinstance(k, basestring):
          raise TypeError("JSON key is not a string")
        d[k] = cls._wrap(v)
      return frozendict(**d)
    elif isinstance(value, (list, tuple)):
      return tuple([cls._wrap(x) for x in value])
    else:
      return value

  def __repr__(self):
    return '%s%s' % (self.name, str(self.data))

  @property
  def name(self):
    return self.__gerrit_object_name__

  @property
  def data(self):
    return self._data

  @classmethod
  def fromJsonDict(cls, json_dict):
    """Loads an instance of this class from a deserialized JSON dictionary"""
    return cls(**json_dict)


class LabelInfo(GerritObject):
  """A class that implements the Gerrit LabelInfo JSON object.

  https://gerrit-review.googlesource.com/Documentation/
    rest-api-changes.html#label-info
  """
  __gerrit_object_name__ = 'LabelInfo'

  @property
  def all(self):
    """Returns the set of 'ApprovalInfo' objects associated with this label.

    This field will only be populated if DETAILED_LABELS is specified in the
    query.

    Returns: (tuple) A tuple of 'ApprovalInfo' objects associated with the
        label
    """
    return tuple(ApprovalInfo(**ai) for ai in self.get('all', ()))

  @property
  def values(self):
    """Returns a sorted tuple of unique values (+1, +2, etc.)

    Note that a 'ChangeInfo' query must include 'DETAILED_LABELS' to contain
    this information.

    Returns: (set) A sorted tuple of label values for 'name'
    """
    values = set()
    for ai in self.all:
      value = ai.get('value')
      if value is not None:
        values.add(int(value))
    return tuple(sorted(values))

  def isApproved(self):
    """Returns 'True' if this label has an 'approved' field"""
    return ('approved' in self.keys())

  def isRejected(self):
    """Returns 'True' if this label has a 'rejected' field"""
    return ('rejected' in self.keys())

  def isRecommended(self):
    """Returns 'True' if this label has a 'recommended' field"""
    return ('recommended' in self.keys())

  def isDisliked(self):
    """Returns 'True' if this label has a 'disliked' field"""
    return ('disliked' in self.keys())


class AccountInfo(GerritObject):
  """A class that implements the Gerrit 'AccountInfo' JSON object.

  https://gerrit-review.googlesource.com/Documentation/
    rest-api-accounts.html#account-info
  """

  __gerrit_object_name__ = 'AccountInfo'


class ApprovalInfo(AccountInfo):
  """A class that implements the Gerrit 'ApprovalInfo' JSON object.

  'ApprovalInfo' has the same fields as 'AccountInfo' plus some more.

  https://gerrit-review.googlesource.com/Documentation/
    rest-api-changes.html#approval-info
  """

  __gerrit_object_name__ = 'ApprovalInfo'

  def __getitem__(self, key):
    if key == 'date':
      return self.date
    return self._data.get(key)

  @property
  def isPermitted(self):
    """Returns whether or not the user is permitted to vote on this label."""
    return (self.get('value') is not None)

  @property
  def date(self):
    value = self._data.get('date')
    if value is None:
      return None
    return ParseGerritTime(value)


class ChangeInfo(GerritObject):
  """A class that wraps a single Gerrit ChangeInfo JSON object.

  https://gerrit-review.googlesource.com/Documentation/
    rest-api-changes.html#change-info
  """
  __gerrit_object_name__ = 'ChangeInfo'


  @property
  def _revisions(self):
    """Constructs our forward-revision mapping on-demand."""
    return frozendict(
        (k, RevisionInfo(k, **v))
            for k, v in self.get('revisions', {}).iteritems())


  @property
  def _revision_number_map(self):
    """Constructs our reverse-revision mapping on-demand."""
    return frozendict(
        (v.get('_number'), v)
            for v in self._revisions.itervalues())

  @staticmethod
  def parse_id(value):
    """Returns the parsed Gerrit change ID fields.

    The Gerrit change ID takes the form: [project]~[branch]~[ID]
    Returns: (project, branch, id)
    """
    return tuple(value.split('~', 2))


  @property
  def id_tuple(self):
    """Parse the 'id' field into a (project, branch, change-id) tuple"""
    return self.parse_id(self['id'])


  @property
  def messages(self):
    """Constructs our 'messages' objects on-demand."""
    return tuple(ChangeMessageInfo(**msg)
        for msg in self.get('messages', ()))


  @property
  def unique_id(self):
    """Returns a comparable value that uniquely identifies this 'ChangeInfo'.

    The returned value is more specific than the 'id' field, which applies to
    all 'ChangeInfo's resulting from the same Gerrit issue ID.

    The composition of this is intentionally vague; external objects must
    not rely on this field's actual value. The only guarantee that this field
    offers is that it is suitable for equality comparisons to other 'unique_id'
    results.

    This field MUST NOT be used as a persistent key for this ChangeInfo.

    Returns: (object) The unique ID object for this change.
    """
    # We are assuming that no two changes for the same Gerrit ID will have the
    # same update time. If this is false, we will need to find an alternative
    # 'unique_id', but any code using it should automatically work.
    return (self.get('id'), self.get('updated'))


  @property
  def update_time(self):
    """Returns a 'datetime.datetime' corresponding to this change's 'updated'
    field. If the field was missing, this will return 'None'.

    Return: A datetime.datetime object representing the update time, or None
      if the update time is not present.

    Raises:
      ValueError if the 'updated' field could not be successfully parsed.
    """
    result = self.get('updated')
    if result is not None:
      result = ParseGerritTime(result)
    return result


  @property
  def created_time(self):
    """Returns a 'datetime.datetime' corresponding to this change's 'created'
    field. If the field was missing, this will return 'None'.

    Return: A datetime.datetime object representing the created time, or None
      if the created time is not present.

    Raises:
      ValueError if the 'created' field could not be successfully parsed.
    """
    result = self.get('created')
    if result is not None:
      result = ParseGerritTime(result)
    return result


  @property
  def revisions(self):
    """
    Calculates the latest revision ID of a given change. This will query the
    change's cached information and pull out the revision ID for the revision
    with the highest "_number" (patch set number) field.

    Returns: (tuple) An ordered tuple of 'RevisionInfo' associated with a
        change, oldest-to-newest. This will return an empty list if the change
        is unregistered or if the change has no associated revisions.
    """
    return tuple(self._revision_number_map[k]
                 for k in sorted(
                     self._revision_number_map.keys(),
                     reverse=True))

  def revisionInfoForNumber(self, value):
    """Gets the revision hash that corresponds to a patch set number.

    Args:
      value: (int) the revision number value
    Returns: (RevisionInfo/None) The RevisionInfo for 'value', or None if one
        is not defined.
    """
    return self._revision_number_map.get(value)


  @property
  def latest_revision(self):
    current_revision = self.get('current_revision')
    if current_revision is None:
      return None
    revision = self._revisions.get(current_revision)
    if revision is not None:
      return revision

    # Return an empty RevisionInfo
    return RevisionInfo(current_revision)


  @property
  def owner(self):
    owner = self.get('owner')
    if owner is not None:
      return AccountInfo(**owner)
    return None

  def label(self, name):
    """Retrieves the value of a Gerrit label field. The label field contains
    the current set of labels that this issue has applied to it along with
    associated metadata.

    Args:
      name: (str) The name of the label to retrieve (case-sensitive).
    Returns: (LabelInfo) A LabelInfo for the requested label, or None if it is
        not present.
    """
    return self.labels.get(name)

  @property
  def labels(self):
    return frozendict((label_name, LabelInfo(**label_dict))
                      for label_name, label_dict in
                          self.get('labels', {}).iteritems())


  def __repr__(self):
    return '%s{%s}' % (type(self).__name__, self.get('id'))


class ChangeMessageInfo(GerritObject):
  """Represents a 'ChangeMessageInfo' Gerrit API object"""

  __gerrit_object_name__ = 'ChangeMessageInfo'

  @property
  def date(self):
    return ParseGerritTime(self['date'])


class RevisionInfo(GerritObject):
  """Represents a 'RevisionInfo' Gerrit API object"""

  __gerrit_object_name__ = 'RevisionInfo'

  def __init__(self, revision, *args, **kwargs):
    GerritObject.__init__(self, *args, **kwargs)
    self._revision = revision

  @property
  def revision(self):
    """The revision value for this 'RevisionInfo' object"""
    return self._revision


class ReviewInput(GerritObject):
  """Interfaces with a Gerrit ReviewInput object.

  https://gerrit-review.googlesource.com/Documentation/
    rest-api-changes.html#review-input
  """

  __gerrit_object_name__ = 'ReviewInput'

  DRAFTS_DELETE = 'DELETE'
  DRAFTS_PUBLISH = 'PUBLISH'
  DRAFTS_KEEP = 'KEEP'

  NOTIFY_NONE = 'NONE'
  NOTIFY_OWNER = 'OWNER'
  NOTIFY_OWNER_REVIEWERS = 'OWNER_REVIEWERS'
  NOTIFY_ALL = 'ALL'

  @classmethod
  def New(cls, message=None, strict_labels=None, drafts=None, notify=None,
          on_behalf_of=None):
    """Constructs a new Gerrit ReviewInput object from a set of composite
    fields.

    Args:
      message: (str) If supplied, the review input message.
      strict_labels (bool): If supplied, a boolean for 'strict_labels'
      drafts: (str) If supplied, one of the 'DRAFTS_*' strings belongining to
          this class.
      notify: (str) If supplied, one of the 'NOTIFY_*' trings belonging to
          this class.
      on_behalf_of: (str) If supplied, the 'on_behalf_of' field value.

    Returns: (ReviewInput) A ReviewInput instance.
    """
    review_info_dict = {}

    def addIfPopulated(key, value, map_fn=None):
      if value is not None:
        if map_fn is not None:
          value = map_fn(value)
        review_info_dict[key] = value

    addIfPopulated('message', message)
    addIfPopulated('strict_labels', strict_labels, map_fn=bool)
    addIfPopulated('drafts', drafts)
    addIfPopulated('notify', notify)
    addIfPopulated('on_behalf_of', on_behalf_of)
    return cls(**review_info_dict)

  def addLabel(self, label, value):
    """Adds a label/value pair

    Args:
      label: (str) the name of the label (e.g., 'Code-Review')
      value: (int) the label value (e.g., -1)
    Returns: (ReviewInput) A new ReviewInput with the specified labels set.
    """
    nlabels = self.get('labels')
    if nlabels is None:
      nlabels = {}
    else:
      nlabels = nlabels.mutableDict()
    nlabels[label] = value
    return self.extend(labels=nlabels)


class ReviewInfo(GerritObject):
  """Wrapper class for the ReviewInfo object.

  https://gerrit-review.googlesource.com/Documentation/
  rest-api-changes.html#review-info
  """

  __gerrit_object_name__ = 'ReviewInfo'
