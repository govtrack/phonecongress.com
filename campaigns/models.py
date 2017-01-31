from django.db import models
from django.contrib.auth.models import AbstractUser

from jsonfield import JSONField

from phonecongress.models import User

class Campaign(models.Model):
  """A Campaign is a call to action for users. Each user can participate in a Campaign just once."""

  owner = models.ForeignKey(User, related_name="campaigns", help_text="The User that owns the Campaign.")
  title = models.CharField(max_length=128, help_text="The display name of the Campaign.")
  active = models.BooleanField(default=False, help_text="Whether this campaign is currently running.")

  created = models.DateTimeField(auto_now_add=True, db_index=True)
  updated = models.DateTimeField(auto_now=True, db_index=True)
  extra = JSONField(blank=True, default={}, help_text="Additional information stored with this object.")

  def __str__(self):
    return self.title + " (by " + str(self.owner) + ")"

  def get_action(self, user_props):
    from .actions import select_action
    actions = [
      action.action_type.render(action, user_props)
      for action in self.actions.all()]
    return select_action(actions, user_props)

class ActionType(models.Model):
  """A type of Action that a user can take. ActionTypes are immutable since they are associated with Actions that users have taken."""

  owner = models.ForeignKey(User, related_name="action_types", help_text="The User that created the ActionType.")
  title = models.CharField(max_length=128, help_text="The display name of the ActionType.")

  specification = JSONField(blank=True, default={}, help_text="Data on what this ActionType is actually about.")

  created = models.DateTimeField(auto_now_add=True, db_index=True)
  updated = models.DateTimeField(auto_now=True, db_index=True)
  extra = JSONField(blank=True, default={}, help_text="Additional information stored with this object.")

  def __str__(self):
    return self.title + " (by " + str(self.owner) + ")"

  def render(self, action, user_props):
    # Render campaign info for this action type, given user properties
    # and an Action. The render function is stored in a separate module.
    import importlib
    module_name, function_name = self.specification['type'].rsplit(".", 1)
    render_func = getattr(importlib.import_module(module_name), function_name)
    return render_func(self.specification, action.specification, user_props)

class Action(models.Model):
  """An Action is a particular activity a user can take when taking action for a Campaign. Actions segment users. They should not be modified once users have taken action on them."""

  campaign = models.ForeignKey(Campaign, related_name="actions", help_text="The Campaign that this Action is a part of.")
  title = models.CharField(max_length=128, help_text="A brief summary of the Action.")
  action_type = models.ForeignKey(ActionType, related_name="actions", help_text="The ActionType that specifies what sort of action this is.")

  specification = JSONField(blank=True, default={}, help_text="Data that is interpreted by the ActionType for generating call scripts, etc.")

  created = models.DateTimeField(auto_now_add=True, db_index=True)
  updated = models.DateTimeField(auto_now=True, db_index=True)
  extra = JSONField(blank=True, default={}, help_text="Additional information stored with this object.")

  def __str__(self):
    return str(self.campaign) + ": " + self.title + " (" + str(self.action_type) + ")"

class UserAction(models.Model):
  """A UserAction records when a User has taken an Action"""

  user = models.ForeignKey(User, related_name="actions", help_text="The User that took this action.")
  action = models.ForeignKey(Action, related_name="useractions", help_text="The Action that was taken.")

  details = JSONField(blank=True, default={}, help_text="Data that is filled in by the ActionType for generating call scripts, etc.")
  state = models.CharField(blank=True, null=True, max_length=16, help_text="The status of the Action.")

  created = models.DateTimeField(auto_now_add=True, db_index=True)
  updated = models.DateTimeField(auto_now=True, db_index=True)
  extra = JSONField(blank=True, default={}, help_text="Additional information stored with this object.")
